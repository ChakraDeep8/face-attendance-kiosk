export type CameraSource = "webcam" | "rtsp-edge";

export const cameraSource: CameraSource =
  (import.meta.env.VITE_CAMERA_SOURCE as CameraSource) || "webcam";

export async function openExperimentCamera(
  purpose: "enrollment" | "monitoring",
): Promise<MediaStream> {
  if (cameraSource !== "webcam") {
    throw new Error(
      "RTSP edge input is not connected yet. Set VITE_CAMERA_SOURCE=webcam for this experiment.",
    );
  }
  return navigator.mediaDevices.getUserMedia({
    video: {
      facingMode: "user",
      width: { ideal: purpose === "monitoring" ? 1920 : 1280 },
      height: { ideal: purpose === "monitoring" ? 1080 : 720 },
      frameRate: { ideal: 30 },
    },
    audio: false,
  });
}

// Future: terminate RTSP on an edge gateway and expose WebRTC to the same
// HTMLVideoElement consumed by the recognition pipeline.
