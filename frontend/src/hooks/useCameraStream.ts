import { useEffect, useRef, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { useCameraStore } from "../store/cameraStore";
import {
  connectToCamera,
  stopCameraConnection,
  reconnectCamera
} from "../services/webrtc";
import type { Camera } from "../types";

export const useCameraStream = (cameraId: string) => {
  const { user } = useAuth();
  
  const videoRef = useRef<HTMLVideoElement | null>(null);
  
  // Localized statuses mirroring cameraStore for reactive rendering
  const [streamStatus, setStreamStatus] = useState<Camera["streamStatus"]>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);

  // Sync state initially from the cameraStore
  useEffect(() => {
    const cam = useCameraStore.getState().cameras.find((c) => c.id === cameraId);
    if (cam) {
      setStreamStatus(cam.streamStatus);
      setIsStreaming(cam.streamStatus === "connected");
    }
  }, [cameraId]);

  const startStream = () => {
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
  };

  const stopStream = () => {
    stopCameraConnection(cameraId);
    setStreamStatus("idle");
    setIsStreaming(false);
  };

  const retryStream = () => {
    if (!videoRef.current) return;
    setErrorMessage(null);
    reconnectCamera(cameraId);
  };

  // Automatic cleanup on unmount or cameraId change
  useEffect(() => {
    return () => {
      stopCameraConnection(cameraId);
    };
  }, [cameraId]);

  return {
    videoRef,
    streamStatus,
    errorMessage,
    startStream,
    stopStream,
    retryStream,
    isStreaming
  };
};
export default useCameraStream;
