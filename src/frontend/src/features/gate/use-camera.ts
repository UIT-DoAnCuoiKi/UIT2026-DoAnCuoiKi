import { useCallback, useEffect, useRef, useState } from "react";

export type CameraDevice = { deviceId: string; label: string };
export type CameraStatus = "idle" | "requesting" | "streaming" | "denied" | "no-device" | "error";

export function useCamera() {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [devices, setDevices] = useState<CameraDevice[]>([]);
  const [deviceId, setDeviceId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<CameraStatus>("idle");

  const listDevices = useCallback(async () => {
    try {
      const all = await navigator.mediaDevices.enumerateDevices();
      const cams = all
        .filter((d) => d.kind === "videoinput")
        .map((d) => ({ deviceId: d.deviceId, label: d.label || "Camera" }));
      setDevices(cams);
      setDeviceId((prev) => prev ?? (cams[0]?.deviceId ?? null));
      setStatus((prev) => (cams.length === 0 ? "no-device" : prev === "streaming" ? prev : "idle"));
    } catch {
      setError("Không liệt kê được camera");
      setStatus("error");
    }
  }, []);

  const start = useCallback(async (id?: string): Promise<boolean> => {
    setStatus("requesting");
    try {
      const constraints: MediaStreamConstraints = {
        video: id ? { deviceId: { exact: id } } : true,
      };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = stream;
      setStream(stream);
      setError(null);
      setStatus("streaming");
      return true;
    } catch (e) {
      const name = (e as { name?: string })?.name;
      const denied = name === "NotAllowedError" || name === "SecurityError";
      setError("Không mở được camera (kiểm tra quyền hoặc thiết bị)");
      setStatus(denied ? "denied" : "error");
      return false;
    }
  }, []);

  const requestPermission = useCallback(async () => {
    const ok = await start();
    if (ok) await listDevices();
  }, [start, listDevices]);

  const capture = useCallback(async (): Promise<Blob | null> => {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return null;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;
    ctx.drawImage(video, 0, 0);
    return new Promise((resolve) => canvas.toBlob((b) => resolve(b), "image/jpeg", 0.85));
  }, []);

  // Gán stream vào <video> sau khi phần tử đã mount. start() không gán trực tiếp
  // được vì <video> chỉ render khi status === "streaming", còn lúc start chạy
  // status vẫn là "requesting" nên videoRef.current chưa tồn tại.
  useEffect(() => {
    const v = videoRef.current;
    if (v && stream && v.srcObject !== stream) {
      v.srcObject = stream;
      void v.play?.().catch(() => {});
    }
  }, [stream, status]);

  useEffect(() => {
    return () => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  return { videoRef, devices, deviceId, setDeviceId, listDevices, start, requestPermission, capture, error, status };
}
