import type { AiFeedMessage, Camera } from "../types";
import { useCameraStore } from "../store/cameraStore";
import { normalizeAiFeedMessage } from "../utils/aiFeed";

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

// AI track feed: subscribers per cameraId (nhận message từ data channel)
const feedSubscribers = new Map<string, Set<(msg: AiFeedMessage) => void>>();

const emitFeed = (cameraId: string, msg: AiFeedMessage) => {
  const subs = feedSubscribers.get(cameraId);
  if (!subs) return;
  subs.forEach((cb) => {
    try {
      cb(msg);
    } catch {
      // subscriber errors không làm sập pipeline
    }
  });
};

export const subscribeToTrackFeed = (
  cameraId: string,
  handler: (msg: AiFeedMessage) => void
): (() => void) => {
  let subs = feedSubscribers.get(cameraId);
  if (!subs) {
    subs = new Set();
    feedSubscribers.set(cameraId, subs);
  }
  subs.add(handler);
  return () => {
    subs?.delete(handler);
    if (subs && subs.size === 0) {
      feedSubscribers.delete(cameraId);
    }
  };
};

// STUN configuration
const iceServers = [
  { urls: "stun:stun.l.google.com:19302" }
  // TODO: Fetch short-lived TURN credentials from backend in production.
];

const DATA_CHANNEL_LABEL = "detections";

/**
 * Play video an toàn: play() gọi ngay sau khi set srcObject có thể bị reject
 * (media chưa sẵn sàng) → retry khi element báo canplay/loadeddata.
 * Tránh hiện tượng video kẹt ở frame đầu tiên (paused) khi vừa kết nối.
 */
const playVideo = (el: HTMLVideoElement) => {
  el.play().catch(() => {
    const retry = () => el.play().catch(() => {});
    el.addEventListener("canplay", retry, { once: true });
    el.addEventListener("loadeddata", retry, { once: true });
  });
};

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

  // Clear any pending reconnect/stop timers
  if (handle.reconnectTimer) {
    window.clearTimeout(handle.reconnectTimer);
    handle.reconnectTimer = undefined;
  }
  if (handle.stopTimer) {
    window.clearTimeout(handle.stopTimer);
    handle.stopTimer = undefined;
  }

  // Stop all media tracks
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

  if (handle.isExplicitlyClosed) {
    useCameraStore.getState().updateCameraStreamStatus(cameraId, "idle");
    handle.onStatusChange?.("idle");
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
    handle.onStatusChange?.("failed");
    handle.onError?.("Mất kết nối tới camera sau 3 lần thử lại.");
    disconnectCamera(cameraId);
    return;
  }

  handle.reconnectCount += 1;
  useCameraStore.getState().updateCameraStreamStatus(cameraId, "reconnecting");
  handle.onStatusChange?.("reconnecting");

  const delay = Math.pow(2, handle.reconnectCount - 1) * 1000; // 1000ms, 2000ms, 4000ms

  disconnectCamera(cameraId);

  handle.reconnectTimer = window.setTimeout(() => {
    connectToCamera({
      cameraId: handle.cameraId,
      userId: handle.userId,
      videoElement: handle.videoElement,
      onStatusChange: handle.onStatusChange,
      onError: handle.onError,
    }, handle.reconnectCount);
  }, delay);
};

/**
 * Initiates WebRTC streaming connection (Edge stream video + data channel)
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
      playVideo(videoElement);
    }

    if (existing.pc || existing.ws) {
      onStatusChange?.(useCameraStore.getState().cameras.find((c) => c.id === cameraId)?.streamStatus || "connected");
      return; // Connection is active, don't duplicate
    }
  }

  // Initialize camera store loading state
  useCameraStore.getState().updateCameraStreamStatus(cameraId, "connecting");
  onStatusChange?.("connecting");

  const handle: WebRTCConnectionHandle = {
    cameraId,
    userId,
    pc: null,
    ws: null as unknown as WebSocket,
    stream: null,
    videoElement,
    reconnectCount: currentReconnectCount,
    isExplicitlyClosed: false,
    onStatusChange,
    onError,
  };
  activeConnections.set(cameraId, handle);

  const wsUrl = buildSignalingUrl(userId);
  let ws: WebSocket;

  try {
    ws = new WebSocket(wsUrl);
  } catch {
    useCameraStore.getState().updateCameraStreamStatus(cameraId, "failed");
    onStatusChange?.("failed");
    onError?.("Không thể kết nối tới máy chủ camera.");
    return;
  }
  handle.ws = ws;

  ws.onopen = async () => {
    try {
      const pc = new RTCPeerConnection({ iceServers });
      handle.pc = pc;

      // Data channel "detections" — Edge bơm track metadata theo đúng
      // source_time_ms của frame WebRTC để frontend đồng bộ qua rVFC.
      const dc = pc.createDataChannel(DATA_CHANNEL_LABEL, { ordered: true });
      dc.onopen = () => {
        console.debug(`[webrtc] data channel open (${cameraId})`);
      };
      dc.onmessage = (event) => {
        try {
          const raw = JSON.parse(String(event.data));
          // Normalize/validate tại biên nhận — không cast mù
          const msg = normalizeAiFeedMessage(raw);
          if (msg) {
            emitFeed(cameraId, msg);
          }
        } catch {
          // ignore malformed messages
        }
      };
      dc.onerror = () => {
        console.warn(`[webrtc] data channel error (${cameraId})`);
      };

      pc.onconnectionstatechange = () => {
        if (pc.connectionState === "connected") {
          useCameraStore.getState().updateCameraStreamStatus(cameraId, "connected");
          onStatusChange?.("connected");
        } else if (pc.connectionState === "disconnected" || pc.connectionState === "failed") {
          triggerReconnect(cameraId);
        }
      };

      // Handle receiving remote tracks
      pc.ontrack = (event) => {
        if (event.streams && event.streams[0]) {
          const stream = event.streams[0];
          handle.stream = stream;
          videoElement.srcObject = stream;
          playVideo(videoElement);

          useCameraStore.getState().updateCameraStreamStatus(cameraId, "connected");
          onStatusChange?.("connected");
        }
      };

      // Add transceiver to indicate we only want to receive video
      pc.addTransceiver("video", { direction: "recvonly" });

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      // Wait for non-trickle ICE gathering to complete before sending offer
      await waitForIceGatheringComplete(pc);

      if (ws.readyState === WebSocket.OPEN) {
        ws.send(
          JSON.stringify({
            type: "offer",
            target: cameraId,
            sdp: pc.localDescription?.sdp,
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
            sdp: msg.sdp,
          })
        );
      } else if (msg.type === "error") {
        onError?.(msg.message || "Không thể nhận luồng camera. Vui lòng thử lại.");
        triggerReconnect(cameraId);
      } else if (msg.type === "camera_offline" || msg.type === "offline") {
        onError?.("Camera đang mất kết nối.");
        useCameraStore.getState().updateCameraStreamStatus(cameraId, "failed");
        onStatusChange?.("failed");
        disconnectCamera(cameraId);
      }
    } catch {
      // JSON parse error or remote description set failure
    }
  };

  ws.onerror = () => {
    onError?.("Kết nối tới máy chủ signaling bị lỗi.");
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

  handle.reconnectCount = 0;
  handle.isExplicitlyClosed = false;

  connectToCamera({
    cameraId: handle.cameraId,
    userId: handle.userId,
    videoElement: handle.videoElement,
    onStatusChange: handle.onStatusChange,
    onError: handle.onError,
  });
};

/**
 * Rời view: đóng hẳn kết nối WebRTC.
 *
 * Quay lại trang hoặc refresh sẽ tạo kết nối MỚI và Edge tự tua video về
 * ĐẦU đoạn demo (set_channel → source.restart) — video luôn chạy lại từ đầu
 * mỗi lần vào xem, không dừng rồi chiếu tiếp ở đoạn giữa chừng.
 */
export const stopCameraConnection = (cameraId: string) => {
  const handle = activeConnections.get(cameraId);
  if (!handle) return;

  if (handle.stopTimer) {
    window.clearTimeout(handle.stopTimer);
  }
  // React StrictMode mount → cleanup → mount lại ngay. Grace ngắn cho phép
  // remount tái sử dụng cùng PC; rời route thật vẫn đóng sau 250 ms.
  handle.stopTimer = window.setTimeout(() => {
    if (activeConnections.get(cameraId) !== handle) return;
    handle.stopTimer = undefined;
    handle.isExplicitlyClosed = true;
    disconnectCamera(cameraId);
  }, 250);
};

/**
 * Đóng kết nối thật sự — dùng cho nút "Ngắt xem trực tiếp" (tương đương
 * stopCameraConnection khi rời trang).
 */
export const stopCameraStream = (cameraId: string) => {
  const handle = activeConnections.get(cameraId);
  if (!handle) return;
  if (handle.stopTimer) {
    window.clearTimeout(handle.stopTimer);
    handle.stopTimer = undefined;
  }
  handle.isExplicitlyClosed = true;
  disconnectCamera(cameraId);
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
  feedSubscribers.clear();
};
