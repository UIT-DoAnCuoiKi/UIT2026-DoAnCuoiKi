import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { GatePanel } from "./gate-panel";

const postInfer = vi.fn().mockResolvedValue({ reading_id: 5, capture_id: "c5", direction: "in", review_state: "confident", plate_text: "51F12345" });
vi.mock("./infer-capture", () => ({ postInfer: (...a: unknown[]) => postInfer(...a) }));
vi.mock("./use-camera", () => ({
  useCamera: () => ({
    videoRef: { current: null },
    devices: [{ deviceId: "cam-a", label: "Cam A" }],
    deviceId: "cam-a",
    setDeviceId: vi.fn(),
    listDevices: vi.fn(),
    start: vi.fn(),
    capture: vi.fn().mockResolvedValue(new Blob(["x"], { type: "image/jpeg" })),
    error: null,
  }),
}));
vi.mock("@/api/generated/sessions/sessions", () => ({
  useConfirmEntry: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useConfirmExit: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useManualSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));
vi.mock("@/api/generated/readings/readings", () => ({ usePatchPlate: () => ({ mutateAsync: vi.fn(), isPending: false }) }));
vi.mock("@/api/generated/config/config", () => ({ useGetToggles: () => ({ data: { read_plate: true, plate_color: true, vehicle_class: true } }) }));
vi.mock("@/lib/vehicle-groups", () => ({ useVehicleGroupMap: () => ({}), groupLabel: (_m: unknown, c?: string | null) => c ?? "—" }));

test("capturing runs infer then shows decision for the plate", async () => {
  render(<GatePanel direction="in" wsCapture={null} active onActivate={() => {}} />);
  await userEvent.click(screen.getByRole("button", { name: "Chụp" }));
  expect(postInfer).toHaveBeenCalled();
  expect(await screen.findByDisplayValue(/51F12345/)).toBeInTheDocument();
});
