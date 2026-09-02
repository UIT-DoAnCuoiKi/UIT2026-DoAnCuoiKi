import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

test("quick range button fills the date inputs", async () => {
  render(<StatsPage />);
  const from = screen.getByLabelText("Từ") as HTMLInputElement;
  const to = screen.getByLabelText("Đến") as HTMLInputElement;
  expect(from.value).toBe("");
  await userEvent.click(screen.getByRole("button", { name: "1 tuần" }));
  expect(from.value).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  expect(to.value).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  expect(from.value <= to.value).toBe(true);
});
