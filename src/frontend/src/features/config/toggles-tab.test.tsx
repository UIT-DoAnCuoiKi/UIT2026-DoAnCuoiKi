import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TogglesTab } from "./toggles-tab";

const mutateAsync = vi.fn().mockResolvedValue({ read_plate: false, plate_color: true, vehicle_class: true });
vi.mock("@/api/generated/config/config", () => ({
  useGetToggles: () => ({
    data: { read_plate: true, plate_color: true, vehicle_class: true },
    isLoading: false,
  }),
  useUpdateToggles: () => ({ mutateAsync, isPending: false }),
}));

test("toggling read_plate calls update with new value", async () => {
  render(<TogglesTab />);
  await userEvent.click(screen.getByLabelText(/Đọc biển số/i));
  expect(mutateAsync).toHaveBeenCalledWith({ data: { read_plate: false } });
});
