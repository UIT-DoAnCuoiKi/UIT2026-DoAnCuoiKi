import { render, screen } from "@testing-library/react";
import { VehicleGroupsTab } from "./vehicle-groups-tab";

vi.mock("@/api/generated/vehicle-groups/vehicle-groups", () => ({
  useListVehicleGroups: () => ({
    data: [
      { id: 1, code: "xe_may", display_name: "Xe máy", active: true, sort_order: 1 },
      { id: 2, code: "o_to_con", display_name: "Ô tô con", active: true, sort_order: 2 },
    ],
    isLoading: false,
  }),
}));
vi.mock("@/api/generated/config/config", () => ({
  useListPriceRules: () => ({ data: [{ id: 9, vehicle_group: "xe_may", mode: "flat", unit_price: 3000, active: true }] }),
  useCreatePriceRule: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useUpdatePriceRule: () => ({ mutateAsync: vi.fn(), isPending: false }),
  getListPriceRulesQueryKey: () => ["/price-rules"],
}));
vi.mock("@tanstack/react-query", async (orig) => ({
  ...(await orig<typeof import("@tanstack/react-query")>()),
  useQueryClient: () => ({ invalidateQueries: vi.fn() }),
}));

test("renders friendly display_name, not raw code", () => {
  render(<VehicleGroupsTab />);
  expect(screen.getByText("Xe máy")).toBeInTheDocument();
  expect(screen.getByText("Ô tô con")).toBeInTheDocument();
  // Mã kỹ thuật bị ẩn: chỉ hiện tên và giá.
  expect(screen.queryByText("xe_may")).not.toBeInTheDocument();
  expect(screen.queryByText("o_to_con")).not.toBeInTheDocument();
});

test("does not offer add or delete controls (fixed catalog)", () => {
  render(<VehicleGroupsTab />);
  expect(screen.queryByRole("button", { name: /Thêm nhóm/i })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /^Xóa$/i })).not.toBeInTheDocument();
});
