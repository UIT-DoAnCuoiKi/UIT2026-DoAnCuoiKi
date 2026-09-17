const DASH = "—";

const vnd = new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND" });
const dt = new Intl.DateTimeFormat("vi-VN", {
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
});

/** Backend lưu giờ UTC nhưng trả chuỗi không kèm Z, thiếu nó thì trình duyệt
    hiểu nhầm thành giờ địa phương và hiển thị sớm hơn đúng phần chênh múi giờ. */
function parseUtc(iso: string): Date {
  return new Date(/(Z|[+-]\d{2}:?\d{2})$/.test(iso) ? iso : `${iso}Z`);
}

export function formatVnd(n: number | null | undefined): string {
  if (n === null || n === undefined) return DASH;
  return vnd.format(n);
}

export function formatDateTime(iso?: string | null): string {
  if (!iso) return DASH;
  const d = parseUtc(iso);
  if (Number.isNaN(d.getTime())) return DASH;
  return dt.format(d);
}

export function formatDuration(startISO?: string | null, endISO?: string | null): string {
  if (!startISO || !endISO) return DASH;
  const ms = parseUtc(endISO).getTime() - parseUtc(startISO).getTime();
  if (!Number.isFinite(ms) || ms < 0) return DASH;
  const mins = Math.floor(ms / 60000);
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  if (h === 0) return `${m} phút`;
  return `${h} giờ ${m} phút`;
}

/** Thời lượng tính sẵn theo phút (backend trả `minutes` ở màn xem trước lượt RA). */
export function formatMinutes(minutes?: number | null): string {
  if (minutes === null || minutes === undefined || !Number.isFinite(minutes)) return DASH;
  const mins = Math.max(0, Math.floor(minutes));
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  if (h === 0) return `${m} phút`;
  return `${h} giờ ${m} phút`;
}

export function formatPlate(s?: string | null): string {
  if (!s) return DASH;
  return s.trim().toUpperCase();
}
