import { useCallback, useEffect, useState } from "react";

export interface ContentRect {
  left: number;
  top: number;
  width: number;
  height: number;
}

/**
 * Tính vùng hiển thị thực của video (object-contain) bên trong container.
 *
 * ROI và detection box CHỈ map lên phần video thật, không map lên letterbox.
 * Khắc phục lỗi preserveAspectRatio="none" làm lệch ROI/box với video khác tỷ lệ.
 */
export const useMediaContentRect = (
  containerRef: React.RefObject<HTMLDivElement | null>,
  videoRef: React.RefObject<HTMLVideoElement | null>
): ContentRect => {
  const [rect, setRect] = useState<ContentRect>({ left: 0, top: 0, width: 0, height: 0 });

  const compute = useCallback(() => {
    const container = containerRef.current;
    const video = videoRef.current;
    if (!container || !video) return;

    const cw = container.clientWidth;
    const ch = container.clientHeight;
    const vw = video.videoWidth || 16;
    const vh = video.videoHeight || 9;
    if (cw === 0 || ch === 0) return;

    const scale = Math.min(cw / vw, ch / vh);
    const width = vw * scale;
    const height = vh * scale;
    setRect({
      left: (cw - width) / 2,
      top: (ch - height) / 2,
      width,
      height,
    });
  }, [containerRef, videoRef]);

  useEffect(() => {
    const container = containerRef.current;
    const video = videoRef.current;
    if (!container || !video) return;

    compute();
    const observer = new ResizeObserver(compute);
    observer.observe(container);
    video.addEventListener("loadedmetadata", compute);
    video.addEventListener("resize", compute);
    return () => {
      observer.disconnect();
      video.removeEventListener("loadedmetadata", compute);
      video.removeEventListener("resize", compute);
    };
  }, [compute, containerRef, videoRef]);

  return rect;
};
