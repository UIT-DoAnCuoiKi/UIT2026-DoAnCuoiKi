import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MultiCameraView } from "./multi-camera-view";
import type { LaneCameraOut } from "@/api/generated/model";
import type { CameraSlot } from "./use-cameras";

function cam(role: string, source_kind: "browser" | "rtsp" = "browser"): LaneCameraOut {
  return {
    id: role === "front" ? 1 : 2,
    lane_id: 1,
    role,
    source_kind,
    device_id: null,
    rtsp_url: source_kind === "rtsp" ? "rtsp://x" : null,
    is_primary: role === "front",
    active: true,
  };
}

function slot(role: string, status: CameraSlot["status"]): CameraSlot {
  return { role, status, videoRef: () => {}, devices: [], deviceId: null, error: null };
}

const noop = () => {};

test("nút Tải ảnh hiện cả khi camera ĐANG chạy (dev_mode bật)", () => {
  // Bug đã gặp thật: máy có webcam cắm sẵn thì ô camera luôn ở trạng thái
  // streaming, nút Tải ảnh chỉ nằm ở nhánh "chưa kết nối" nên không bao giờ
  // bấm được, dù dev_mode đã bật. CameraView (1 camera) không bị lỗi này.
  render(
    <MultiCameraView
      cameras={[cam("front"), cam("rear")]}
      slots={[slot("front", "streaming"), slot("rear", "streaming")]}
      onRequestPermission={noop}
      onUploadForRole={noop}
      allowUpload
    />,
  );
  expect(screen.getAllByRole("button", { name: /Tải ảnh/i })).toHaveLength(2);
});

test("đang chạy + dev_mode tắt thì không có nút Tải ảnh", () => {
  render(
    <MultiCameraView
      cameras={[cam("front")]}
      slots={[slot("front", "streaming")]}
      onRequestPermission={noop}
      onUploadForRole={noop}
      allowUpload={false}
    />,
  );
  expect(screen.queryByRole("button", { name: /Tải ảnh/i })).not.toBeInTheDocument();
});

test("bấm Tải ảnh lúc đang chạy gọi onUploadForRole đúng vai trò camera", async () => {
  const onUploadForRole = vi.fn();
  render(
    <MultiCameraView
      cameras={[cam("front"), cam("rear")]}
      slots={[slot("front", "streaming"), slot("rear", "streaming")]}
      onRequestPermission={noop}
      onUploadForRole={onUploadForRole}
      allowUpload
    />,
  );
  const file = new File(["x"], "plate.jpg", { type: "image/jpeg" });
  await userEvent.upload(screen.getByLabelText("Tải ảnh Sau"), file);
  expect(onUploadForRole).toHaveBeenCalledWith("rear", file);
});

test("camera RTSP chỉ hiện trạng thái, không có nút Tải ảnh", () => {
  render(
    <MultiCameraView
      cameras={[cam("front", "rtsp")]}
      slots={[]}
      onRequestPermission={noop}
      onUploadForRole={noop}
      allowUpload
    />,
  );
  expect(screen.getByText(/RTSP/)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Tải ảnh/i })).not.toBeInTheDocument();
});
