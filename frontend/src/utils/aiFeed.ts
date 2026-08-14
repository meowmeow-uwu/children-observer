import type {
  AiFeedBase,
  AiFeedMessage,
  AiStatusMessage,
  StreamSyncMessage,
  TrackBox,
  TrackFrameMessage,
} from "../types";
import { AI_FEED_SCHEMA_VERSION } from "../types";

/**
 * Normalize message thật từ Edge (snake_case, schema_version=1) sang model
 * nội bộ camelCase. Đây là biên DUY NHẤT nhận dữ liệu — không cast mù
 * `JSON.parse(...) as AiFeedMessage` ở bất kỳ đâu khác.
 *
 * - Reject message sai schema_version / type / camera / box.
 * - Clamp box về [0,1]; box không hợp lệ → reject track (không render NaN).
 * - Giữ trackId ổn định, không cho key undefined.
 */
const VALID_TYPES = new Set(["stream_sync", "tracks", "status", "heartbeat"]);

const clamp01 = (v: number): number => Math.max(0, Math.min(1, v));

const isFiniteNumber = (v: unknown): v is number =>
  typeof v === "number" && Number.isFinite(v);

const normalizeTrack = (raw: unknown): TrackBox | null => {
  if (typeof raw !== "object" || raw === null) return null;
  const t = raw as Record<string, unknown>;

  const trackId = t.track_id;
  const classId = t.class_id;
  const className = t.class_name;
  const confidence = t.confidence;
  const box = t.box;

  if (!isFiniteNumber(trackId) || trackId < 0) return null;
  if (!isFiniteNumber(confidence) || confidence <= 0 || confidence > 1) return null;
  if (typeof className !== "string" || className.length === 0) return null;

  if (!Array.isArray(box) || box.length !== 4) return null;
  const b = box.map(Number);
  if (b.some((v) => !Number.isFinite(v))) return null;
  const [x1, y1, x2, y2] = b;
  if (x2 <= x1 || y2 <= y1) return null;
  if (x1 < -0.01 || y1 < -0.01 || x2 > 1.01 || y2 > 1.01) return null;

  return {
    trackId: Math.round(trackId),
    classId: isFiniteNumber(classId) ? Math.round(classId) : -1,
    className,
    confidence,
    box: [clamp01(x1), clamp01(y1), clamp01(x2), clamp01(y2)],
    confirmed: t.confirmed === true,
    zoneBreach: t.zone_breach === true,
    zoneId: typeof t.zone_id === "string" || typeof t.zone_id === "number" ? String(t.zone_id) : null,
    zoneName: typeof t.zone_name === "string" ? t.zone_name : null,
  };
};

const requireBase = (raw: Record<string, unknown>): Pick<AiFeedBase, "cameraId" | "streamId" | "sentAtMs"> | null => {
  if (raw.schema_version !== AI_FEED_SCHEMA_VERSION) return null;
  if (typeof raw.camera_id !== "string" || raw.camera_id.length === 0) return null;
  if (typeof raw.stream_id !== "string" || raw.stream_id.length === 0) return null;
  if (!isFiniteNumber(raw.sent_at_ms)) return null;
  return {
    cameraId: raw.camera_id,
    streamId: raw.stream_id,
    sentAtMs: raw.sent_at_ms,
  };
};

export const normalizeAiFeedMessage = (raw: unknown): AiFeedMessage | null => {
  if (typeof raw !== "object" || raw === null) return null;
  const m = raw as Record<string, unknown>;
  const type = m.type;
  if (typeof type !== "string" || !VALID_TYPES.has(type)) return null;

  const base = requireBase(m);
  if (!base) return null;

  if (type === "stream_sync") {
    if (!isFiniteNumber(m.stream_origin_ms)) return null;
    const msg: StreamSyncMessage = {
      ...base,
      type: "stream_sync",
      schemaVersion: AI_FEED_SCHEMA_VERSION,
      streamOriginMs: m.stream_origin_ms,
      videoFps: isFiniteNumber(m.video_fps) ? m.video_fps : 30,
    };
    return msg;
  }

  if (type === "status" || type === "heartbeat") {
    const state = m.state;
    if (
      state !== "initializing" &&
      state !== "tracking" &&
      state !== "no_objects" &&
      state !== "error"
    ) {
      return null;
    }
    const msg: AiStatusMessage = {
      ...base,
      type: "status",
      schemaVersion: AI_FEED_SCHEMA_VERSION,
      state,
      latencyMs: isFiniteNumber(m.latency_ms) ? m.latency_ms : 0,
      trackCount: isFiniteNumber(m.track_count) ? Math.round(m.track_count) : 0,
      sourcePtsMs: isFiniteNumber(m.source_pts_ms) ? m.source_pts_ms : 0,
      loopId: isFiniteNumber(m.loop_id) ? Math.round(m.loop_id) : 0,
      alerts: isFiniteNumber(m.alerts) ? Math.round(m.alerts) : undefined,
    };
    return msg;
  }

  if (type === "tracks") {
    if (!isFiniteNumber(m.source_time_ms) || !isFiniteNumber(m.source_pts_ms)) return null;
    if (!isFiniteNumber(m.loop_id)) return null;
    if (!Array.isArray(m.tracks)) return null;

    const tracks: TrackBox[] = [];
    for (const t of m.tracks) {
      const track = normalizeTrack(t);
      if (track) tracks.push(track);
      // Track không hợp lệ bị bỏ có kiểm soát — không làm crash UI
    }

    const msg: TrackFrameMessage = {
      ...base,
      type: "tracks",
      schemaVersion: AI_FEED_SCHEMA_VERSION,
      frameId: isFiniteNumber(m.frame_id) ? Math.round(m.frame_id) : 0,
      sourcePtsMs: m.source_pts_ms,
      sourceTimeMs: m.source_time_ms,
      loopId: Math.round(m.loop_id),
      latencyMs: isFiniteNumber(m.latency_ms) ? m.latency_ms : 0,
      tracks,
    };
    return msg;
  }

  return null;
};
