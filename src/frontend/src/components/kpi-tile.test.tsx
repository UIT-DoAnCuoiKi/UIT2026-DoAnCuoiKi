import { render, screen } from "@testing-library/react";
import { KpiTile } from "./kpi-tile";

test("renders value and delta; skeleton when loading", () => {
  const { rerender } = render(<KpiTile title="Đang trong bãi" value="12" tile="blue" delta={5} />);
  expect(screen.getByText("Đang trong bãi")).toBeInTheDocument();
  expect(screen.getByText("12")).toBeInTheDocument();
  rerender(<KpiTile title="X" value="0" tile="blue" loading />);
  expect(screen.queryByText("0")).toBeNull();
});
