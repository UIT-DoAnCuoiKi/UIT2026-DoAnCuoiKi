import { render, screen } from "@testing-library/react";
import { RecognitionResult } from "./recognition-result";
import type { GateCapture } from "./use-gate-socket";

vi.mock("@/lib/vehicle-groups", () => ({
  groupLabel: (_m: Record<string, string>, c?: string | null) => (c === "xe_may" ? "Xe máy" : c ?? "—"),
}));

const base: GateCapture = {
  reading_id: 1,
  capture_id: "c1",
  direction: "in",
  review_state: "confident",
  plate_text: "51F-123",
};

test("renders type, group label and color label", () => {
  render(
    <RecognitionResult
      capture={{ ...base, vehicle_type: "Xe tay ga", vehicle_group: "xe_may", color: "white" }}
      groupMap={{}}
    />,
  );
  expect(screen.getByText("Xe tay ga")).toBeInTheDocument();
  expect(screen.getByText("Xe máy")).toBeInTheDocument();
  expect(screen.getByText("Trắng")).toBeInTheDocument();
});

test("shows invalid-format and duplicate warnings", () => {
  render(<RecognitionResult capture={{ ...base, plate_valid: false, duplicate: true }} groupMap={{}} />);
  expect(screen.getByText(/sai định dạng/i)).toBeInTheDocument();
  expect(screen.getByText(/trùng phiên/i)).toBeInTheDocument();
});
