import React, { useRef, useState, useEffect } from "react";
import { useRoiStore } from "../../store/roiStore";
import { createRectangleFromTwoPoints, clampPoint } from "../../utils/roiGeometry";
import type { ROIPoint } from "../../types";
import { useCameraStream } from "../../hooks/useCameraStream";

interface ROISVGOverlayProps {
  cameraId: string;
  cameraName: string;
}

export const ROISVGOverlay: React.FC<ROISVGOverlayProps> = ({ cameraId, cameraName }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  
  const { videoRef, streamStatus, startStream } = useCameraStream(cameraId);

  useEffect(() => {
    // Automatically start the stream when drawing UI loads
    startStream();
  }, [startStream]);
  
  const {
    draftPoints,
    drawingMode,
    drawingState,
    selectedPointIndex,
    addDraftPoint,
    updateDraftPoint,
    completeZone,
    draftZone
  } = useRoiStore();

  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [hoveredPointIndex, setHoveredPointIndex] = useState<number | null>(null);
  const [mousePos, setMousePos] = useState<ROIPoint | null>(null);

  // ResizeObserver to track container dimension changes
  useEffect(() => {
    if (!containerRef.current) return;

    const observer = new ResizeObserver((entries) => {
      if (entries.length === 0) return;
      const { width, height } = entries[0].contentRect;
      setDimensions({ width, height });
    });

    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

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
    
    // Normalize coordinates back to [0.0, 1.0] by dividing by 1000
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
      // If clicking near first point (threshold 0.02) and points >= 3, complete polygon
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
    
    // Set active point index in store
    useRoiStore.setState({ selectedPointIndex: index });
    setDraggedIndex(index);
    setIsDragging(true);
    
    // Set capture for mouse moving out of bounds
    if (svgRef.current) {
      svgRef.current.setPointerCapture(e.pointerId);
    }
  };

  const handlePointerMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const currentPoint = getSVGCoordinates(e);
    setMousePos(currentPoint);

    if (isDragging && draggedIndex !== null) {
      if (drawingMode === "edit") {
        updateDraftPoint(draggedIndex, currentPoint);
      }
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

  return (
    <div className="space-y-3">
      {/* Visual Workspace Container */}
      <div 
        ref={containerRef}
        className="w-full relative aspect-video bg-black rounded-2xl overflow-hidden shadow-inner border border-outline-variant/30 select-none touch-none"
      >
        {/* Media Underlay */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className={`absolute inset-0 w-full h-full object-contain pointer-events-none select-none transition-opacity duration-300 ${
            streamStatus === "connected" ? "opacity-100" : "opacity-0"
          }`}
        />

        {streamStatus !== "connected" && (
          <div className="absolute inset-0 w-full h-full flex items-center justify-center bg-surface-container-high text-on-surface-variant flex-col gap-3 pointer-events-none select-none z-10">
            {streamStatus === "connecting" || streamStatus === "reconnecting" ? (
              <>
                <div className="w-8 h-8 border-4 border-amber-500 border-t-transparent rounded-full animate-spin"></div>
                <span className="text-xs font-medium">Đang kết nối luồng camera...</span>
              </>
            ) : (
              <>
                <span className="material-symbols-outlined text-[32px]">videocam_off</span>
                <span className="text-xs font-medium">Camera mất kết nối</span>
              </>
            )}
          </div>
        )}

        {/* SVG Drawing Layer */}
        <svg
          ref={svgRef}
          className="absolute inset-0 w-full h-full z-20 cursor-crosshair"
          viewBox="0 0 1000 1000"
          preserveAspectRatio="none"
          onClick={handleSVGClick}
          onPointerMove={handlePointerMove}
          onPointerUp={handlePointerUp}
        >
          {/* Rendering the active polygon/rectangle */}
          {draftPoints.length > 0 && (
            <>
              {draftZone?.type === "polygon" && drawingState !== "roi_saved" && (
                <>
                  {/* Semi-filled polygon shape if completed, or line segment if drawing */}
                  {draftPoints.length >= 3 ? (
                    <polygon
                      points={getPointsString(draftPoints)}
                      className="fill-primary/20 stroke-primary stroke-[3]"
                    />
                  ) : (
                    <polyline
                      points={getPointsString(draftPoints)}
                      className="fill-none stroke-primary stroke-[3]"
                    />
                  )}

                  {/* Temporary line connecting last point to current mouse position */}
                  {drawingState === "roi_drawing" && mousePos && draftPoints.length > 0 && (
                    <line
                      x1={draftPoints[draftPoints.length - 1].x * 1000}
                      y1={draftPoints[draftPoints.length - 1].y * 1000}
                      x2={mousePos.x * 1000}
                      y2={mousePos.y * 1000}
                      className="stroke-primary/50 stroke-[2] stroke-dasharray-[5,5]"
                      style={{ strokeDasharray: "8, 8" }}
                    />
                  )}
                </>
              )}

              {draftZone?.type === "rectangle" && (
                <>
                  {/* Drawing rectangle based on points */}
                  {draftPoints.length === 4 ? (
                    <polygon
                      points={getPointsString(draftPoints)}
                      className="fill-primary/20 stroke-primary stroke-[3]"
                    />
                  ) : (
                    // Preview rectangle during drag definition
                    draftPoints.length === 1 && mousePos && (
                      <polygon
                        points={getPointsString(createRectangleFromTwoPoints(draftPoints[0], mousePos))}
                        className="fill-primary/10 stroke-primary/50 stroke-[2] stroke-dasharray-[5,5]"
                        style={{ strokeDasharray: "8, 8" }}
                      />
                    )
                  )}
                </>
              )}

              {/* Point vertices circular handles */}
              {drawingMode !== "idle" && (drawingMode === "edit" || drawingState === "roi_drawing") && (
                draftPoints.map((pt, idx) => {
                  const isSelected = selectedPointIndex === idx;
                  const isHovered = hoveredPointIndex === idx;
                  
                  return (
                    <circle
                      key={idx}
                      cx={pt.x * 1000}
                      cy={pt.y * 1000}
                      r={isSelected ? 14 : isHovered ? 12 : 9}
                      className={`cursor-move transition-all ${
                        isSelected 
                          ? "fill-red-500 stroke-white stroke-[3]" 
                          : drawingMode === "edit" 
                          ? "fill-primary stroke-white stroke-[2]" 
                          : "fill-on-primary-container stroke-primary stroke-[2]"
                      }`}
                      onPointerDown={(e) => handlePointerDown(idx, e)}
                      onMouseEnter={() => setHoveredPointIndex(idx)}
                      onMouseLeave={() => setHoveredPointIndex(null)}
                    />
                  );
                })
              )}
            </>
          )}
        </svg>

        {/* Dynamic Canvas resolution indicator */}
        <div className="absolute bottom-3 right-3 bg-black/60 px-2.5 py-1 rounded text-[10px] text-white font-mono z-30 select-none pointer-events-none">
          {Math.round(dimensions.width)}x{Math.round(dimensions.height)} px
        </div>
      </div>

      {/* Drawing Instructions text */}
      <div className="bg-surface-container-low p-3.5 rounded-xl border border-outline-variant/20 flex gap-2 items-start text-xs text-on-surface-variant font-medium">
        <span className="material-symbols-outlined text-[18px] text-primary shrink-0">info</span>
        <div className="leading-relaxed">
          {drawingMode === "polygon" && draftPoints.length === 0 && (
            <p>Nhấp vào bất kỳ điểm nào trên khung hình để bắt đầu vẽ đa giác.</p>
          )}
          {drawingMode === "polygon" && draftPoints.length > 0 && draftPoints.length < 3 && (
            <p>Nhấp thêm để tạo góc. Cần tối thiểu <strong>3 điểm</strong> để hoàn thành đa giác.</p>
          )}
          {drawingMode === "polygon" && draftPoints.length >= 3 && (
            <p>Nhấp vào <strong>Điểm đầu tiên</strong> hoặc bấm nút <strong>"Hoàn tất vùng"</strong> ở thanh công cụ để khép kín đa giác.</p>
          )}
          {drawingMode === "rectangle" && draftPoints.length === 0 && (
            <p>Nhấp chọn điểm góc xuất phát của hình chữ nhật, sau đó di chuyển chuột.</p>
          )}
          {drawingMode === "rectangle" && draftPoints.length === 1 && (
            <p>Nhấp chuột lần nữa tại góc đối diện để hoàn thành vẽ hình chữ nhật.</p>
          )}
          {drawingMode === "edit" && (
            <p>Nhấp và kéo các chấm tròn màu xanh để chỉnh sửa các góc. Chọn góc và nhấp <span className="material-symbols-outlined text-[14px] align-middle">delete_forever</span> để xóa.</p>
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
