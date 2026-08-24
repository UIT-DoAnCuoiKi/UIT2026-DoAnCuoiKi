import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SessionsPage } from "./sessions-page";

vi.mock("@/api/generated/sessions/sessions", () => ({
  useListSessions: () => ({
    data: {
      total: 1,
      items: [
        {
          id: 5,
          status: "completed",
          plate_text: "51F-123",
          vehicle_group: "car",
          entry_time: "2026-08-23T08:00:00Z",
          exit_time: "2026-08-23T09:00:00Z",
          fee_amount: 15000,
          match_flag: "exact",
        },
      ],
    },
    isLoading: false,
  }),
}));

test("renders a session row with plate and status", () => {
  render(
    <MemoryRouter>
      <SessionsPage />
    </MemoryRouter>,
  );
  expect(screen.getByText("51F-123")).toBeInTheDocument();
  expect(screen.getByText("Hoàn tất")).toBeInTheDocument();
});
