import { useEffect, useMemo, useRef, useState } from "react";
import type { RefObject } from "react";
import type { AiStreamState, TrackBox, TrackFrameMessage } from "../types";
import { useDetectionFeed } from "./useDetectionFeed";

export interface TrackSyncResult {
  tracks: TrackBox[];
  aiState: AiStreamState;
  latencyMs: number;
  lastFrameAgeMs: number;
}

const HEARTBEAT_TIMEOUT_MS = 4000; // không nhận message nào 4s → offline
const HOLD_MAX_MS = 350;           // giữ box tối đa 350ms khi thiếu frame kế tiếp
const STALE_MS = 750;              // stale ≥ 750ms → ẩn box

const SYNC_JITTER_HOLD_MS = 500;

/**
 * Đồng bộ track metadata với video đang render bằng requestVideoFrameCallback.
 *
 * Timeline: browser tính thời gian Edge tương ứng = streamOriginMs + mediaTime*1000
 * (mediaTime từ rVFC; streamOriginMs từ message stream_sync của đúng PeerConnection).
 * - Chọn hai track frame cùng stream_id, cùng loop_id kề quanh edgeTime.
 * - Nội suy tuyến tính box chỉ khi hai box cùng track_id và gap hợp lệ.
 * - Không nội suy qua biên loop / stream khác.
 * - Giữ box tối đa 350ms khi thiếu frame kế tiếp; stale ≥ 750ms phải ẩn.
 * - Browser không hỗ trợ rVFC: dùng latest message theo arrival time với TTL tương tự.
 */
export const useTrackSync = (
  videoRef: RefObject<HTMLVideoElement | null>,
  cameraId: string,
  videoElement: HTMLVideoElement | null = null
): TrackSyncResult => {
  const { frames, status, streamSync, lastActivityAt } = useDetectionFeed(cameraId);
  const [tracks, setTracks] = useState<TrackBox[]>([]);
  const [nowMs, setNowMs] = useState(() => Date.now());

  const framesRef = useRef(frames);
  framesRef.current = frames;
  const streamSyncRef = useRef(streamSync);
  streamSyncRef.current = streamSync;
  const lastResolvedRef = useRef<{ tracks: TrackBox[]; atMs: number } | null>(null);

  const resolveTracks = useMemo(() => {
    return (mediaTimeMs: number): TrackBox[] | null => {
      const list = framesRef.current;
      if (list.length === 0) return [];

      const sync = streamSyncRef.current;
      if (!sync) return null; // no stream origin yet

      // Thời gian Edge tương ứng frame đang render
      const edgeTimeMs = sync.streamOriginMs + mediaTimeMs;

      // Frame quá cũ (stale) → ẩn toàn bộ
      const newest = list[list.length - 1];
      if (edgeTimeMs - newest.sourceTimeMs > STALE_MS) return null;
      if (newest.sourceTimeMs - edgeTimeMs > STALE_MS) return null;

      // Bỏ qua frame thuộc loop cũ (loop mới có sourcePtsMs nhỏ hơn)
      const currentLoop = newest.loopId;
      const loopFrames = list.filter(
        (f) => f.loopId === currentLoop && f.streamId === sync.streamId
      );
      if (loopFrames.length === 0) return null;

      // Tìm hai frame kề nhau (bracketing) quanh edgeTime
      let prev: TrackFrameMessage | null = null;
      let next: TrackFrameMessage | null = null;
      for (const f of loopFrames) {
        if (f.sourceTimeMs <= edgeTimeMs) prev = f;
        else {
          next = f;
          break;
        }
      }
      if (!prev) prev = loopFrames[0];
      if (!next) next = prev;

      const gap = next.sourceTimeMs - prev.sourceTimeMs;
      // Khe hở quá lớn → không nội suy, dùng prev (cũ nhất có thể giữ 350ms)
      const t = gap > 0 && gap <= HOLD_MAX_MS ? (edgeTimeMs - prev.sourceTimeMs) / gap : 0;

      const lerpBox = (
        a: [number, number, number, number],
        b: [number, number, number, number]
      ): [number, number, number, number] => [
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
        a[3] + (b[3] - a[3]) * t,
      ];

      // Chỉ nội suy cùng track_id; track chỉ xuất hiện ở prev → giữ prev
      const prevById = new Map(prev.tracks.map((tr) => [tr.trackId, tr]));
      const merged = new Map<number, TrackBox>();
      for (const tr of prev.tracks) merged.set(tr.trackId, tr);
      for (const tr of next.tracks) {
        const p = prevById.get(tr.trackId);
        if (p && p.confirmed === tr.confirmed) {
          merged.set(tr.trackId, { ...tr, box: lerpBox(p.box, tr.box) });
        } else {
          merged.set(tr.trackId, tr);
        }
      }
      return Array.from(merged.values());
    };
  }, []);

  useEffect(() => {
    // Element thật có thể chưa tồn tại ở effect đầu — effect rerun khi
    // videoElement (state) chuyển từ null thành element.
    const video = videoElement ?? videoRef.current;
    if (!video || typeof video.requestVideoFrameCallback !== "function") {
      // Browser không hỗ trợ rVFC (Firefox) → latest message theo arrival time;
      // stale được xử lý bởi heartbeat timeout (HEARTBEAT_TIMEOUT_MS) bên dưới.
      const latest = framesRef.current[framesRef.current.length - 1];
      setTracks(latest ? latest.tracks : []);
      return;
    }

    let cancelled = false;
    let lastTickMs = 0;
    const loop = (now: number, metadata: VideoFrameCallbackMetadata) => {
      if (cancelled) return;
      const mediaTimeMs = (metadata.mediaTime ?? video.currentTime) * 1000;
      const resolved = resolveTracks(mediaTimeMs);
      if (resolved === null) {
        const previous = lastResolvedRef.current;
        if (previous && now - previous.atMs <= SYNC_JITTER_HOLD_MS) {
          setTracks(previous.tracks);
        } else {
          setTracks([]);
        }
      } else {
        setTracks(resolved);
        // A fresh empty frame means no objects, so do not keep a ghost box.
        lastResolvedRef.current = resolved.length ? { tracks: resolved, atMs: now } : null;
      }
      // Giới hạn re-render khi không có data mới
      if (now - lastTickMs > 200) {
        lastTickMs = now;
        setNowMs(Date.now());
      }
      video.requestVideoFrameCallback(loop);
    };
    video.requestVideoFrameCallback(loop);

    return () => {
      cancelled = true;
    };
  }, [videoElement, videoRef, resolveTracks]);

  // AI state: heartbeat timeout + status từ Edge
  let aiState: AiStreamState = "offline";
  const statusAge = nowMs - lastActivityAt;
  if (statusAge <= HEARTBEAT_TIMEOUT_MS) {
    aiState = status?.state ?? "tracking";
  } else if (status) {
    aiState = "offline";
  }

  return {
    tracks,
    aiState,
    latencyMs: status?.latencyMs ?? 0,
    lastFrameAgeMs: statusAge,
  };
};

declare global {
  interface VideoFrameCallbackMetadata {
    mediaTime: number;
    presentedFrames: number;
    width: number;
    height: number;
    presentationTime: number;
    expectedDisplayTime: number;
  }
}
