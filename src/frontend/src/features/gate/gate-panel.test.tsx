import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GatePanel } from "./gate-panel";

const postInfer = vi.fn().mockResolvedValue({ reading_id: 5, capture_id: "c5", direction: "in", review_state: "confident", plate_text: "51F12345" });
vi.mock("./infer-capture", () => ({ postInfer: (...a: unknown[]) => postInfer(...a) }));
vi.mock("./use-cameras", () => ({
  useCameras: (roles: string[]) => ({
    slots: roles.map((role) => ({
      role,
      videoRef: () => {},
      devices: [],
      deviceId: null,
      status: "idle",
      error: null,
    })),
    start: vi.fn(),
    requestPermission: vi.fn(),
    setDeviceId: vi.fn(),
    capture: vi.fn(),
    captureAll: vi.fn().mockResolvedValue([]),
  }),
}));
vi.mock("./use-camera", () => ({
  useCamera: () => ({
    videoRef: { current: null },
    devices: [{ deviceId: "cam-a", label: "Cam A" }],
    deviceId: "cam-a",
    status: "streaming",
    setDeviceId: vi.fn(),
    listDevices: vi.fn(),
    start: vi.fn(),
    requestPermission: vi.fn(),
    capture: vi.fn().mockResolvedValue(new Blob(["x"], { type: "image/jpeg" })),
    error: null,
  }),
}));
vi.mock("@/api/generated/sessions/sessions", () => ({
  useConfirmEntry: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useConfirmExit: () => ({ mutateAsync: vi.fn(), isPending: false }),
  usePreviewExit: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useManualSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));
vi.mock("@/api/generated/readings/readings", () => ({ usePatchPlate: () => ({ mutateAsync: vi.fn(), isPending: false }) }));
vi.mock("@/api/generated/payments/payments", () => ({ useCreatePayment: () => ({ mutateAsync: vi.fn(), isPending: false }) }));
// dev_mode: true mặc định để các test tải-ảnh-tay dưới đây thấy được nút
// "Tải ảnh"; test riêng bên dưới ghi đè về false để khoá hành vi ẩn nút.
const getToggles = vi.fn().mockReturnValue({
  data: { read_plate: true, plate_color: true, vehicle_class: true, dev_mode: true },
});
vi.mock("@/api/generated/config/config", () => ({
  useGetToggles: () => getToggles(),
  useListPriceRules: () => ({ data: [] }),
}));
vi.mock("@/api/generated/vehicle-groups/vehicle-groups", () => ({ useListVehicleGroups: () => ({ data: [] }) }));
vi.mock("@/lib/vehicle-groups", () => ({
  useVehicleGroupMap: () => ({}),
  groupLabel: (_m: unknown, c?: string | null) => c ?? "—",
  groupForVehicleType: (t?: string | null) =>
    ({ car: "o_to_con", truck: "xe_tai", bus: "xe_khach", motorbike: "xe_may", bicycle: "xe_may" })[t ?? ""],
}));

test("capturing runs infer then shows decision for the plate", async () => {
  render(<GatePanel direction="in" wsCapture={null} active onActivate={() => {}} />);
  await userEvent.click(screen.getByRole("button", { name: "Chụp" }));
  expect(postInfer).toHaveBeenCalled();
  expect(await screen.findByDisplayValue(/51F12345/)).toBeInTheDocument();
});

test("multi-camera upload waits for every configured camera role before submitting", async () => {
  postInfer.mockClear();
  render(
    <GatePanel
      direction="in"
      wsCapture={null}
      active
      onActivate={() => {}}
      laneName="lane-1"
      laneCameras={[
        { id: 1, lane_id: 1, role: "front", source_kind: "browser", device_id: null, rtsp_url: null, is_primary: true, active: true },
        { id: 2, lane_id: 1, role: "rear", source_kind: "browser", device_id: null, rtsp_url: null, is_primary: false, active: true },
      ]}
    />,
  );
  const front = new File(["a"], "front.jpg", { type: "image/jpeg" });
  const rear = new File(["b"], "rear.jpg", { type: "image/jpeg" });

  // Tải ảnh camera chính trước: trước đây gửi ngay với 0 ảnh phụ, mất luôn ảnh
  // camera thứ 2 tải sau đó — giờ phải chờ đủ cả 2 role mới gửi.
  await userEvent.upload(screen.getByLabelText("Tải ảnh Trước"), front);
  expect(postInfer).not.toHaveBeenCalled();

  await userEvent.upload(screen.getByLabelText("Tải ảnh Sau"), rear);
  expect(postInfer).toHaveBeenCalledTimes(1);
  const [, , , lane, extraImages, primaryRole] = postInfer.mock.calls[0];
  expect(lane).toBe("lane-1");
  expect(extraImages).toEqual([{ role: "rear", blob: rear }]);
  expect(primaryRole).toBe("front");
});

test("shows a thumbnail for the secondary camera image after a multi-camera capture", async () => {
  // Backend đã lưu đúng cả 2 ảnh (kiểm tra trực tiếp qua DB), nhưng trước đây
  // không có UI nào hiện ảnh phụ — nhân viên tưởng chỉ 1 ảnh được lưu.
  postInfer.mockResolvedValueOnce({
    reading_id: 9,
    capture_id: "c9",
    direction: "in",
    review_state: "confident",
    plate_text: "51F99999",
    images: [
      { role: "front", image_asset_id: 201, is_primary: true },
      { role: "rear", image_asset_id: 202, is_primary: false },
    ],
  });
  render(
    <GatePanel
      direction="in"
      wsCapture={null}
      active
      onActivate={() => {}}
      laneName="lane-1"
      laneCameras={[
        { id: 1, lane_id: 1, role: "front", source_kind: "browser", device_id: null, rtsp_url: null, is_primary: true, active: true },
        { id: 2, lane_id: 1, role: "rear", source_kind: "browser", device_id: null, rtsp_url: null, is_primary: false, active: true },
      ]}
    />,
  );
  await userEvent.upload(screen.getByLabelText("Tải ảnh Trước"), new File(["a"], "f.jpg", { type: "image/jpeg" }));
  await userEvent.upload(screen.getByLabelText("Tải ảnh Sau"), new File(["b"], "r.jpg", { type: "image/jpeg" }));
  // "Sau" xuất hiện ở nhãn ô camera lẫn chú thích thumbnail ảnh phụ mới thêm.
  expect(await screen.findAllByText("Sau")).toHaveLength(2);
});

test("upload fallback is hidden everywhere when dev_mode is off", () => {
  getToggles.mockReturnValueOnce({
    data: { read_plate: true, plate_color: true, vehicle_class: true, dev_mode: false },
  });
  render(
    <GatePanel
      direction="in"
      wsCapture={null}
      active
      onActivate={() => {}}
      laneName="lane-1"
      laneCameras={[
        { id: 1, lane_id: 1, role: "front", source_kind: "browser", device_id: null, rtsp_url: null, is_primary: true, active: true },
      ]}
    />,
  );
  expect(screen.queryByLabelText("Tải ảnh Trước")).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Tải ảnh/i })).not.toBeInTheDocument();
});

test("single-camera upload fallback is hidden when dev_mode is off, shown when on", () => {
  getToggles.mockReturnValueOnce({
    data: { read_plate: true, plate_color: true, vehicle_class: true, dev_mode: false },
  });
  const { unmount } = render(<GatePanel direction="in" wsCapture={null} active onActivate={() => {}} />);
  expect(screen.queryByLabelText("Tải ảnh lên")).not.toBeInTheDocument();
  unmount();

  render(<GatePanel direction="in" wsCapture={null} active onActivate={() => {}} />);
  expect(screen.getByLabelText("Tải ảnh lên")).toBeInTheDocument();
});
