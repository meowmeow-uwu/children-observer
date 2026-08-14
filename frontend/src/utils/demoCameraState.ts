export type DemoCameraState = "preview" | "connecting" | "failed" | "offline";

export const getDemoCameraState = (cameraId: string): DemoCameraState => {
  if (cameraId === "camera_living_room_01") return "preview";
  if (cameraId.includes("balcony")) return "connecting";
  if (cameraId.includes("kitchen")) return "failed";
  return "offline";
};
