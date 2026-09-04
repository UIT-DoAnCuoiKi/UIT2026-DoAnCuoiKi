import { render, screen } from "@testing-library/react";
import { RecognitionResult } from "./recognition-result";
import type { GateCapture } from "./use-gate-socket";

vi.mock("@/lib/image-blob", () => ({
  fetchImageObjectUrl: vi.fn().mockResolvedValue("blob:x"),
}));

const base: GateCapture = {
  reading_id: 1,
  capture_id: "c1",
  direction: "in",
  review_state: "confident",
  plate_text: "51F-123",
};

test("surfaces OCR and color confidence when present", () => {
  render(<RecognitionResult capture={{ ...base, ocr_conf: 0.91, color_conf: 0.8 }} />);
  expect(screen.getByText("91%")).toBeInTheDocument();
  expect(screen.getByText("80%")).toBeInTheDocument();
});

test("shows invalid-format warning", () => {
  render(<RecognitionResult capture={{ ...base, plate_valid: false }} />);
  expect(screen.getByText(/sai định dạng/i)).toBeInTheDocument();
});

test("shows a second preview for the color-processed crop", () => {
  render(
    <RecognitionResult capture={{ ...base, image_asset_id: 11, plate_crop_asset_id: 12 }} />,
  );
  expect(screen.getByText(/biển đã xử lý màu/i)).toBeInTheDocument();
});

test("no crop preview when plate_crop_asset_id is absent", () => {
  render(<RecognitionResult capture={{ ...base, image_asset_id: 11 }} />);
  expect(screen.queryByText(/biển đã xử lý màu/i)).not.toBeInTheDocument();
});
