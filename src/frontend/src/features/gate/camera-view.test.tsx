import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CameraView } from "./camera-view";

const base = {
  videoRef: { current: null },
  devices: [],
  deviceId: null,
  onSelectDevice: () => {},
  onCapture: () => {},
  onManual: () => {},
  onUpload: () => {},
  error: null,
  allowUpload: true,
};

test("no-device status shows connect button and hides video", () => {
  render(<CameraView {...base} status="no-device" onRequestPermission={() => {}} />);
  expect(screen.getByRole("button", { name: /Kết nối lại/i })).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Chụp" })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Nhập tay/i })).toBeInTheDocument();
});

test("denied status calls onRequestPermission when granting", async () => {
  const onRequestPermission = vi.fn();
  render(<CameraView {...base} status="denied" onRequestPermission={onRequestPermission} />);
  await userEvent.click(screen.getByRole("button", { name: /Cấp quyền camera/i }));
  expect(onRequestPermission).toHaveBeenCalled();
});

test("streaming status shows capture button", () => {
  render(
    <CameraView
      {...base}
      status="streaming"
      devices={[{ deviceId: "cam-a", label: "Cam A" }]}
      deviceId="cam-a"
      onRequestPermission={() => {}}
    />,
  );
  expect(screen.getByRole("button", { name: "Chụp" })).toBeInTheDocument();
});

test("picking a file calls onUpload (fallback khi không có camera)", async () => {
  const onUpload = vi.fn();
  render(<CameraView {...base} status="no-device" onRequestPermission={() => {}} onUpload={onUpload} />);
  const file = new File(["x"], "plate.jpg", { type: "image/jpeg" });
  await userEvent.upload(screen.getByLabelText("Tải ảnh lên"), file);
  expect(onUpload).toHaveBeenCalledWith(file);
});

test("upload fallback hidden when allowUpload is off (dev_mode off)", () => {
  render(<CameraView {...base} status="no-device" onRequestPermission={() => {}} allowUpload={false} />);
  expect(screen.queryByLabelText("Tải ảnh lên")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Tải ảnh lên" })).not.toBeInTheDocument();
});

test("upload fallback hidden in streaming state when allowUpload is off", () => {
  render(
    <CameraView
      {...base}
      status="streaming"
      devices={[{ deviceId: "cam-a", label: "Cam A" }]}
      deviceId="cam-a"
      onRequestPermission={() => {}}
      allowUpload={false}
    />,
  );
  expect(screen.queryByLabelText("Tải ảnh lên")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Tải ảnh" })).not.toBeInTheDocument();
});
