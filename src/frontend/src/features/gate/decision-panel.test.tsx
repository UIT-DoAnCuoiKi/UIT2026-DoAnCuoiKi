import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DecisionPanel } from "./decision-panel";
import type { GateCapture } from "./use-gate-socket";

vi.mock("@/lib/vehicle-groups", () => ({
  useVehicleGroupMap: () => ({ xe_may: "Xe máy" }),
  groupLabel: (m: Record<string, string>, c?: string | null) => (c ? (m[c] ?? c) : "—"),
}));

const toastWarning = vi.fn();
const toastSuccess = vi.fn();
vi.mock("sonner", () => ({
  toast: { success: (m: string) => toastSuccess(m), error: () => {}, warning: (m: string) => toastWarning(m) },
}));

const confirmEntry = vi.fn().mockResolvedValue({ id: 1, status: "in_lot" });
const confirmExit = vi.fn();
const manualFn = vi.fn().mockResolvedValue({ id: 2 });
const patchFn = vi.fn().mockResolvedValue({});
const payFn = vi.fn().mockResolvedValue({});
vi.mock("@/api/generated/sessions/sessions", () => ({
  useConfirmEntry: () => ({ mutateAsync: confirmEntry, isPending: false }),
  useConfirmExit: () => ({ mutateAsync: confirmExit, isPending: false }),
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
}));
vi.mock("@/api/generated/vehicle-groups/vehicle-groups", () => ({
  useListVehicleGroups: () => ({ data: [{ code: "xe_may", display_name: "Xe máy" }, { code: "o_to", display_name: "Ô tô" }] }),
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

test("manual entry requires a vehicle group before submit", async () => {
  render(<DecisionPanel capture={{ ...base, vehicle_group: null }} direction="in" onDone={noop} onRecapture={noop} />);
  await userEvent.click(screen.getByRole("button", { name: /Nhập tay/i }));
  const submit = screen.getByRole("button", { name: /Ghi nhận nhập tay/i });
  expect(submit).toBeDisabled();
  await userEvent.selectOptions(screen.getByLabelText("Nhóm phí"), "o_to");
  expect(submit).toBeEnabled();
  await userEvent.click(submit);
  expect(manualFn).toHaveBeenCalledWith({
    data: { action: "entry", plate_text: "51F-123", vehicle_group: "o_to", reading_id: 7 },
  });
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

test("exit with fee shows inline pay row, no modal", async () => {
  confirmExit.mockResolvedValueOnce({ outcome: "completed", session: { id: 9, fee_amount: 5000, plate_text: "51F1" } });
  render(<DecisionPanel capture={{ ...base, review_state: "confident" }} direction="out" onDone={noop} onRecapture={noop} />);
  await userEvent.click(screen.getByRole("button", { name: /Xác nhận RA/i }));
  expect(await screen.findByText(/Thu tiền khi RA/i)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /Thu & in/i }));
  expect(payFn).toHaveBeenCalledWith({ data: { session_id: 9, amount: 5000, method: "cash", kind: "payment" } });
});
