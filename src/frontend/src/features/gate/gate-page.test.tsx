import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { GatePage } from "./gate-page";

vi.mock("@/lib/vehicle-groups", () => ({
  useVehicleGroupMap: () => ({ xe_may: "Xe máy" }),
  groupLabel: (map: Record<string, string>, code?: string | null) => (code ? map[code] ?? code : "—"),
}));

vi.mock("./use-gate-socket", () => ({
  useGateSocket: () => ({ capture: null, events: [], degraded: false }),
}));

test("gate page shows no statistics KPI", () => {
  render(
    <MemoryRouter>
      <GatePage />
    </MemoryRouter>,
  );
  expect(screen.queryByText("Đang trong bãi")).toBeNull();
  expect(screen.queryByText("Doanh thu")).toBeNull();
});
