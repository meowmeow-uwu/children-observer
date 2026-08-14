import { useCallback, useEffect, useRef, useState } from "react";
import { subscribeToTrackFeed } from "../services/webrtc";
import type {
  AiFeedMessage,
  AiStatusMessage,
  StreamSyncMessage,
  TrackFrameMessage,
} from "../types";

export interface DetectionFeedState {
  /** Message tracks của stream HIỆN TẠI (ring buffer) — useTrackSync chọn theo sourceTimeMs */
  frames: TrackFrameMessage[];
  status: AiStatusMessage | null;
  streamSync: StreamSyncMessage | null;
  /** Lần cuối nhận được bất kỳ message nào (ms epoch) — phát hiện AI offline */
  lastActivityAt: number;
  streamId: string | null;
}

const MAX_FRAMES = 64; // 8 FPS * 8s

/**
 * Lắng nghe AI feed của một camera từ WebRTC DataChannel.
 * Buffer được partition theo (camera, stream): stream mới (reconnect/PC mới)
 * làm sạch buffer cũ — không nội suy qua stream khác.
 * An toàn với React StrictMode: unsubscribe triệt để khi unmount.
 */
export const useDetectionFeed = (cameraId: string): DetectionFeedState => {
  const [frames, setFrames] = useState<TrackFrameMessage[]>([]);
  const [status, setStatus] = useState<AiStatusMessage | null>(null);
  const [streamSync, setStreamSync] = useState<StreamSyncMessage | null>(null);
  const [lastActivityAt, setLastActivityAt] = useState(0);
  const [streamId, setStreamId] = useState<string | null>(null);

  const framesRef = useRef<TrackFrameMessage[]>([]);
  const lastActivityRef = useRef(0);
  const streamIdRef = useRef<string | null>(null);

  const handleMessage = useCallback((msg: AiFeedMessage) => {
    const now = Date.now();
    lastActivityRef.current = now;
    setLastActivityAt(now);

    // Stream mới → buffer cũ phải được loại bỏ hoàn toàn
    if (msg.streamId !== streamIdRef.current) {
      streamIdRef.current = msg.streamId;
      framesRef.current = [];
      setStreamId(msg.streamId);
      setFrames([]);
    }

    if (msg.type === "stream_sync") {
      setStreamSync(msg);
    } else if (msg.type === "tracks") {
      const next = [...framesRef.current, msg];
      if (next.length > MAX_FRAMES) {
        next.splice(0, next.length - MAX_FRAMES);
      }
      framesRef.current = next;
      setFrames(next);
    } else if (msg.type === "status") {
      setStatus(msg);
    }
  }, []);

  useEffect(() => {
    if (!cameraId) return;
    return subscribeToTrackFeed(cameraId, handleMessage);
  }, [cameraId, handleMessage]);

  return { frames, status, streamSync, lastActivityAt, streamId };
};
