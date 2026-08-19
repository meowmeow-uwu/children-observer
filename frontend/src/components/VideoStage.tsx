import React, { useRef } from "react";
import { useCameraStream } from "../hooks/useCameraStream";
import { useMediaContentRect, type ContentRect } from "../hooks/useMediaContentRect";
import { useCameraStore } from "../store/cameraStore";

export interface VideoStageRenderContext {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  /** Element video thật (state — effect phụ thuộc sẽ rerun khi element đổi) */
  videoElement: HTMLVideoElement | null;
  contentRect: ContentRect;
  streamStatus: string;
}

interface VideoStageProps {
  cameraId: string;
  /**
   * Render các overlay (ROI SVG, detection) BÊN TRONG vùng video thật.
   * Overlay nhận viewBox 0 0 1000 1000 (preserveAspectRatio="none" an toàn
   * vì container đã khớp đúng tỷ lệ video).
   */
  children: (ctx: VideoStageRenderContext) => React.ReactNode;
  onStartStream?: () => void;
  /** Tự động kết nối stream khi mount (trang vẽ ROI) */
  autoStart?: boolean;
  /** Ref callback — nhận element video thật (gọi trong commit, không phải render) */
  onVideoElement?: (el: HTMLVideoElement | null) => void;
}

/**
 * VideoStage dùng chung cho trang camera và trang vẽ ROI:
 * - Video element (object-contain) qua callback ref + tính media content rect.
 * - Layer overlay được đặt chính xác lên vùng video thật.
 * - `connected` phản ánh trạng thái WebRTC thật từ useCameraStream,
 *   không dùng trạng thái mock.
 */
export const VideoStage: React.FC<VideoStageProps> = ({
  cameraId,
  children,
  onStartStream,
  autoStart = false,
  onVideoElement,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { videoRef, videoElement, attachVideoElement, streamStatus, startStream } = useCameraStream(cameraId);
  const contentRect = useMediaContentRect(containerRef, videoRef);
  const cameraStatus = useCameraStore(
    (state) => state.cameras.find((camera) => camera.id === cameraId)?.status
  );
  const sourceOffline = cameraStatus === "offline";
  const showLiveVideo = streamStatus === "connected" && !sourceOffline;

  const handleAttach = React.useCallback(
    (el: HTMLVideoElement | null) => {
      attachVideoElement(el);
      onVideoElement?.(el);
    },
    [attachVideoElement, onVideoElement]
  );

  React.useEffect(() => {
    if (autoStart && streamStatus === "idle") {
      startStream();
    }
  }, [autoStart, streamStatus, startStream]);

  // Re-attach/đồng bộ stream: element mới (sau khi rời trang rồi quay lại)
  // chưa có srcObject dù store đang connected/connecting/reconnecting.
  // Gọi startStream() → connectToCamera sẽ TÁI SỬ DỤNG kết nối đang sống
  // (không tạo kết nối mới), gắn stream vào element hiện tại và báo trạng
  // thái thật — video không chạy lại từ đầu, không kẹt "đang kết nối".
  React.useEffect(() => {
    if (
      streamStatus !== "idle" &&
      streamStatus !== "failed" &&
      videoElement &&
      !videoElement.srcObject
    ) {
      startStream();
    }
  }, [streamStatus, videoElement, startStream]);

  const handleStart = () => {
    onStartStream?.();
    startStream();
  };

  return (
    <div
      ref={containerRef}
      className="w-full relative aspect-video bg-black rounded-2xl overflow-hidden border border-outline-variant/30"
    >
      <video
        ref={handleAttach}
        autoPlay
        playsInline
        muted
        className={`absolute inset-0 h-full w-full object-contain pointer-events-none select-none transition-all duration-300 ${
          showLiveVideo
            ? "opacity-100"
            : sourceOffline
              ? "scale-[1.01] opacity-40 grayscale blur-[2px]"
              : "opacity-0"
        }`}
      />

      {/* Overlay layer — khớp đúng vùng video thật (không tràn vào letterbox) */}
      <div
        className="absolute pointer-events-none"
        style={{
          left: contentRect.left,
          top: contentRect.top,
          width: contentRect.width,
          height: contentRect.height,
          opacity: showLiveVideo ? 1 : 0,
          transition: "opacity 300ms",
        }}
      >
        {children({ videoRef, videoElement, contentRect, streamStatus })}
      </div>

      {sourceOffline ? (
        <div
          className="absolute inset-0 z-30 flex flex-col items-center justify-center bg-black/55 p-5 text-center backdrop-blur-[1px]"
          role="status"
          aria-live="polite"
        >
          <div className="flex max-w-sm flex-col items-center rounded-2xl border border-white/15 bg-black/65 px-6 py-5 shadow-xl">
            <span className="material-symbols-outlined mb-2 text-[48px] text-red-400">videocam_off</span>
            <strong className="text-base text-white">Mất kết nối camera</strong>
            <span className="mt-1 text-xs leading-5 text-white/75">
              Không nhận được tín hiệu trực tiếp. Hãy kiểm tra nguồn điện, cáp mạng hoặc kết nối RTSP.
            </span>
          </div>
        </div>
      ) : streamStatus === "connecting" || streamStatus === "reconnecting" ? (
        <div className="absolute inset-0 w-full h-full flex items-center justify-center pointer-events-none z-10">
          <div className="bg-black/60 backdrop-blur-sm px-4 py-3 rounded-xl flex items-center gap-3">
            <div className="w-5 h-5 border-2 border-amber-400 border-t-transparent rounded-full animate-spin"></div>
            <span className="text-xs font-medium text-white">Đang kết nối luồng camera...</span>
          </div>
        </div>
      ) : null}

      {!sourceOffline && streamStatus === "idle" && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 z-20">
          <button
            onClick={handleStart}
            className="w-16 h-16 rounded-full bg-primary hover:bg-primary/90 text-white flex items-center justify-center shadow-lg transition-transform hover:scale-105 active:scale-95 cursor-pointer"
            aria-label="Bắt đầu xem trực tiếp"
            title="Bắt đầu xem trực tiếp"
          >
            <span className="material-symbols-outlined text-[36px] fill ml-1">play_arrow</span>
          </button>
          <span className="text-xs text-white font-semibold">Nhấp để kết nối truyền phát camera</span>
        </div>
      )}

      {!sourceOffline && streamStatus === "failed" && (
        <div className="absolute inset-0 z-20 flex items-center justify-center bg-error-container/15 p-4">
          <button
            onClick={handleStart}
            className="min-h-[44px] px-5 py-3 bg-primary text-white text-sm font-bold rounded-xl shadow-sm hover:bg-primary/90 cursor-pointer focus:outline-none focus:ring-2 focus:ring-white/40"
          >
            Thử kết nối lại
          </button>
        </div>
      )}
    </div>
  );
};
