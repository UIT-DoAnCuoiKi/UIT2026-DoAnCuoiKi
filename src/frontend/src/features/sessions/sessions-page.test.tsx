import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SessionsPage } from "./sessions-page";

vi.mock("@/lib/vehicle-groups", () => ({
  useVehicleGroupMap: () => ({ xe_may: "Xe máy" }),
  groupLabel: (map: Record<string, string>, code?: string | null) => (code ? map[code] ?? code : "—"),
}));

let lastParams: any;

vi.mock("@/api/generated/sessions/sessions", () => ({
  useListSessions: (p: any) => {
    lastParams = p;
    return {
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
            vehicle_type: "o_to_con",
            closed_by_name: "closer",
            payment_method: "cash",
          },
        ],
      },
      isLoading: false,
    };
  },
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

test("same-day entry range produces a non-empty window", () => {
  render(
    <MemoryRouter>
      <SessionsPage />
    </MemoryRouter>,
  );
  fireEvent.change(screen.getByLabelText("Giờ vào từ"), { target: { value: "2026-08-23" } });
  fireEvent.change(screen.getByLabelText("Giờ vào đến"), { target: { value: "2026-08-23" } });
  expect(lastParams.entry_from).not.toBeNull();
  expect(lastParams.entry_to).not.toBeNull();
  expect(new Date(lastParams.entry_from).getTime()).toBeLessThan(new Date(lastParams.entry_to).getTime());
});

test("renders vehicle_type, staff, payment method columns", () => {
  render(
    <MemoryRouter>
      <SessionsPage />
    </MemoryRouter>,
  );
  expect(screen.getByText("o_to_con")).toBeInTheDocument();
  expect(screen.getByText("closer")).toBeInTheDocument();
  expect(screen.getByText("cash")).toBeInTheDocument();
});
