import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LanesTab } from "./lanes-tab";

const createLane = vi.fn().mockResolvedValue({ id: 2 });
const updateLane = vi.fn().mockResolvedValue({});
const createLaneCamera = vi.fn().mockResolvedValue({ id: 10 });
const updateLaneCamera = vi.fn().mockResolvedValue({});
const deleteLaneCamera = vi.fn().mockResolvedValue({});
const laneWithCameras = {
  id: 1, name: "Cổng chính", rtsp_url: "rtsp://old", active: true, recognition_mode: "primary",
  cameras: [
    { id: 10, lane_id: 1, role: "front", source_kind: "browser", device_id: "cam-a", rtsp_url: null, is_primary: true, active: true },
  ],
};
vi.mock("@/api/generated/config/config", () => ({
  useListLanes: () => ({ data: [laneWithCameras], isLoading: false }),
  useCreateLane: () => ({ mutateAsync: createLane, isPending: false }),
  useUpdateLane: () => ({ mutateAsync: updateLane, isPending: false }),
  useCreateLaneCamera: () => ({ mutateAsync: createLaneCamera, isPending: false }),
  useUpdateLaneCamera: () => ({ mutateAsync: updateLaneCamera, isPending: false }),
  useDeleteLaneCamera: () => ({ mutateAsync: deleteLaneCamera, isPending: false }),
  getListLanesQueryKey: () => ["/lanes"],
}));
vi.mock("@tanstack/react-query", async (orig) => ({
  ...(await orig<typeof import("@tanstack/react-query")>()),
  useQueryClient: () => ({ invalidateQueries: vi.fn() }),
}));
const toastError = vi.fn();
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: (m: string) => toastError(m) } }));

beforeEach(() => {
  createLane.mockClear();
  updateLane.mockClear();
  createLaneCamera.mockClear();
  updateLaneCamera.mockClear();
  deleteLaneCamera.mockClear();
  toastError.mockClear();
});

test("creates a lane with name and rtsp url", async () => {
  render(<LanesTab />);
  await userEvent.type(screen.getByLabelText("Tên lane mới"), "Cổng phụ");
  await userEvent.type(screen.getByLabelText("RTSP URL mới"), "rtsp://cam2");
  await userEvent.click(screen.getByRole("button", { name: /Tạo lane/i }));
  expect(createLane).toHaveBeenCalledWith({ data: { name: "Cổng phụ", rtsp_url: "rtsp://cam2", active: true } });
});

test("edits an existing lane's RTSP url", async () => {
  render(<LanesTab />);
  const rtsp = screen.getByLabelText("RTSP Cổng chính");
  await userEvent.clear(rtsp);
  await userEvent.type(rtsp, "rtsp://new");
  await userEvent.click(screen.getAllByRole("button", { name: /^Lưu$/i })[1]);
  expect(updateLane).toHaveBeenCalledWith({ laneId: 1, data: { rtsp_url: "rtsp://new" } });
});

test("save is disabled until a field changes", async () => {
  render(<LanesTab />);
  // name cell save button (first Lưu) starts disabled since value is unchanged
  expect(screen.getAllByRole("button", { name: /^Lưu$/i })[0]).toBeDisabled();
  await userEvent.type(screen.getByLabelText("Tên lane Cổng chính"), "X");
  expect(screen.getAllByRole("button", { name: /^Lưu$/i })[0]).toBeEnabled();
});

test("opening a lane's camera panel lists its cameras and can delete one", async () => {
  render(<LanesTab />);
  await userEvent.click(screen.getByRole("button", { name: /1 camera/i }));
  expect(screen.getByText(/Camera của làn "Cổng chính"/i)).toBeInTheDocument();
  // "Trước" cũng xuất hiện trong <select> thêm camera mới, nên kiểm ít nhất 1 chỗ.
  expect(screen.getAllByText("Trước").length).toBeGreaterThan(0);
  expect(screen.getByText("Chính")).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: /Xoá/i }));
  expect(deleteLaneCamera).toHaveBeenCalledWith({ cameraId: 10 });
});

test("adds an RTSP camera to the open lane", async () => {
  render(<LanesTab />);
  await userEvent.click(screen.getByRole("button", { name: /1 camera/i }));
  await userEvent.selectOptions(screen.getByLabelText("Nguồn"), "rtsp");
  await userEvent.type(screen.getByLabelText("RTSP URL"), "rtsp://cam-rear");
  await userEvent.click(screen.getByRole("button", { name: /Thêm camera/i }));
  expect(createLaneCamera).toHaveBeenCalledWith({
    laneId: 1,
    data: {
      role: "front", source_kind: "rtsp", device_id: null, rtsp_url: "rtsp://cam-rear",
      is_primary: false, active: true,
    },
  });
});

test("RTSP camera without a url shows an error instead of submitting", async () => {
  render(<LanesTab />);
  await userEvent.click(screen.getByRole("button", { name: /1 camera/i }));
  await userEvent.selectOptions(screen.getByLabelText("Nguồn"), "rtsp");
  await userEvent.click(screen.getByRole("button", { name: /Thêm camera/i }));
  expect(createLaneCamera).not.toHaveBeenCalled();
  expect(toastError).toHaveBeenCalledWith("Nguồn RTSP cần địa chỉ luồng");
});

test("switching device in camera tester reopens the preview on the newly picked camera", async () => {
  // Trước đây đổi dropdown chỉ ghi nhớ deviceId, khung xem trước vẫn kẹt ở
  // camera mặc định lúc bấm "Thử camera" — nhân viên tưởng camera USB (thiết
  // bị thứ 2 trong danh sách) không nhận được dù vẫn được liệt kê đúng.
  const enumerate = vi.fn().mockResolvedValue([
    { kind: "videoinput", deviceId: "cam-built-in", label: "Built-in" },
    { kind: "videoinput", deviceId: "cam-usb", label: "USB Camera" },
  ]);
  const getUserMedia = vi.fn().mockResolvedValue({ getTracks: () => [{ stop: vi.fn() }] });
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { enumerateDevices: enumerate, getUserMedia },
  });

  render(<LanesTab />);
  await userEvent.click(screen.getByRole("button", { name: /1 camera/i }));
  await userEvent.click(screen.getByRole("button", { name: /Thử camera/i }));
  await waitFor(() => expect(getUserMedia).toHaveBeenCalledTimes(1));
  expect(getUserMedia).toHaveBeenLastCalledWith({ video: true });

  await userEvent.selectOptions(screen.getByLabelText("Chọn thiết bị camera"), "cam-usb");
  await waitFor(() => expect(getUserMedia).toHaveBeenCalledTimes(2));
  expect(getUserMedia).toHaveBeenLastCalledWith({ video: { deviceId: { exact: "cam-usb" } } });
});
