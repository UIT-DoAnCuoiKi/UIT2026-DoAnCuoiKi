import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DecisionPanel } from "./decision-panel";
import type { GateCapture } from "./use-gate-socket";

const toastWarning = vi.fn();
const toastSuccess = vi.fn();
vi.mock("sonner", () => ({
  toast: { success: (m: string) => toastSuccess(m), error: () => {}, warning: (m: string) => toastWarning(m) },
}));

const confirmEntry = vi.fn().mockResolvedValue({ id: 1, status: "in_lot" });
const confirmExit = vi.fn();
const previewExit = vi.fn();
const manualFn = vi.fn().mockResolvedValue({ id: 2 });
const patchFn = vi.fn().mockResolvedValue({});
const payFn = vi.fn().mockResolvedValue({});
vi.mock("@/api/generated/sessions/sessions", () => ({
  useConfirmEntry: () => ({ mutateAsync: confirmEntry, isPending: false }),
  useConfirmExit: () => ({ mutateAsync: confirmExit, isPending: false }),
  usePreviewExit: () => ({ mutateAsync: previewExit, isPending: false }),
  useManualSession: () => ({ mutateAsync: manualFn, isPending: false }),
}));
vi.mock("@/api/generated/readings/readings", () => ({
  usePatchPlate: () => ({ mutateAsync: patchFn, isPending: false }),
}));
vi.mock("@/api/generated/payments/payments", () => ({
  useCreatePayment: () => ({ mutateAsync: payFn, isPending: false }),
}));
vi.mock("@/api/generated/config/config", () => ({
  useGetToggles: () => ({ data: { read_plate: true, plate_color: true, vehicle_class: true } }),
  useListPriceRules: () => ({
    data: [
      { id: 1, vehicle_group: "o_to_con", mode: "flat", unit_price: 20000, active: true },
      { id: 2, vehicle_group: "xe_tai", mode: "block", unit_price: 5000, block_minutes: 30, active: true },
    ],
  }),
}));

const base: GateCapture = {
  reading_id: 7,
  capture_id: "c1",
  direction: "in",
  review_state: "confident",
  plate_text: "51F-123",
};

const noop = () => {};

beforeEach(() => {
  confirmEntry.mockClear();
  confirmExit.mockClear();
  manualFn.mockClear();
  patchFn.mockClear();
  payFn.mockClear();
  toastWarning.mockClear();
  toastSuccess.mockClear();
});

test("confident IN confirms entry", async () => {
  render(<DecisionPanel capture={base} direction="in" onDone={noop} onRecapture={noop} />);
  await userEvent.click(screen.getByRole("button", { name: /Xác nhận VÀO/i }));
  expect(confirmEntry).toHaveBeenCalledWith({ data: { reading_id: 7 } });
});

test("edited plate is saved before confirming entry", async () => {
  render(<DecisionPanel capture={base} direction="in" onDone={noop} onRecapture={noop} />);
  const input = screen.getByLabelText("Biển số");
  await userEvent.clear(input);
  await userEvent.type(input, "51F-999");
  await userEvent.click(screen.getByRole("button", { name: /Xác nhận VÀO/i }));
  expect(patchFn).toHaveBeenCalledWith({ readingId: 7, data: { plate_text: "51F-999" } });
  expect(confirmEntry).toHaveBeenCalled();
});

test("empty plate disables primary confirm and offers plateless entry", async () => {
  render(<DecisionPanel capture={{ ...base, plate_text: "" }} direction="in" onDone={noop} onRecapture={noop} />);
  expect(screen.getByRole("button", { name: /Xác nhận VÀO/i })).toBeDisabled();
  const plateless = screen.getByRole("button", { name: /Vào không biển/i });
  await userEvent.click(plateless);
  expect(confirmEntry).toHaveBeenCalledWith({ data: { reading_id: 7 } });
  expect(patchFn).not.toHaveBeenCalled();
});

test("manual entry derives fee group from vehicle type before submit", async () => {
  render(<DecisionPanel capture={{ ...base, vehicle_type: null }} direction="in" onDone={noop} onRecapture={noop} />);
  await userEvent.click(screen.getByRole("button", { name: /Nhập tay/i }));
  const submit = screen.getByRole("button", { name: /Ghi nhận nhập tay/i });
  expect(submit).toBeDisabled();
  await userEvent.selectOptions(screen.getByLabelText("Loại xe"), "car");
  expect(submit).toBeEnabled();
  await userEvent.click(submit);
  expect(manualFn).toHaveBeenCalledWith({
    data: { action: "entry", plate_text: "51F-123", vehicle_group: "o_to_con", reading_id: 7 },
  });
});

test("entry price follows the selected vehicle type", async () => {
  render(<DecisionPanel capture={{ ...base, vehicle_type: null }} direction="in" onDone={noop} onRecapture={noop} />);
  const price = screen.getByTestId("entry-price");
  expect(price).toHaveTextContent("Chọn loại xe");
  await userEvent.selectOptions(screen.getByLabelText("Loại xe"), "car");
  expect(price).toHaveTextContent(/20.*lượt/);
  await userEvent.selectOptions(screen.getByLabelText("Loại xe"), "truck");
  expect(price).toHaveTextContent(/5.*30 phút/);
});

test("manual edit of vehicle type and plate color is saved via patch", async () => {
  render(
    <DecisionPanel
      capture={{ ...base, vehicle_type: "car", color: "white" }}
      direction="in"
      onDone={noop}
      onRecapture={noop}
    />,
  );
  const save = screen.getByRole("button", { name: /Lưu chỉnh sửa/i });
  expect(save).toBeDisabled();
  await userEvent.selectOptions(screen.getByLabelText("Loại xe"), "truck");
  await userEvent.selectOptions(screen.getByLabelText("Màu biển"), "yellow");
  expect(save).toBeEnabled();
  await userEvent.click(save);
  expect(patchFn).toHaveBeenCalledWith({ readingId: 7, data: { vehicle_type: "truck", color: "yellow" } });
});

test("reset button reverts manual edits to recognized values", async () => {
  render(
    <DecisionPanel
      capture={{ ...base, vehicle_type: "car", color: "white" }}
      direction="in"
      onDone={noop}
      onRecapture={noop}
    />,
  );
  const plate = screen.getByLabelText("Biển số") as HTMLInputElement;
  await userEvent.clear(plate);
  await userEvent.type(plate, "51F-999");
  await userEvent.selectOptions(screen.getByLabelText("Loại xe"), "truck");
  const reset = screen.getByRole("button", { name: /Hoàn tác sửa/i });
  expect(reset).toBeEnabled();
  await userEvent.click(reset);
  expect(plate.value).toBe("51F-123");
  expect((screen.getByLabelText("Loại xe") as HTMLSelectElement).value).toBe("car");
  expect(reset).toBeDisabled();
  expect(patchFn).not.toHaveBeenCalled();
});

test("duplicate 409 offers override; retry sends override_duplicate", async () => {
  confirmEntry
    .mockRejectedValueOnce({ response: { status: 409 } })
    .mockResolvedValueOnce({ id: 1, status: "in_lot" });
  render(<DecisionPanel capture={base} direction="in" onDone={noop} onRecapture={noop} />);
  await userEvent.click(screen.getByRole("button", { name: /^Xác nhận VÀO$/i }));
  const override = await screen.findByRole("button", { name: /ghi đè/i });
  await userEvent.click(override);
  expect(confirmEntry).toHaveBeenLastCalledWith({ data: { reading_id: 7, override_duplicate: true } });
});

test("entry warning from BE is surfaced instead of plain success", async () => {
  confirmEntry.mockResolvedValueOnce({ id: 1, status: "in_lot", warning: "biển trong danh sách đen" });
  render(<DecisionPanel capture={base} direction="in" onDone={noop} onRecapture={noop} />);
  await userEvent.click(screen.getByRole("button", { name: /^Xác nhận VÀO$/i }));
  expect(toastWarning).toHaveBeenCalledWith("biển trong danh sách đen");
  expect(toastSuccess).not.toHaveBeenCalled();
});

test("re-recognize button calls onRecapture", async () => {
  const onRecapture = vi.fn();
  render(<DecisionPanel capture={base} direction="in" onDone={noop} onRecapture={onRecapture} />);
  await userEvent.click(screen.getByRole("button", { name: /Nhận lại/i }));
  expect(onRecapture).toHaveBeenCalled();
});

test("Xoá lượt discards the current capture without saving edits, even with no manual edits made", async () => {
  const onDone = vi.fn();
  render(<DecisionPanel capture={base} direction="in" onDone={onDone} onRecapture={noop} />);
  // Đúng lỗi thật: "Hoàn tác sửa" (trước đây gọi "Đặt lại") bị disable khi chưa
  // sửa gì tay, nên không có cách nào bỏ 1 lượt chụp hỏng trước khi có nút này.
  expect(screen.getByRole("button", { name: /Hoàn tác sửa/i })).toBeDisabled();
  await userEvent.click(screen.getByRole("button", { name: /Xoá lượt/i }));
  expect(onDone).toHaveBeenCalled();
  expect(patchFn).not.toHaveBeenCalled();
});

test("exit goes through review before closing the session", async () => {
  // Bước 1 chỉ tính thử: phải hiện đối chiếu vào/ra, KHÔNG được gọi confirmExit.
  previewExit.mockResolvedValueOnce({
    outcome: "match",
    session: { id: 9, fee_amount: 5000, plate_text: "51F1", entry_time: "2026-09-04T01:00:00" },
    entry_reading: { id: 1, image_asset_id: 11, plate_text: "51F1" },
    exit_reading: { id: 2, image_asset_id: 12, plate_text: "51F1" },
    minutes: 90,
    fee_amount: 5000,
    fee_rule_snapshot: { mode: "flat", unit_price: 5000, minutes: 90 },
  });
  render(<DecisionPanel capture={{ ...base, review_state: "confident" }} direction="out" onDone={noop} onRecapture={noop} />);

  await userEvent.click(screen.getByRole("button", { name: /Đối chiếu & cho RA/i }));
  expect(await screen.findByText(/Lúc VÀO/i)).toBeInTheDocument();
  expect(screen.getByText(/1 giờ 30 phút/i)).toBeInTheDocument();
  expect(confirmExit).not.toHaveBeenCalled();

  // Bước 2 mới thật sự đóng phiên rồi chuyển sang thu tiền.
  confirmExit.mockResolvedValueOnce({
    outcome: "completed",
    session: { id: 9, fee_amount: 5000, plate_text: "51F1", entry_time: "2026-09-04T01:00:00" },
  });
  await userEvent.click(screen.getByRole("button", { name: /^Xác nhận RA$/i }));
  expect(await screen.findByText(/Thu tiền khi RA/i)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /Thu & in/i }));
  expect(payFn).toHaveBeenCalledWith({ data: { session_id: 9, amount: 5000, method: "cash", kind: "payment" } });
});

test("exit review shows entry time and duration before charging", async () => {
  previewExit.mockResolvedValueOnce({
    outcome: "match",
    session: { id: 9, fee_amount: 3000, plate_text: "51F1", entry_time: "2026-09-04T01:00:00" },
    entry_reading: { id: 1, image_asset_id: 11, created_at: "2026-09-04T01:00:00" },
    exit_reading: { id: 2, image_asset_id: 12, created_at: "2026-09-04T03:30:00" },
    minutes: 150,
    fee_amount: 3000,
    fee_rule_snapshot: { mode: "flat", unit_price: 3000, minutes: 150 },
  });
  render(<DecisionPanel capture={{ ...base, review_state: "confident" }} direction="out" onDone={noop} onRecapture={noop} />);
  await userEvent.click(screen.getByRole("button", { name: /Đối chiếu & cho RA/i }));

  expect(await screen.findByText(/Giờ vào/i)).toBeInTheDocument();
  expect(screen.getByText(/2 giờ 30 phút/i)).toBeInTheDocument();
  expect(screen.getByText(/Giá trọn lượt/i)).toBeInTheDocument();
});

test("exit review shows both camera images per side when the lane has multi-camera", async () => {
  previewExit.mockResolvedValueOnce({
    outcome: "match",
    session: { id: 9, fee_amount: 3000, plate_text: "51F1", entry_time: "2026-09-04T01:00:00" },
    entry_reading: {
      id: 1, image_asset_id: 11, created_at: "2026-09-04T01:00:00",
      images: [
        { role: "front", image_asset_id: 11, is_primary: true },
        { role: "rear", image_asset_id: 13, is_primary: false },
      ],
    },
    exit_reading: { id: 2, image_asset_id: 12, created_at: "2026-09-04T03:30:00" },
    minutes: 150,
    fee_amount: 3000,
    fee_rule_snapshot: { mode: "flat", unit_price: 3000, minutes: 150 },
  });
  render(<DecisionPanel capture={{ ...base, review_state: "confident" }} direction="out" onDone={noop} onRecapture={noop} />);
  await userEvent.click(screen.getByRole("button", { name: /Đối chiếu & cho RA/i }));

  // Lúc VÀO có 2 ảnh (đa camera): phải thấy cả nhãn "Trước" và "Sau", không
  // chỉ mỗi ảnh camera chính như trước đây.
  expect(await screen.findByText("Trước")).toBeInTheDocument();
  expect(screen.getByText("Sau")).toBeInTheDocument();
});
