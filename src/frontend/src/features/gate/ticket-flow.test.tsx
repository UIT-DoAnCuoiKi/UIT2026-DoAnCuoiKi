import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DecisionPanel } from "./decision-panel";
import type { GateCapture } from "./use-gate-socket";

vi.mock("sonner", () => ({ toast: { success: () => {}, error: () => {}, warning: () => {} } }));

const confirmEntry = vi.fn().mockResolvedValue({ id: 1, status: "in_lot", code: "A1B2C3D4", plate_text: "51F-123" });
const previewExit = vi.fn().mockResolvedValue({ outcome: "no_match" });
const inLot = [
  { id: 42, status: "in_lot", code: "51B21666-7AEF1", plate_text: "51B-216.66", entry_time: "2026-09-17T13:00:00" },
  { id: 43, status: "in_lot", code: "29A12345-9C2D0", plate_text: "29A-123.45", entry_time: "2026-09-17T13:05:00" },
];
vi.mock("@/api/generated/sessions/sessions", () => ({
  useConfirmEntry: () => ({ mutateAsync: confirmEntry, isPending: false }),
  useConfirmExit: () => ({ mutateAsync: vi.fn(), isPending: false }),
  usePreviewExit: () => ({ mutateAsync: previewExit, isPending: false }),
  useListSessions: () => ({ data: { items: inLot, total: inLot.length } }),
  useManualSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));
vi.mock("@/api/generated/readings/readings", () => ({ usePatchPlate: () => ({ mutateAsync: vi.fn().mockResolvedValue({}), isPending: false }) }));
vi.mock("@/api/generated/payments/payments", () => ({ useCreatePayment: () => ({ mutateAsync: vi.fn(), isPending: false }) }));
vi.mock("@/api/generated/config/config", () => ({
  useGetToggles: () => ({ data: { read_plate: true, plate_color: true, vehicle_class: true } }),
  useListPriceRules: () => ({ data: [{ id: 1, vehicle_group: "o_to_con", mode: "flat", unit_price: 5000, active: true }] }),
}));
const apiGet = vi.fn();
vi.mock("@/api/axios-instance", () => ({ AXIOS_INSTANCE: { get: (url: string) => apiGet(url) } }));

const capture = (direction: "in" | "out"): GateCapture => ({
  reading_id: 7,
  capture_id: `c-${direction}`,
  direction,
  review_state: "confident",
  plate_text: "51F-123",
});

beforeEach(() => {
  confirmEntry.mockClear();
  previewExit.mockClear();
  apiGet.mockReset();
});

test("xac nhan VAO xong thi hien phieu kem ma vach de in", async () => {
  const onDone = vi.fn();
  render(<DecisionPanel capture={capture("in")} direction="in" onDone={onDone} onRecapture={() => {}} />);
  await userEvent.click(screen.getByRole("button", { name: /Xác nhận VÀO/ }));

  expect(await screen.findByText("A1B2C3D4")).toBeInTheDocument();
  expect(screen.getByRole("img", { name: /Mã vạch A1B2C3D4/ })).toBeInTheDocument();
  expect(onDone).not.toHaveBeenCalled();   // chờ nhân viên in xong mới đóng

  await userEvent.click(screen.getByRole("button", { name: "Xong" }));
  expect(onDone).toHaveBeenCalled();
});

test("go vai ky tu bien so thi hien goi y xe trong bai", async () => {
  render(<DecisionPanel capture={capture("out")} direction="out" onDone={() => {}} onRecapture={() => {}} />);

  await userEvent.type(screen.getByLabelText("Mã phiếu gửi xe"), "29A");
  const goiY = screen.getByRole("button", { name: /29A-123\.45/ });
  await userEvent.click(goiY);

  expect(previewExit).toHaveBeenCalledWith({ data: { reading_id: 7, session_id: 43 } });
  expect(apiGet).not.toHaveBeenCalled();   // khớp trong danh sách thì khỏi gọi API tra mã
});

test("chi con dung mot xe khop thi Enter la chon luon", async () => {
  render(<DecisionPanel capture={capture("out")} direction="out" onDone={() => {}} onRecapture={() => {}} />);

  await userEvent.type(screen.getByLabelText("Mã phiếu gửi xe"), "7AEF1{Enter}");

  expect(previewExit).toHaveBeenCalledWith({ data: { reading_id: 7, session_id: 42 } });
});

test("ma khong khop goi y nao thi goi API tra ma", async () => {
  apiGet.mockResolvedValue({ data: { id: 99 } });
  render(<DecisionPanel capture={capture("out")} direction="out" onDone={() => {}} onRecapture={() => {}} />);

  await userEvent.type(screen.getByLabelText("Mã phiếu gửi xe"), "88X99999-QQQQQ{Enter}");

  expect(apiGet).toHaveBeenCalledWith("/sessions/by-code/88X99999-QQQQQ");
  expect(previewExit).toHaveBeenCalledWith({ data: { reading_id: 7, session_id: 99 } });
});

test("khung VAO khong co o quet ma", () => {
  render(<DecisionPanel capture={capture("in")} direction="in" onDone={() => {}} onRecapture={() => {}} />);
  expect(screen.queryByLabelText("Mã phiếu gửi xe")).toBeNull();
});
