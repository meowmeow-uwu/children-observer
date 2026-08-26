import React, { useMemo } from "react";
import type { AiStreamState, PoseSkeleton, TrackBox } from "../types";

interface DetectionOverlayProps {
  tracks: TrackBox[];
  poses?: PoseSkeleton[];
  aiState?: AiStreamState;
  latencyMs?: number;
  showLabels?: boolean;
  showStats?: boolean;
}

const STATE_TEXT: Record<AiStreamState, { label: string; color: string }> = {
  initializing: { label: "AI đang khởi tạo...", color: "#f59e0b" },
  tracking: { label: "AI đang theo dõi", color: "#22c55e" },
  no_objects: { label: "AI online — không có đối tượng", color: "#94a3b8" },
  error: { label: "AI gặp lỗi", color: "#ef4444" },
  offline: { label: "AI ngoại tuyến", color: "#ef4444" },
};

const CLASS_LABEL: Record<string, string> = {
  child: "Trẻ",
  adult: "Người lớn",
  knife: "Dao",
  outlet: "Ổ điện",
  scissors: "Kéo",
};

const FALL_STATE_LABEL: Record<NonNullable<TrackBox["fall"]>["state"], string> = {
  normal: "Bình thường",
  suspected: "Nghi ngờ té ngã",
  confirmed: "Đã xác nhận té ngã",
  recovered: "Đã hồi phục",
};

// COCO-17 topology, indexed from zero.  This colour stays fixed; fall state is
// communicated in the label instead of changing the appearance of the pose.
const FALL_SKELETON: ReadonlyArray<readonly [number, number]> = [
  [0, 1], [0, 2], [1, 3], [2, 4], [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],
  [5, 11], [6, 12], [11, 12], [11, 13], [13, 15], [12, 14], [14, 16],
];
const KEYPOINT_CONFIDENCE = 0.3;

/**
 * Overlay bounding boxes thuần presentation:
 * - Box bình thường: xanh (child) — label "Trẻ #12 · 87%".
 * - Box đỏ CHỈ khi track thực sự vi phạm ROI (zone_breach từ Edge).
 * - Trạng thái té ngã hiển thị bằng chữ trên nhãn, không đổi màu box.
 * - Không animation (tôn trọng prefers-reduced-motion), aria-hidden
 *   vì toàn bộ overlay là trang trí không tương tác.
 */
export const DetectionOverlay = React.memo(({
  tracks,
  poses = [],
  aiState = "offline",
  latencyMs = 0,
  showLabels = true,
  showStats = true,
}: DetectionOverlayProps) => {
  const safeTracks = useMemo(
    () => tracks.filter((t) => {
      const [x1, y1, x2, y2] = t.box;
      return t.confidence > 0 && x2 > x1 && y2 > y1;
    }),
    [tracks]
  );

  const stateCfg = STATE_TEXT[aiState] || STATE_TEXT.offline;

  return (
    <svg
      className="absolute inset-0 w-full h-full pointer-events-none select-none"
      viewBox="0 0 1000 1000"
      preserveAspectRatio="none"
      style={{ zIndex: 15 }}
      aria-hidden="true"
    >
      {safeTracks.map((track) => {
        const [x1, y1, x2, y2] = track.box;
        const sx = x1 * 1000;
        const sy = y1 * 1000;
        const sw = Math.max(2, (x2 - x1) * 1000);
        const sh = Math.max(2, (y2 - y1) * 1000);

        const isBreach = Boolean(track.zoneBreach);
        const color = isBreach ? "#ef4444" : "#22c55e";
        const label = track.className
          ? CLASS_LABEL[track.className] || track.className
          : "Trẻ";
        const fallLabel = track.fall ? FALL_STATE_LABEL[track.fall.state] : undefined;

        return (
          <g key={`track-${track.trackId}`}>
            <rect
              x={sx}
              y={sy}
              width={sw}
              height={sh}
              fill="none"
              stroke={color}
              strokeWidth={isBreach ? 4 : 2.5}
              strokeLinejoin="round"
              opacity={0.9}
              rx={4}
              ry={4}
            />
            {isBreach && (
              <>
                <rect x={sx - 4} y={sy - 4} width={sw + 8} height={sh + 8} fill="none" stroke="#ef4444" strokeWidth={1.5} strokeDasharray="6 4" opacity={0.6} />
                <circle cx={sx + sw / 2} cy={sy + sh / 2} r={4} fill="#ef4444" />
              </>
            )}
            {showLabels && (
              <g>
                <rect
                  x={sx}
                  y={sy - 28}
                  width={Math.max(sw * 0.5, fallLabel ? 280 : 150)}
                  height={26}
                  rx={4}
                  fill={color}
                  opacity={0.85}
                />
                <text
                  x={sx + 6}
                  y={sy - 10}
                  fontSize="15"
                  fontWeight="700"
                  fontFamily="Be Vietnam Pro, Inter, sans-serif"
                  fill="white"
                  dominantBaseline="central"
                >
                  {label} #{track.trackId} · {Math.round(track.confidence * 100)}%
                  {isBreach && track.zoneName ? ` · ${track.zoneName}` : ""}
                  {fallLabel ? ` · ${fallLabel}` : ""}
                </text>
              </g>
            )}
          </g>
        );
      })}

      {poses.map((pose, poseIndex) => (
        <g key={`pose-${poseIndex}`} aria-label="Fall pose skeleton">
          {FALL_SKELETON.map(([from, to]) => {
            const start = pose.keypoints[from];
            const end = pose.keypoints[to];
            if (!start || !end || start[2] < KEYPOINT_CONFIDENCE || end[2] < KEYPOINT_CONFIDENCE) {
              return null;
            }
            return (
              <line
                key={`${from}-${to}`}
                x1={start[0] * 1000}
                y1={start[1] * 1000}
                x2={end[0] * 1000}
                y2={end[1] * 1000}
                stroke="#38bdf8"
                strokeWidth={3}
                strokeLinecap="round"
                opacity={0.95}
              />
            );
          })}
          {pose.keypoints.map(([x, y, confidence], index) => (
            confidence >= KEYPOINT_CONFIDENCE ? (
              <circle
                key={index}
                cx={x * 1000}
                cy={y * 1000}
                r={5}
                fill="#facc15"
                stroke="#0f172a"
                strokeWidth={1}
              />
            ) : null
          ))}
        </g>
      ))}

      {showStats && (
        <g>
          <rect x={700} y={10} width={290} height={50} rx={8} fill="rgba(0,0,0,0.6)" />
          <circle cx={718} cy={24} r={4} fill={stateCfg.color} />
          <text x={730} y={28} fontSize="12" fill={stateCfg.color} fontWeight="600" fontFamily="Be Vietnam Pro, sans-serif">
            {stateCfg.label}
          </text>
          <text x={730} y={48} fontSize="12" fill="#94a3b8" fontWeight="500" fontFamily="monospace">
            Tracks: {safeTracks.length} · AI: {Math.round(latencyMs)}ms
          </text>
        </g>
      )}
    </svg>
  );
});
