import { render, screen } from "@testing-library/react";
import { StatsPage } from "./stats-page";

vi.mock("@/api/generated/stats/stats", () => ({
  useGetStats: () => ({
    data: { in_lot: 12, entries: 40, exits: 28, revenue: 420000 },
    isLoading: false,
  }),
}));
vi.mock("@/lib/auth", async (orig) => ({
  ...(await orig<typeof import("@/lib/auth")>()),
  getRole: () => "staff",
}));
vi.mock("./stats-export", () => ({
  downloadStatsCsv: vi.fn(),
  fetchDailyRows: vi.fn().mockResolvedValue([]),
}));

test("staff sees KPIs but not export button", () => {
  render(<StatsPage />);
  // RTL normalizes NBSP to a regular space, so a plain space matches the vi-VN format.
  expect(screen.getByText("420.000 ₫")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Xuất CSV/i })).toBeNull();
});
