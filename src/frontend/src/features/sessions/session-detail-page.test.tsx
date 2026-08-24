import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { SessionDetailPage } from "./session-detail-page";

vi.mock("@/api/generated/sessions/sessions", () => ({
  useSessionDetail: () => ({
    data: {
      id: 9,
      status: "completed",
      plate_text: "51F-123",
      vehicle_group: "car",
      entry_time: "2026-08-23T08:00:00Z",
      exit_time: "2026-08-23T09:00:00Z",
      fee_amount: 15000,
      match_flag: "exact",
      entry_reading: { id: 1, review_state: "confident", plate_text: "51F-123", image_asset_id: 11 },
      exit_reading: { id: 2, review_state: "confident", plate_text: "51F-123", image_asset_id: 12 },
    },
    isLoading: false,
    refetch: vi.fn(),
  }),
  useDisputeSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useResolveSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

test("shows detail fields and retention notice", () => {
  render(
    <MemoryRouter initialEntries={["/sessions/9"]}>
      <Routes>
        <Route path="/sessions/:id" element={<SessionDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
  expect(screen.getByText("51F-123")).toBeInTheDocument();
  expect(screen.getByText(/30 ngày/)).toBeInTheDocument();
});
