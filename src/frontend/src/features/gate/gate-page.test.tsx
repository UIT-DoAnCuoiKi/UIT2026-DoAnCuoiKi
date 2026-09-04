import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GatePage } from "./gate-page";

const confirm = vi.fn();
vi.mock("./use-gate-socket", () => ({
  useGateSocket: () => ({
    capturesByDirection: { in: null, out: null },
    events: [],
    connected: true,
    degraded: false,
  }),
}));
vi.mock("./gate-panel", async () => {
  const { forwardRef, useImperativeHandle } = await import("react");
  return {
    GatePanel: forwardRef(function GP(
      { direction, active }: { direction: string; active: boolean },
      ref: unknown,
    ) {
      useImperativeHandle(ref as never, () => ({
        capture: () => {},
        focusPlate: () => {},
        confirm,
        manual: () => {},
        cancel: () => {},
        payMethod: () => {},
      }));
      return <div data-testid={`panel-${direction}`}>{active ? "ACTIVE" : "idle"}</div>;
    }),
  };
});

beforeEach(() => {
  localStorage.clear();
  confirm.mockClear();
});

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

test("Enter key routes confirm to the active panel", async () => {
  render(<GatePage />);
  await userEvent.keyboard("{Enter}");
  expect(confirm).toHaveBeenCalled();
});
