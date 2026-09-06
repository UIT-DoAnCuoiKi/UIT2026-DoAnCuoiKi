import { useCallback, useEffect, useRef, useState } from "react";
import type { CameraDevice, CameraStatus } from "./use-camera";

// Bản nhiều camera của use-camera.ts: khi làn cấu hình 2-3 camera (thường
// trước + sau xe), mỗi camera cần luồng riêng, chụp đồng thời tất cả. Quản lý
// theo Record<role, ...> trong CÙNG 1 hook thay vì gọi useCamera() lặp lại,
// vì số lượng "role" có thể đổi (đổi cấu hình làn) và hook không được gọi có
// điều kiện/số lượng thay đổi giữa các lần render.
export type CameraSlot = {
  role: string;
  videoRef: (el: HTMLVideoElement | null) => void;
  devices: CameraDevice[];
  deviceId: string | null;
  status: CameraStatus;
  error: string | null;
};

export function useCameras(roles: string[]) {
  const videoEls = useRef<Record<string, HTMLVideoElement | null>>({});
  const streams = useRef<Record<string, MediaStream | null>>({});
  const [devices, setDevices] = useState<Record<string, CameraDevice[]>>({});
  const [deviceIds, setDeviceIds] = useState<Record<string, string | null>>({});
  const [statuses, setStatuses] = useState<Record<string, CameraStatus>>({});
  const [errors, setErrors] = useState<Record<string, string | null>>({});

  const attachStream = (role: string, stream: MediaStream | null) => {
    const el = videoEls.current[role];
    if (el && stream && el.srcObject !== stream) {
      el.srcObject = stream;
      void el.play?.().catch(() => {});
    }
  };

  const listDevices = useCallback(async (role: string) => {
    try {
      const all = await navigator.mediaDevices.enumerateDevices();
      const cams = all.filter((d) => d.kind === "videoinput").map((d) => ({ deviceId: d.deviceId, label: d.label || "Camera" }));
      setDevices((s) => ({ ...s, [role]: cams }));
      setDeviceIds((s) => ({ ...s, [role]: s[role] ?? cams[0]?.deviceId ?? null }));
      setStatuses((s) => ({ ...s, [role]: cams.length === 0 ? "no-device" : s[role] === "streaming" ? s[role] : "idle" }));
    } catch {
      setErrors((s) => ({ ...s, [role]: "Không liệt kê được camera" }));
      setStatuses((s) => ({ ...s, [role]: "error" }));
    }
  }, []);

  const start = useCallback(async (role: string, id?: string): Promise<boolean> => {
    setStatuses((s) => ({ ...s, [role]: "requesting" }));
    try {
      const constraints: MediaStreamConstraints = { video: id ? { deviceId: { exact: id } } : true };
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      streams.current[role]?.getTracks().forEach((t) => t.stop());
      streams.current[role] = stream;
      attachStream(role, stream);
      setErrors((s) => ({ ...s, [role]: null }));
      setStatuses((s) => ({ ...s, [role]: "streaming" }));
      return true;
    } catch (e) {
      const name = (e as { name?: string })?.name;
      const denied = name === "NotAllowedError" || name === "SecurityError";
      setErrors((s) => ({ ...s, [role]: "Không mở được camera (kiểm tra quyền hoặc thiết bị)" }));
      setStatuses((s) => ({ ...s, [role]: denied ? "denied" : "error" }));
      return false;
    }
  }, []);

  const requestPermission = useCallback(
    async (role: string) => {
      const ok = await start(role);
      if (ok) await listDevices(role);
    },
    [start, listDevices],
  );

  const setDeviceId = useCallback((role: string, id: string) => {
    setDeviceIds((s) => ({ ...s, [role]: id }));
  }, []);

  const capture = useCallback(async (role: string): Promise<Blob | null> => {
    const video = videoEls.current[role];
    if (!video || !video.videoWidth) return null;
    const canvas = document.createElement("canvas");
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return null;
    ctx.drawImage(video, 0, 0);
    return new Promise((resolve) => canvas.toBlob((b) => resolve(b), "image/jpeg", 0.85));
  }, []);

  /** Chụp tất cả camera đang stream cùng lúc — 1 nút Chụp cho cả làn. */
  const captureAll = useCallback(async (): Promise<{ role: string; blob: Blob }[]> => {
    const out: { role: string; blob: Blob }[] = [];
    for (const role of roles) {
      if (statuses[role] !== "streaming") continue;
      const blob = await capture(role);
      if (blob) out.push({ role, blob });
    }
    return out;
  }, [roles, statuses, capture]);

  // Đổi deviceId của 1 role thì mở lại đúng luồng của role đó, không đụng role khác.
  useEffect(() => {
    for (const role of roles) {
      const id = deviceIds[role];
      if (id) start(role, id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roles.map((r) => deviceIds[r]).join(",")]);

  useEffect(() => {
    return () => {
      Object.values(streams.current).forEach((s) => s?.getTracks().forEach((t) => t.stop()));
    };
  }, []);

  const slots: CameraSlot[] = roles.map((role) => ({
    role,
    videoRef: (el: HTMLVideoElement | null) => {
      videoEls.current[role] = el;
      attachStream(role, streams.current[role] ?? null);
    },
    devices: devices[role] ?? [],
    deviceId: deviceIds[role] ?? null,
    status: statuses[role] ?? "idle",
    error: errors[role] ?? null,
  }));

  return { slots, start, requestPermission, setDeviceId, capture, captureAll };
}
