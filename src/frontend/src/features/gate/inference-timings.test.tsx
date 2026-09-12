import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { InferenceTimings } from "./inference-timings";

test("không hiện gì khi backend không trả thời gian (dev_mode tắt)", () => {
  const { container } = render(<InferenceTimings timings={null} />);
  expect(container).toBeEmptyDOMElement();
});

test("không hiện gì khi object rỗng", () => {
  const { container } = render(<InferenceTimings timings={{}} />);
  expect(container).toBeEmptyDOMElement();
});

// Bố cục màn Trạm cổng cố ý không cuộn ở phần thao tác (nút xác nhận ghim đáy),
// nên bảng chi tiết phải thu gọn mặc định, chỉ bung khi bấm. Bản đầu để bảng
// luôn mở làm nội dung bị đẩy khuất khỏi màn hình, người dùng không thấy.
test("mặc định chỉ hiện chip tổng, chưa hiện chi tiết", () => {
  render(<InferenceTimings timings={{ phat_hien_bien: 66.9, doc_bien_ocr: 3.6, tong: 70.4 }} />);
  expect(screen.getByRole("button", { name: /Suy luận/ })).toHaveTextContent("70 ms");
  expect(screen.queryByText("Phát hiện biển")).not.toBeInTheDocument();
});

test("bấm chip thì bung chi tiết, sắp theo thời gian giảm dần", async () => {
  render(
    <InferenceTimings
      timings={{ phat_hien_bien: 66.9, doc_bien_ocr: 3.6, phan_loai_loai_xe: 24.8, tong: 95.3 }}
    />,
  );
  await userEvent.click(screen.getByRole("button", { name: /Suy luận/ }));

  expect(screen.getByText("Phát hiện biển")).toBeInTheDocument();
  expect(screen.getByText("66.9")).toBeInTheDocument();

  // Bước nặng nhất phải đứng đầu để nhìn ra nút thắt ngay.
  const rows = screen.getAllByRole("row").map((r) => r.textContent ?? "");
  expect(rows[0]).toContain("Phát hiện biển");
});

test("bấm lần nữa thì thu lại", async () => {
  render(<InferenceTimings timings={{ phat_hien_bien: 66.9, tong: 66.9 }} />);
  const chip = screen.getByRole("button", { name: /Suy luận/ });
  await userEvent.click(chip);
  expect(screen.getByText("Phát hiện biển")).toBeInTheDocument();
  await userEvent.click(chip);
  expect(screen.queryByText("Phát hiện biển")).not.toBeInTheDocument();
});

test("tên giai đoạn lạ vẫn hiện nguyên khoá, không nuốt mất", async () => {
  render(<InferenceTimings timings={{ buoc_moi_chua_dat_ten: 12.5, tong: 12.5 }} />);
  await userEvent.click(screen.getByRole("button", { name: /Suy luận/ }));
  expect(screen.getByText("buoc_moi_chua_dat_ten")).toBeInTheDocument();
});
