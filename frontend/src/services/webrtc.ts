import type { Camera } from "../types";
import { useCameraStore } from "../store/cameraStore";

export interface WebRTCServiceOptions {
  cameraId: string;
  userId: string;
  videoElement: HTMLVideoElement;
  onStatusChange?: (state: Camera["streamStatus"]) => void;
  onError?: (error: string) => void;
}

export interface WebRTCConnectionHandle {
  cameraId: string;
  userId: string;
  pc: RTCPeerConnection | null;
  ws: WebSocket | null;
  stream: MediaStream | null;
  videoElement: HTMLVideoElement;
  reconnectCount: number;
  isExplicitlyClosed: boolean;
  reconnectTimer?: number;
  stopTimer?: number;
  onStatusChange?: (state: Camera["streamStatus"]) => void;
  onError?: (error: string) => void;
}

export interface SignalingMessage {
  type: "offer" | "answer" | "error" | "camera_offline" | "offline";
  target?: string;
  sender?: string;
  sdp?: string;
  message?: string;
}

// Global active connections map
const activeConnections = new Map<string, WebRTCConnectionHandle>();

// STUN configuration
const iceServers = [
  { urls: "stun:stun.l.google.com:19302" }
  // TODO: Fetch short-lived TURN credentials from backend in production.
];

/**
 * Builds the WS/WSS signaling URL depending on environment and user ID
 */
export const buildSignalingUrl = (userId: string): string => {
  const protocol = import.meta.env.VITE_SIGNALING_PROTOCOL || "ws";
  const host = import.meta.env.VITE_SIGNALING_HOST || "localhost:8007";
  const path = import.meta.env.VITE_SIGNALING_PATH || "/ws/signaling";
  return `${protocol}://${host}${path}/${userId}`;
};

/**
 * Promise helper to wait for non-trickle ICE gathering to complete before sending SDP Offer
 */
const waitForIceGatheringComplete = (pc: RTCPeerConnection): Promise<void> => {
  return new Promise<void>((resolve) => {
    if (pc.iceGatheringState === "complete") {
      resolve();
      return;
    }

    const checkState = () => {
      if (pc.iceGatheringState === "complete") {
        pc.removeEventListener("icegatheringstatechange", checkState);
        resolve();
      }
    };

    pc.addEventListener("icegatheringstatechange", checkState);

    // Timeout fallback after 8 seconds
    setTimeout(() => {
      pc.removeEventListener("icegatheringstatechange", checkState);
      resolve();
    }, 8000);
  });
};

/**
 * Closes and cleans up a specific camera's connection handle
 */
export const disconnectCamera = (cameraId: string) => {
  const handle = activeConnections.get(cameraId);
  if (!handle) return;

  // Clear any pending reconnect timers
  if (handle.reconnectTimer) {
    window.clearTimeout(handle.reconnectTimer);
    handle.reconnectTimer = undefined;
  }

  // Stop all media tracks to release camera hardware
  if (handle.stream) {
    handle.stream.getTracks().forEach((track) => track.stop());
    handle.stream = null;
  }

  // Close peer connection
  if (handle.pc) {
    handle.pc.close();
    handle.pc = null;
  }

  // Close signaling WebSocket
  if (handle.ws) {
    handle.ws.close();
    handle.ws = null;
  }

  // Detach video elements
  try {
    handle.videoElement.srcObject = null;
  } catch {
    // Ignore errors during element detach
  }

  // If explicitly closed, update camera store state
  if (handle.isExplicitlyClosed) {
    useCameraStore.getState().updateCameraStreamStatus(cameraId, "idle");
    if (handle.onStatusChange) {
      handle.onStatusChange("idle");
    }
    activeConnections.delete(cameraId);
  }
};

/**
 * Triggers the reconnect loop with exponential delays (1s, 2s, 4s)
 */
const triggerReconnect = (cameraId: string) => {
  const handle = activeConnections.get(cameraId);
  if (!handle || handle.isExplicitlyClosed) return;

  if (handle.reconnectCount >= 3) {
    // Exhausted retries
    useCameraStore.getState().updateCameraStreamStatus(cameraId, "failed");
    if (handle.onStatusChange) {
      handle.onStatusChange("failed");
    }
    if (handle.onError) {
      handle.onError("Mất kết nối tới camera sau 3 lần thử lại.");
    }
    disconnectCamera(cameraId);
    return;
  }

  // Increment retries count
  handle.reconnectCount += 1;
  useCameraStore.getState().updateCameraStreamStatus(cameraId, "reconnecting");
  if (handle.onStatusChange) {
    handle.onStatusChange("reconnecting");
  }

  const delay = Math.pow(2, handle.reconnectCount - 1) * 1000; // 1000ms, 2000ms, 4000ms
  
  // Cleanup current socket/connection before trying new connect
  disconnectCamera(cameraId);

  handle.reconnectTimer = window.setTimeout(() => {
    // Reconnect
    connectToCamera({
      cameraId: handle.cameraId,
      userId: handle.userId,
      videoElement: handle.videoElement,
      onStatusChange: handle.onStatusChange,
      onError: handle.onError
    }, handle.reconnectCount);
  }, delay);
};

/**
 * Initiates WebRTC streaming connection
 */
export const connectToCamera = async (
  options: WebRTCServiceOptions,
  currentReconnectCount = 0
): Promise<void> => {
  const { cameraId, userId, videoElement, onStatusChange, onError } = options;

  // Reuse existing connection if any
  const existing = activeConnections.get(cameraId);
  if (existing) {
    if (existing.stopTimer) {
      window.clearTimeout(existing.stopTimer);
      existing.stopTimer = undefined;
    }
    
    // Update handle with new component's references
    existing.videoElement = videoElement;
    existing.onStatusChange = onStatusChange;
    existing.onError = onError;

    if (existing.stream) {
      videoElement.srcObject = existing.stream;
      videoElement.play().catch(e => console.error("Play auto-resume failed:", e));
    }

    if (existing.pc || existing.ws) {
      // Immediately notify the new component of the current stream status
      if (onStatusChange) {
        onStatusChange(useCameraStore.getState().cameras.find(c => c.id === cameraId)?.streamStatus || "connected");
      }
      return; // Connection is active, don't duplicate
    }
  }

  // Initialize camera store loading state
  useCameraStore.getState().updateCameraStreamStatus(cameraId, "connecting");
  if (onStatusChange) {
    onStatusChange("connecting");
  }

  // Build signaling path
  const wsUrl = buildSignalingUrl(userId);
  let ws: WebSocket;

  try {
    ws = new WebSocket(wsUrl);
  } catch {
    useCameraStore.getState().updateCameraStreamStatus(cameraId, "failed");
    if (onStatusChange) {
      onStatusChange("failed");
    }
    if (onError) {
      onError("Không thể kết nối tới máy chủ camera.");
    }
    return;
  }

  const handle: WebRTCConnectionHandle = {
    cameraId,
    userId,
    pc: null,
    ws,
    stream: null,
    videoElement,
    reconnectCount: currentReconnectCount,
    isExplicitlyClosed: false,
    onStatusChange,
    onError
  };

  activeConnections.set(cameraId, handle);

  ws.onopen = async () => {
    try {
      const pc = new RTCPeerConnection({ iceServers });
      handle.pc = pc;

      // Listen for ICE state changes
      pc.onconnectionstatechange = () => {
        if (pc.connectionState === "connected") {
          useCameraStore.getState().updateCameraStreamStatus(cameraId, "connected");
          if (onStatusChange) onStatusChange("connected");
        } 
        else if (pc.connectionState === "disconnected" || pc.connectionState === "failed") {
          triggerReconnect(cameraId);
        }
      };

      // Handle receiving remote tracks
      pc.ontrack = (event) => {
        if (event.streams && event.streams[0]) {
          const stream = event.streams[0];
          handle.stream = stream;
          videoElement.srcObject = stream;
          videoElement.play().catch(() => {
            // Autoplay blocked fallback or stream closed
          });

          useCameraStore.getState().updateCameraStreamStatus(cameraId, "connected");
          if (onStatusChange) onStatusChange("connected");
        }
      };

      // Add transceiver to indicate we only want to receive video
      pc.addTransceiver("video", { direction: "recvonly" });

      // Create local SDP Offer
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      // Wait for non-trickle ICE gathering to complete before sending offer
      await waitForIceGatheringComplete(pc);

      if (ws.readyState === WebSocket.OPEN) {
        ws.send(
          JSON.stringify({
            type: "offer",
            target: cameraId,
            sdp: pc.localDescription?.sdp
          })
        );
      }
    } catch {
      triggerReconnect(cameraId);
    }
  };

  ws.onmessage = async (event) => {
    try {
      const msg: SignalingMessage = JSON.parse(event.data);

      if (msg.type === "answer" && msg.sdp && handle.pc) {
        await handle.pc.setRemoteDescription(
          new RTCSessionDescription({
            type: "answer",
            sdp: msg.sdp
          })
        );
      } 
      else if (msg.type === "error") {
        if (onError) {
          onError(msg.message || "Không thể nhận luồng camera. Vui lòng thử lại.");
        }
        triggerReconnect(cameraId);
      } 
      else if (msg.type === "camera_offline" || msg.type === "offline") {
        if (onError) {
          onError("Camera đang mất kết nối.");
        }
        useCameraStore.getState().updateCameraStreamStatus(cameraId, "failed");
        if (onStatusChange) onStatusChange("failed");
        disconnectCamera(cameraId);
      }
    } catch {
      // JSON parse error or remote description set failure
    }
  };

  ws.onerror = () => {
    if (onError) {
      onError("Kết nối tới máy chủ signaling bị lỗi.");
    }
  };

  ws.onclose = () => {
    if (!handle.isExplicitlyClosed) {
      triggerReconnect(cameraId);
    }
  };
};

/**
 * Triggers a manual connection retry
 */
export const reconnectCamera = (cameraId: string) => {
  const handle = activeConnections.get(cameraId);
  if (!handle) return;

  // Reset reconnect counters
  handle.reconnectCount = 0;
  handle.isExplicitlyClosed = false;

  connectToCamera({
    cameraId: handle.cameraId,
    userId: handle.userId,
    videoElement: handle.videoElement,
    onStatusChange: handle.onStatusChange,
    onError: handle.onError
  });
};

/**
 * Explicitly requests closing a specific camera connection
 * Uses a debounce timer to allow reusing the connection when navigating between views
 */
export const stopCameraConnection = (cameraId: string) => {
  const handle = activeConnections.get(cameraId);
  if (handle) {
    if (handle.stopTimer) {
      window.clearTimeout(handle.stopTimer);
    }
    handle.stopTimer = window.setTimeout(() => {
      handle.isExplicitlyClosed = true;
      disconnectCamera(cameraId);
    }, 250); // 250ms debounce
  }
};

/**
 * Cleans up all active connections (e.g. on log out or global page exit)
 */
export const cleanupAllConnections = () => {
  activeConnections.forEach((handle, cameraId) => {
    handle.isExplicitlyClosed = true;
    disconnectCamera(cameraId);
  });
  activeConnections.clear();
};
