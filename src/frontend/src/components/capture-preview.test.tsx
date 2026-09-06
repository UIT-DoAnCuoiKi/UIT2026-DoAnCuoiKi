import { render, screen, waitFor } from "@testing-library/react";
import { CapturePreview } from "./capture-preview";

const fetchImageObjectUrl = vi.fn();
vi.mock("@/lib/image-blob", () => ({
  fetchImageObjectUrl: (id: number) => fetchImageObjectUrl(id),
}));

beforeEach(() => fetchImageObjectUrl.mockReset());

test("renders the local frame without hitting the server", () => {
  render(<CapturePreview localUrl="blob:local-1" />);
  expect(screen.getByRole("img")).toHaveAttribute("src", "blob:local-1");
  expect(fetchImageObjectUrl).not.toHaveBeenCalled();
});

test("shows placeholder when there is no image", () => {
  render(<CapturePreview />);
  expect(screen.getByText(/không có ảnh/i)).toBeInTheDocument();
});

test("fetches by asset id when no local frame is available", async () => {
  fetchImageObjectUrl.mockResolvedValueOnce("blob:server-9");
  render(<CapturePreview imageAssetId={9} />);
  await waitFor(() => expect(screen.getByRole("img")).toHaveAttribute("src", "blob:server-9"));
  expect(fetchImageObjectUrl).toHaveBeenCalledWith(9);
});
