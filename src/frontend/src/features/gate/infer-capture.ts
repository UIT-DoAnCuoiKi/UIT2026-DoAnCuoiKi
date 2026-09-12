import { AXIOS_INSTANCE } from "@/api/axios-instance";
import type { CaptureResponse } from "@/api/generated/model";

/** Id duy nhất cho mỗi lượt chụp.
 *
 * Không gọi thẳng `crypto.randomUUID()`: hàm đó chỉ tồn tại ở ngữ cảnh an toàn
 * (HTTPS hoặc localhost). Mở portal qua IP trong LAN, ví dụ khi chạy trên
 * Raspberry Pi và xem từ máy khác, nó là undefined nên ném lỗi trước cả khi
 * kịp gửi request, và triệu chứng nhìn thấy chỉ là "nhận dạng thất bại".
 * `getRandomValues` thì vẫn dùng được ở ngữ cảnh không an toàn.
 */
export function newCaptureId(): string {
  const c = globalThis.crypto;
  if (typeof c?.randomUUID === "function") return c.randomUUID();
  if (typeof c?.getRandomValues === "function") {
    const bytes = c.getRandomValues(new Uint8Array(16));
    return Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  }
  return `${Date.now().toString(16)}-${Math.random().toString(16).slice(2, 10)}`;
}

export async function postInfer(
  blob: Blob,
  direction: "in" | "out",
  captureId: string,
  lane?: string,
  // Ảnh camera phụ khi làn có 2-3 camera: lưu làm bằng chứng (hoặc, nếu làn
  // cấu hình recognition_mode=best_of, có thể được backend chọn làm ảnh chính
  // thay cho `blob` nếu đọc rõ hơn) — không tự chạy nhận dạng ở phía client.
  extraImages?: { role: string; blob: Blob }[],
  primaryRole?: string,
): Promise<CaptureResponse> {
  const form = new FormData();
  form.append("capture_id", captureId);
  form.append("direction", direction);
  if (lane) form.append("lane", lane);
  if (primaryRole) form.append("primary_role", primaryRole);
  form.append("image", blob, `${captureId}.jpg`);
  for (const { role, blob: extraBlob } of extraImages ?? []) {
    form.append("extra_images", extraBlob, `${captureId}-${role}.jpg`);
    form.append("extra_roles", role);
  }
  const res = await AXIOS_INSTANCE.post<CaptureResponse>("/captures/infer", form);
  return res.data;
}
