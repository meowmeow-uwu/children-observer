import React, { useMemo } from "react";
import type { AiStreamState, TrackBox } from "../types";

interface DetectionOverlayProps {
  tracks: TrackBox[];
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

/**
 * Overlay bounding boxes thuần presentation:
 * - Box bình thường: xanh (child) — label "Trẻ #12 · 87%".
 * - Box đỏ CHỈ khi track thực sự vi phạm ROI (zone_breach từ Edge).
 * - Không animation (tôn trọng prefers-reduced-motion), aria-hidden
 *   vì toàn bộ overlay là trang trí không tương tác.
 */
export const DetectionOverlay = React.memo(({
  tracks,
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
        const isFallConfirmed = track.fall?.state === "confirmed";
        const isFallSuspected = track.fall?.state === "suspected";
        const color = isFallConfirmed || isBreach ? "#ef4444" : isFallSuspected ? "#f59e0b" : "#22c55e";
        const label = track.className
          ? CLASS_LABEL[track.className] || track.className
          : "Trẻ";

        return (
          <g key={`track-${track.trackId}`}>
            <rect
              x={sx}
              y={sy}
              width={sw}
              height={sh}
              fill="none"
              stroke={color}
              strokeWidth={isFallConfirmed || isBreach ? 4 : 2.5}
              strokeLinejoin="round"
              opacity={0.9}
              rx={4}
              ry={4}
            />
            {(isBreach || isFallConfirmed) && (
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
                  width={Math.max(sw * 0.5, 150)}
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
                  {isFallConfirmed ? " · Fall" : isFallSuspected ? " · Suspected fall" : ""}
                </text>
              </g>
            )}
          </g>
        );
      })}

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
