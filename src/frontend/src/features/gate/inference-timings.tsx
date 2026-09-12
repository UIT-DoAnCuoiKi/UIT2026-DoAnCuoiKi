import { useState } from "react";

/** Thời gian suy luận từng giai đoạn, hiện dạng chip gọn trong dải độ tin cậy.
 *
 * Backend chỉ trả `timings_ms` khi bật dev_mode ở màn Cấu hình, nên không cần
 * kiểm tra lại cờ đó ở đây: có dữ liệu nghĩa là được phép hiện.
 *
 * Cố tình làm chip thu gọn thay vì bảng luôn mở: bố cục màn Trạm cổng không
 * cuộn ở phần thao tác (nút xác nhận ghim đáy), thêm một khối cao vào đó sẽ đẩy
 * nội dung khuất khỏi màn hình. Chi tiết chỉ bung khi bấm.
 */
const LABELS: Record<string, string> = {
  doi_mau: "Đổi màu ảnh",
  phat_hien_bien: "Phát hiện biển",
  mau_bien: "Màu biển",
  doc_bien_ocr: "Đọc biển (OCR)",
  dinh_vi_xe: "Định vị xe",
  phan_loai_loai_xe: "Phân loại loại xe",
  phan_loai_kieu_dang: "Phân loại kiểu dáng",
};

const RES_LABELS: Record<string, { label: string; unit: string }> = {
  ram_tien_trinh_mb: { label: "RAM tiến trình", unit: "MB" },
  so_loi_dung: { label: "Số lõi dùng", unit: "" },
  cpu_time_ms: { label: "CPU-time", unit: "ms" },
};

export function InferenceTimings({
  timings,
  resources,
}: {
  timings?: Record<string, number> | null;
  resources?: Record<string, number> | null;
}) {
  const [open, setOpen] = useState(false);
  if (!timings || Object.keys(timings).length === 0) return null;

  const total = timings.tong ?? 0;
  const rows = Object.entries(timings)
    .filter(([k]) => k !== "tong")
    .sort((a, b) => b[1] - a[1]);

  return (
    <span className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="rounded border border-line px-1.5 py-0.5 text-[13px] hover:bg-surface"
        title="Bấm để xem thời gian từng giai đoạn"
      >
        Suy luận: <span className="font-medium text-ink tabular-nums">{total.toFixed(0)} ms</span>
        <span className="ml-1 text-[11px] text-muted">{open ? "▲" : "▼"}</span>
      </button>

      {open && (
        <div className="absolute left-0 top-full z-20 mt-1 w-60 rounded-[var(--radius-control)] border border-line bg-bg p-2 shadow-lg">
          <table className="w-full text-[12px]">
            <tbody>
              {rows.map(([key, ms]) => (
                <tr key={key}>
                  <td className="py-0.5 pr-2 text-muted">{LABELS[key] ?? key}</td>
                  <td className="py-0.5 pr-1 text-right tabular-nums text-ink">{ms.toFixed(1)}</td>
                  <td className="w-9 py-0.5 text-right tabular-nums text-muted">
                    {total > 0 ? `${Math.round((ms / total) * 100)}%` : ""}
                  </td>
                </tr>
              ))}
              {total > 0 && (
                <tr className="border-t border-line">
                  <td className="py-0.5 pr-2 font-medium text-ink">Tổng</td>
                  <td className="py-0.5 pr-1 text-right font-medium tabular-nums text-ink">
                    {total.toFixed(1)}
                  </td>
                  <td />
                </tr>
              )}
            </tbody>
          </table>
          {resources && Object.keys(resources).length > 0 && (
            <table className="mt-2 w-full border-t border-line pt-1 text-[12px]">
              <tbody>
                {Object.entries(resources).map(([key, val]) => {
                  const meta = RES_LABELS[key];
                  return (
                    <tr key={key}>
                      <td className="py-0.5 pr-2 text-muted">{meta?.label ?? key}</td>
                      <td className="py-0.5 text-right tabular-nums text-ink">
                        {val.toFixed(key === "so_loi_dung" ? 2 : 1)}
                        {meta?.unit ? ` ${meta.unit}` : ""}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
          <p className="mt-1 text-[11px] text-muted">
            Thời gian tính bằng mili giây. Số lõi dùng bằng CPU-time chia thời gian thực, khoảng 1 là
            đơn luồng. Chỉ hiện khi bật dev_mode.
          </p>
        </div>
      )}
    </span>
  );
}
