import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DecisionPanel } from "./decision-panel";
import type { GateCapture } from "./use-gate-socket";

vi.mock("./payment-dialog", () => ({
  PaymentDialog: ({ amount }: { amount: number }) => <div>DIALOG {amount}</div>,
}));

const confirmEntry = vi.fn().mockResolvedValue({ id: 1, status: "in_lot" });
const confirmExit = vi.fn();
vi.mock("@/api/generated/sessions/sessions", () => ({
  useConfirmEntry: () => ({ mutateAsync: confirmEntry, isPending: false }),
  useConfirmExit: () => ({ mutateAsync: confirmExit, isPending: false }),
  useManualSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));
vi.mock("@/api/generated/readings/readings", () => ({
  usePatchPlate: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));
vi.mock("@/api/generated/config/config", () => ({
  useGetToggles: () => ({ data: { read_plate: true, plate_color: true, vehicle_class: true } }),
}));

const base: GateCapture = {
  reading_id: 7,
  capture_id: "c1",
  direction: "in",
  review_state: "confident",
  plate_text: "51F-123",
};

test("confident IN shows confirm entry and calls API", async () => {
  render(<DecisionPanel capture={base} direction="in" onDone={() => {}} />);
  await userEvent.click(screen.getByRole("button", { name: /Xác nhận VÀO/i }));
  expect(confirmEntry).toHaveBeenCalledWith({ data: { reading_id: 7 } });
});

test("manual state always shows full manual entry button", () => {
  render(<DecisionPanel capture={{ ...base, review_state: "manual" }} direction="in" onDone={() => {}} />);
  expect(screen.getByRole("button", { name: /Nhập tay hoàn toàn/i })).toBeInTheDocument();
});

test("exit with positive fee opens payment dialog", async () => {
  confirmExit.mockResolvedValueOnce({ outcome: "completed", session: { id: 9, fee_amount: 5000, plate_text: "51F1" } });
  render(<DecisionPanel capture={{ ...base, direction: "out", review_state: "confident" }} direction="out" onDone={() => {}} />);
  await userEvent.click(screen.getByRole("button", { name: /Xác nhận RA/i }));
  expect(await screen.findByText(/DIALOG 5000/)).toBeInTheDocument();
});
