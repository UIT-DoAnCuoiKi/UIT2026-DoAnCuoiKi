import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LanesTab } from "./lanes-tab";

const createLane = vi.fn().mockResolvedValue({ id: 2 });
const updateLane = vi.fn().mockResolvedValue({});
vi.mock("@/api/generated/config/config", () => ({
  useListLanes: () => ({
    data: [{ id: 1, name: "Cổng chính", rtsp_url: "rtsp://old", active: true }],
    isLoading: false,
  }),
  useCreateLane: () => ({ mutateAsync: createLane, isPending: false }),
  useUpdateLane: () => ({ mutateAsync: updateLane, isPending: false }),
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
