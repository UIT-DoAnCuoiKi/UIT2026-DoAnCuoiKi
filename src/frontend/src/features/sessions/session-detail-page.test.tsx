import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { SessionDetailPage } from "./session-detail-page";

vi.mock("@/lib/vehicle-groups", () => ({
  useVehicleGroupMap: () => ({ xe_may: "Xe máy" }),
  groupLabel: (map: Record<string, string>, code?: string | null) => (code ? map[code] ?? code : "—"),
}));

// Ảnh bằng chứng tự tải khi mở phiên: mock để không gọi mạng thật trong test.
vi.mock("@/lib/image-blob", () => ({ fetchImageObjectUrl: vi.fn().mockResolvedValue("blob:mock") }));

const baseSessionData = {
  id: 9,
  status: "completed",
  plate_text: "51F-123",
  vehicle_group: "xe_may",
  entry_time: "2026-08-23T08:00:00Z",
  exit_time: "2026-08-23T09:00:00Z",
  fee_amount: 15000,
  match_flag: "exact",
  entry_reading: { id: 1, review_state: "confident", plate_text: "51F-123", image_asset_id: 11, plate_crop_asset_id: 21, lane: "lane-e2e" },
  exit_reading: { id: 2, review_state: "confident", plate_text: "51F-123", image_asset_id: 12, lane: "lane-e2e" },
  created_by_name: "creator",
  closed_by_name: "closer2",
  lot_name: "Bãi A",
  zone_name: "Khu 1",
  fee_rule_snapshot: { mode: "flat", unit_price: 5000 },
  payments: [
    { id: 1, amount: 5000, method: "qr", kind: "payment", staff_name: "closer2", paid_at: "2026-08-23T09:00:00Z" },
  ],
};
// Ghi đè được per-test (vd. thêm entry_reading.images cho lượt đa camera) mà
// không phải viết lại toàn bộ mock — mặc định trả đúng dữ liệu như trước.
const getSessionDetail = vi.fn().mockReturnValue({ data: baseSessionData, isLoading: false, refetch: vi.fn() });
vi.mock("@/api/generated/sessions/sessions", () => ({
  useSessionDetail: () => getSessionDetail(),
  useUpdateSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useDisputeSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useResolveSession: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

test("shows staff, payments and vehicle group display_name", () => {
  render(
    <MemoryRouter initialEntries={["/sessions/9"]}>
      <Routes>
        <Route path="/sessions/:id" element={<SessionDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
  // "Xe máy" xuất hiện ở Field nhóm xe và trong option của select loại xe.
  expect(screen.getAllByText("Xe máy").length).toBeGreaterThan(0);
  expect(screen.getByText("creator")).toBeInTheDocument();
  expect(screen.getByText("qr")).toBeInTheDocument();
});

test("shows the color-processed crop evidence", () => {
  render(
    <MemoryRouter initialEntries={["/sessions/9"]}>
      <Routes>
        <Route path="/sessions/:id" element={<SessionDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
  expect(screen.getByText(/biển đã xử lý màu/i)).toBeInTheDocument();
});

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

test("shows lane for entry and exit, and a receipt-style header line", () => {
  // Dữ liệu này vốn đã có sẵn trên PlateReading.lane, chỉ trước đây không lộ
  // ra màn chi tiết — nhân viên tưởng hệ thống không lưu lane nào cả.
  render(
    <MemoryRouter initialEntries={["/sessions/9"]}>
      <Routes>
        <Route path="/sessions/:id" element={<SessionDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
  expect(screen.getAllByText("lane-e2e").length).toBe(2);
  // Phiên đã hoàn tất (có exit_time): dòng đầu trang hiện "Giờ ra", không phải
  // "Đã đậu" (chỉ dùng cho phiên còn trong bãi).
  expect(screen.getByText(/Giờ ra:/)).toBeInTheDocument();
});

test("shows elapsed time instead of exit time while the vehicle is still in the lot", () => {
  getSessionDetail.mockReturnValueOnce({
    data: { ...baseSessionData, status: "in_lot", exit_time: null, exit_reading: null },
    isLoading: false,
    refetch: vi.fn(),
  });
  render(
    <MemoryRouter initialEntries={["/sessions/9"]}>
      <Routes>
        <Route path="/sessions/:id" element={<SessionDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
  expect(screen.getByText(/Đã đậu:/)).toBeInTheDocument();
  expect(screen.queryByText(/^Giờ ra:/)).not.toBeInTheDocument();
});

test("shows both camera images for a multi-camera entry reading", () => {
  // Trước đây chỉ hiện ảnh camera chính dù backend đã lưu đủ ảnh camera phụ.
  getSessionDetail.mockReturnValueOnce({
    data: {
      ...baseSessionData,
      entry_reading: {
        ...baseSessionData.entry_reading,
        images: [
          { role: "front", image_asset_id: 11, is_primary: true },
          { role: "rear", image_asset_id: 31, is_primary: false },
        ],
      },
    },
    isLoading: false,
    refetch: vi.fn(),
  });
  render(
    <MemoryRouter initialEntries={["/sessions/9"]}>
      <Routes>
        <Route path="/sessions/:id" element={<SessionDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
  expect(screen.getByText("Trước")).toBeInTheDocument();
  expect(screen.getByText("Sau")).toBeInTheDocument();
});
