import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TogglesTab } from "./toggles-tab";

const mutateAsync = vi.fn().mockResolvedValue({ read_plate: false, plate_color: true, vehicle_class: true });
vi.mock("@/api/generated/config/config", () => ({
  useGetToggles: () => ({
    data: { read_plate: true, plate_color: true, vehicle_class: true, dev_mode: false },
    isLoading: false,
  }),
  useUpdateToggles: () => ({ mutateAsync, isPending: false }),
  getGetTogglesQueryKey: () => ["/feature-toggles"],
}));
vi.mock("@tanstack/react-query", async (orig) => ({
  ...(await orig<typeof import("@tanstack/react-query")>()),
  useQueryClient: () => ({ setQueryData: vi.fn(), getQueryData: vi.fn() }),
}));

test("toggling read_plate calls update with new value", async () => {
  render(<TogglesTab />);
  await userEvent.click(screen.getByLabelText(/Đọc biển số/i));
  expect(mutateAsync).toHaveBeenCalledWith({ data: { read_plate: false } });
});

test("toggling dev_mode calls update with new value", async () => {
  render(<TogglesTab />);
  await userEvent.click(screen.getByLabelText(/Chế độ dev/i));
  expect(mutateAsync).toHaveBeenCalledWith({ data: { dev_mode: true } });
});
