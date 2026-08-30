import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SessionsPage } from "./sessions-page";

vi.mock("@/lib/vehicle-groups", () => ({
  useVehicleGroupMap: () => ({ xe_may: "Xe máy" }),
  groupLabel: (map: Record<string, string>, code?: string | null) => (code ? map[code] ?? code : "—"),
}));

vi.mock("@/api/generated/sessions/sessions", () => ({
  useListSessions: () => ({
    data: {
      total: 1,
      items: [
        {
          id: 5,
          status: "completed",
          plate_text: "51F-123",
          vehicle_group: "xe_may",
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

test("renders vehicle group display_name in sessions table", () => {
  render(
    <MemoryRouter>
      <SessionsPage />
    </MemoryRouter>,
  );
  expect(screen.getAllByText("Xe máy").length).toBeGreaterThan(0);
});

test("renders filter controls", () => {
  render(
    <MemoryRouter>
      <SessionsPage />
    </MemoryRouter>,
  );
  expect(screen.getByLabelText("Lọc nhóm xe")).toBeInTheDocument();
  expect(screen.getByLabelText("Lọc cách khớp")).toBeInTheDocument();
  expect(screen.getByLabelText("Giờ vào từ")).toBeInTheDocument();
  expect(screen.getByLabelText("Giờ vào đến")).toBeInTheDocument();
});
