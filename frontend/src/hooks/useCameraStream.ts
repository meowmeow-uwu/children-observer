import { useEffect, useRef, useState, useCallback } from "react";
import { useAuth } from "../context/AuthContext";
import { useCameraStore } from "../store/cameraStore";
import {
  connectToCamera,
  stopCameraConnection,
  stopCameraStream,
  reconnectCamera
} from "../services/webrtc";
import type { Camera } from "../types";

export const useCameraStream = (cameraId: string) => {
  const { user } = useAuth();

  const videoRef = useRef<HTMLVideoElement | null>(null);
  // State element thật — callback ref đảm bảo effect rerun khi element
  // chuyển từ null thành HTMLVideoElement (rVFC gắn đúng element).
  const [videoElement, setVideoElement] = useState<HTMLVideoElement | null>(null);

  // Localized statuses mirroring cameraStore for reactive rendering
  const [streamStatus, setStreamStatus] = useState<Camera["streamStatus"]>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);

  const attachVideoElement = useCallback((el: HTMLVideoElement | null) => {
    videoRef.current = el;
    setVideoElement(el);
  }, []);

  // Sync state initially from the cameraStore
  useEffect(() => {
    const cam = useCameraStore.getState().cameras.find((c) => c.id === cameraId);
    if (cam) {
      setStreamStatus(cam.streamStatus);
      setIsStreaming(cam.streamStatus === "connected");
    }
  }, [cameraId]);

  // Luôn theo sát store — mọi thay đổi trạng thái (connecting/connected/
  // reconnecting/failed) phải phản ánh ngay, không kẹt trạng thái cũ
  // khi quay lại trang hoặc StrictMode remount.
  useEffect(() => {
    const unsub = useCameraStore.subscribe((state) => {
      const cam = state.cameras.find((c) => c.id === cameraId);
      if (cam) {
        setStreamStatus(cam.streamStatus);
        setIsStreaming(cam.streamStatus === "connected");
      }
    });
    return unsub;
  }, [cameraId]);

  const startStream = useCallback(() => {
    if (!videoRef.current) return;

    setErrorMessage(null);
    const userId = user?.id || import.meta.env.VITE_WEBRTC_DEFAULT_USER_ID || "web_parent_01";

    connectToCamera({
      cameraId,
      userId,
      videoElement: videoRef.current,
      onStatusChange: (status) => {
        setStreamStatus(status);
        setIsStreaming(status === "connected");
      },
      onError: (err) => {
        setErrorMessage(err);
      }
    });
  }, [cameraId, user?.id]);

  const stopStream = useCallback(() => {
    // "Ngắt xem trực tiếp" — đóng hẳn kết nối WebRTC
    stopCameraStream(cameraId);
    setStreamStatus("idle");
    setIsStreaming(false);
  }, [cameraId]);

  const retryStream = useCallback(() => {
    if (!videoRef.current) return;
    setErrorMessage(null);
    reconnectCamera(cameraId);
  }, [cameraId]);

  // Automatic cleanup on unmount or cameraId change
  useEffect(() => {
    return () => {
      stopCameraConnection(cameraId);
    };
  }, [cameraId]);

  return {
    videoRef,
    videoElement,
    attachVideoElement,
    streamStatus,
    errorMessage,
    startStream,
    stopStream,
    retryStream,
    isStreaming
  };
};
export default useCameraStream;
