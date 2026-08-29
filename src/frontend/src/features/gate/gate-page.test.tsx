import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GatePage } from "./gate-page";

vi.mock("./use-gate-socket", () => ({
  useGateSocket: () => ({
    capturesByDirection: { in: null, out: null },
    events: [],
    connected: true,
    degraded: false,
  }),
}));
vi.mock("./gate-panel", () => ({
  GatePanel: ({ direction, active }: { direction: string; active: boolean }) => (
    <div data-testid={`panel-${direction}`}>{active ? "ACTIVE" : "idle"}</div>
  ),
}));

beforeEach(() => localStorage.clear());

test("split layout renders both panels by default", () => {
  render(<GatePage />);
  expect(screen.getByTestId("panel-in")).toBeInTheDocument();
  expect(screen.getByTestId("panel-out")).toBeInTheDocument();
});

test("in-only layout renders one panel", async () => {
  render(<GatePage />);
  await userEvent.click(screen.getByRole("button", { name: /Chỉ VÀO/i }));
  expect(screen.getByTestId("panel-in")).toBeInTheDocument();
  expect(screen.queryByTestId("panel-out")).not.toBeInTheDocument();
});
