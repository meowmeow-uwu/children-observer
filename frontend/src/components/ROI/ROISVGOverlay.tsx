import React, { useRef, useState, useEffect, useCallback } from "react";
import { useRoiStore } from "../../store/roiStore";
import { createRectangleFromTwoPoints, clampPoint } from "../../utils/roiGeometry";
import type { ROIPoint } from "../../types";
import { VideoStage } from "../VideoStage";

interface ROISVGOverlayProps {
  cameraId: string;
  cameraName: string;
}

export const ROISVGOverlay: React.FC<ROISVGOverlayProps> = ({ cameraId, cameraName }) => {
  const svgRef = useRef<SVGSVGElement>(null);

  const {
    zones,
    draftPoints,
    drawingMode,
    drawingState,
    selectedZoneId,
    selectedPointIndex,
    addDraftPoint,
    updateDraftPoint,
    completeZone,
    draftZone
  } = useRoiStore();

  const allCameraZones = zones.filter(z => z.cameraId === cameraId);
  // Khi edit, selectedZoneId là danh tính canonical của vùng đã lưu. Không
  // dựa vào draftZone vì draft có thể được tạo trước nhịp hydrate từ API.
  const activeZoneId = selectedZoneId ?? draftZone?.id ?? null;
  const existingCameraZones = allCameraZones.filter(z => z.id !== activeZoneId);

  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [hoveredPointIndex, setHoveredPointIndex] = useState<number | null>(null);
  const [mousePos, setMousePos] = useState<ROIPoint | null>(null);

  // ResizeObserver theo dõi kích thước SVG để scale stroke cho hợp lý
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    const observer = new ResizeObserver((entries) => {
      if (entries.length === 0) return;
      const { width, height } = entries[0].contentRect;
      setDimensions({ width, height });
    });
    observer.observe(svg);
    return () => observer.disconnect();
  }, []);

  // Responsive stroke width dựa trên kích thước SVG (từ container)
  const getStrokeWidth = useCallback(() => {
    if (dimensions.width === 0) return 3;
    return Math.max(2.5, Math.min(4.5, 2800 / dimensions.width));
  }, [dimensions.width]);

  // Convert client cursor mouse event to SVG coordinate system [0 - 1000]
  const getSVGCoordinates = (e: React.MouseEvent<SVGSVGElement> | React.PointerEvent<SVGSVGElement>): ROIPoint => {
    const svg = svgRef.current;
    if (!svg) return { x: 0, y: 0 };

    const pt = svg.createSVGPoint();
    pt.x = e.clientX;
    pt.y = e.clientY;

    const screenCTM = svg.getScreenCTM();
    if (!screenCTM) return { x: 0, y: 0 };

    const svgPoint = pt.matrixTransform(screenCTM.inverse());

    return clampPoint({
      x: svgPoint.x / 1000,
      y: svgPoint.y / 1000
    });
  };

  const handleSVGClick = (e: React.MouseEvent<SVGSVGElement>) => {
    // If we are dragging a point or edit index is active, ignore clicks
    if (isDragging || drawingMode === "idle" || drawingMode === "edit") return;

    const clickPoint = getSVGCoordinates(e);

    if (drawingMode === "polygon") {
      // If clicking near first point (threshold 0.025) and points >= 3, complete polygon
      if (draftPoints.length >= 3) {
        const firstPt = draftPoints[0];
        const dist = Math.hypot(clickPoint.x - firstPt.x, clickPoint.y - firstPt.y);
        if (dist < 0.025) {
          completeZone();
          return;
        }
      }
      addDraftPoint(clickPoint);
    }
    else if (drawingMode === "rectangle") {
      if (draftPoints.length === 0) {
        // First click sets starting point
        addDraftPoint(clickPoint);
      } else if (draftPoints.length === 1) {
        // Second click completes rectangle
        const p1 = draftPoints[0];
        const rectPoints = createRectangleFromTwoPoints(p1, clickPoint);

        // Update the store by clearing and pushing the 4 points
        useRoiStore.setState({
          draftPoints: rectPoints,
          drawingState: "roi_unsaved"
        });
      }
    }
  };

  const handlePointerDown = (index: number, e: React.PointerEvent) => {
    if (drawingMode !== "edit") return;
    e.stopPropagation();
    e.preventDefault();

    useRoiStore.setState({ selectedPointIndex: index });
    setDraggedIndex(index);
    setIsDragging(true);

    if (svgRef.current) {
      svgRef.current.setPointerCapture(e.pointerId);
    }
  };

  const handlePointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const currentPoint = getSVGCoordinates(e);
    setMousePos(currentPoint);

    if (isDragging && draggedIndex !== null && drawingMode === "edit") {
      updateDraftPoint(draggedIndex, currentPoint);
    }
  };

  const handlePointerUp = (e: React.PointerEvent<SVGSVGElement>) => {
    if (isDragging) {
      setIsDragging(false);
      setDraggedIndex(null);
      if (svgRef.current) {
        svgRef.current.releasePointerCapture(e.pointerId);
      }
    }
  };

  const getPointsString = (points: ROIPoint[]): string => {
    return points.map((p) => `${p.x * 1000},${p.y * 1000}`).join(" ");
  };

  const strokeW = getStrokeWidth();

  const cursorClass = drawingMode === "polygon" || drawingMode === "rectangle"
    ? "roi-canvas-drawing"
    : drawingMode === "edit"
    ? "roi-canvas-editing"
    : "roi-canvas-idle";

  return (
    <div className="space-y-3">
      <VideoStage cameraId={cameraId} autoStart>
        {({ streamStatus }) => (
          <>
            <div className="pointer-events-none absolute left-3 top-3 z-30 rounded-lg border border-white/15 bg-black/65 px-2.5 py-1.5 text-[10px] font-semibold text-white backdrop-blur-sm">
              {streamStatus === "connected"
                ? `Camera trực tiếp · ${cameraName}`
                : "Đang kết nối camera..."}
            </div>

              {/* SVG maps exactly to the real video content rect supplied by VideoStage. */}
              <svg
                ref={svgRef}
                className={`pointer-events-auto absolute inset-0 z-20 h-full w-full touch-none ${cursorClass}`}
                viewBox="0 0 1000 1000"
                preserveAspectRatio="none"
                role="application"
                aria-label={`Vẽ vùng nguy hiểm trên camera ${cameraName}`}
                onClick={handleSVGClick}
                onPointerMove={handlePointerMove}
                onPointerUp={handlePointerUp}
              >
                <defs>
                  <filter id="roi-glow" x="-50%" y="-50%" width="200%" height="200%">
                    <feGaussianBlur stdDeviation="4" result="blur" />
                    <feComposite in="SourceGraphic" in2="blur" operator="over" />
                  </filter>
                  <pattern id="roi-hatch" patternUnits="userSpaceOnUse" width="20" height="20" patternTransform="rotate(45)">
                    <line x1="0" y1="0" x2="0" y2="20" stroke="#eab308" strokeWidth="1.5" opacity="0.25" />
                  </pattern>
                </defs>

                {/* Render existing zones (inactive style) so user can see them while drawing new ones */}
                {existingCameraZones.map((zone) => {
                  if (zone.points.length < 3) return null;
                  return (
                    <g key={zone.id} opacity={0.8}>
                      <polygon
                        points={getPointsString(zone.points)}
                        fill="rgba(234, 179, 8, 0.1)"
                        stroke="#eab308"
                        strokeWidth="2.5"
                        strokeLinejoin="round"
                      />
                    </g>
                  );
                })}

                {/* Rendering the active polygon/rectangle */}
                {draftPoints.length > 0 && (
                  <>
                    {drawingState !== "roi_saved" && (
                      <>
                        {draftPoints.length >= 3 ? (
                          <>
                            <polygon
                              points={getPointsString(draftPoints)}
                              fill="url(#roi-hatch)"
                              stroke="none"
                            />
                            <polygon
                              points={getPointsString(draftPoints)}
                              fill="rgba(234, 179, 8, 0.2)"
                              stroke="#eab308"
                              strokeWidth={strokeW}
                              strokeLinejoin="round"
                              strokeLinecap="round"
                            />
                          </>
                        ) : (
                          <polyline
                            points={getPointsString(draftPoints)}
                            fill="none"
                            stroke="#eab308"
                            strokeWidth={strokeW}
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          />
                        )}

                        {drawingState === "roi_drawing" && mousePos && draftPoints.length > 0 && (
                          <line
                            x1={draftPoints[draftPoints.length - 1].x * 1000}
                            y1={draftPoints[draftPoints.length - 1].y * 1000}
                            x2={mousePos.x * 1000}
                            y2={mousePos.y * 1000}
                            stroke="#eab308"
                            strokeWidth={strokeW * 0.7}
                            strokeDasharray="10, 8"
                            opacity="0.8"
                          />
                        )}
                      </>
                    )}

                    {/* Point vertices */}
                    {drawingMode !== "idle" && (drawingMode === "edit" || drawingState === "roi_drawing" || drawingState === "roi_unsaved") && (
                      draftPoints.map((pt, idx) => {
                        const isSelected = selectedPointIndex === idx;
                        const isHovered = hoveredPointIndex === idx;
                        const isFirstPoint = idx === 0 && drawingMode === "polygon" && drawingState === "roi_drawing" && draftPoints.length >= 3;

                        const r = isSelected ? 8 : isHovered ? 7 : 6;

                        return (
                          <g key={idx}>
                            {isFirstPoint && (
                              <>
                                <circle
                                  cx={pt.x * 1000}
                                  cy={pt.y * 1000}
                                  r={r * 2.5}
                                  fill="none"
                                  stroke="#eab308"
                                  strokeWidth="2"
                                  opacity="0.5"
                                  style={{ animation: "roi-pulse-ring 1.5s ease-out infinite" }}
                                />
                                <circle
                                  cx={pt.x * 1000}
                                  cy={pt.y * 1000}
                                  r={r * 1.5}
                                  fill="#eab308"
                                  opacity="0.3"
                                  style={{ animation: "roi-pulse 2s ease-in-out infinite" }}
                                />
                              </>
                            )}

                            <circle
                              cx={pt.x * 1000}
                              cy={pt.y * 1000}
                              r={r}
                              fill={isSelected ? "var(--color-error)" : "#eab308"}
                              stroke="white"
                              strokeWidth={isSelected ? 2 : 1.5}
                              className="cursor-move roi-handle-selected"
                              onPointerDown={(e) => handlePointerDown(idx, e)}
                              onMouseEnter={() => setHoveredPointIndex(idx)}
                              onMouseLeave={() => setHoveredPointIndex(null)}
                            />

                            {(isSelected || (isHovered && drawingMode === "edit")) && (
                              <text
                                x={pt.x * 1000}
                                y={pt.y * 1000 - r - 8}
                                textAnchor="middle"
                                fontSize="14"
                                fontWeight="600"
                                fill="white"
                                opacity="0.9"
                                style={{ textShadow: "0 1px 3px rgba(0,0,0,0.8)", pointerEvents: "none" }}
                              >
                                {(pt.x * 100).toFixed(0)}%, {(pt.y * 100).toFixed(0)}%
                              </text>
                            )}
                          </g>
                        );
                      })
                    )}
                  </>
                )}
              </svg>
          </>
        )}
      </VideoStage>

      {/* Dynamic Canvas resolution indicator */}
      <div className="flex flex-wrap items-center gap-2 justify-between">
        {/* Drawing mode indicator badge */}
        {drawingMode !== "idle" && (
          <div className="bg-black/70 backdrop-blur-sm px-3 py-1.5 rounded-lg text-[10px] text-white font-bold select-none flex items-center gap-1.5 animate-fade-in">
            <span className={`w-2 h-2 rounded-full ${
              drawingMode === "polygon" ? "bg-amber-400" : drawingMode === "rectangle" ? "bg-sky-400" : "bg-amber-400"
            }`}></span>
            {drawingMode === "polygon" ? "Đa giác" :
             drawingMode === "rectangle" ? "Hình chữ nhật" :
             "Chỉnh sửa"}
            {draftPoints.length > 0 && (
              <span className="text-white/60 ml-1">• {draftPoints.length} điểm</span>
            )}
          </div>
        )}
      </div>

      {/* Drawing Instructions text */}
      <div className="bg-surface-container-low p-3.5 rounded-xl border border-outline-variant/20 flex gap-2 items-start text-xs text-on-surface-variant font-medium animate-slide-up">
        <span className="material-symbols-outlined text-[18px] text-primary shrink-0">info</span>
        <div className="leading-relaxed">
          {drawingMode === "polygon" && draftPoints.length === 0 && (
            <p>Nhấp vào bất kỳ điểm nào trên khung hình để bắt đầu vẽ đa giác.</p>
          )}
          {drawingMode === "polygon" && draftPoints.length > 0 && draftPoints.length < 3 && (
            <p>Nhấp thêm để tạo góc. Cần tối thiểu <strong>3 điểm</strong> để hoàn thành đa giác.</p>
          )}
          {drawingMode === "polygon" && draftPoints.length >= 3 && drawingState === "roi_drawing" && (
            <p>Nhấp vào <strong className="text-amber-500">Điểm số 1 (đang nhấp nháy)</strong> hoặc bấm nút <strong>"Hoàn tất vùng"</strong> ở thanh công cụ để khép kín đa giác.</p>
          )}
          {drawingMode === "rectangle" && draftPoints.length === 0 && (
            <p>Nhấp điểm góc thứ nhất, sau đó nhấp <strong>góc đối diện</strong> để tạo hình chữ nhật.</p>
          )}
          {drawingMode === "rectangle" && draftPoints.length === 1 && (
            <p>Nhấp <strong>góc đối diện</strong> để hoàn thành hình chữ nhật.</p>
          )}
          {drawingMode === "polygon" && drawingState === "roi_unsaved" && (
            <p>Đa giác đã khép kín. Đặt tên và cấu hình quy tắc ở panel bên phải, sau đó bấm <strong>"Lưu thiết lập"</strong>.</p>
          )}
          {drawingMode === "rectangle" && drawingState === "roi_unsaved" && (
            <p>Hình chữ nhật đã hoàn thành. Đặt tên và cấu hình quy tắc ở panel bên phải, sau đó bấm <strong>"Lưu thiết lập"</strong>.</p>
          )}
          {drawingMode === "edit" && (
            <p>Nhấp và kéo các <strong>điểm nhỏ</strong> để chỉnh sửa các góc. Chọn góc (chuyển đỏ) và nhấp <span className="material-symbols-outlined text-[14px] align-middle text-error">delete_forever</span> để xóa.</p>
          )}
          {drawingMode === "idle" && (
            <p>Hãy vẽ rộng hơn khu vực nguy hiểm thực tế một chút để hệ thống AI cảnh báo sớm hơn.</p>
          )}
        </div>
      </div>
    </div>
  );
};
export default ROISVGOverlay;
