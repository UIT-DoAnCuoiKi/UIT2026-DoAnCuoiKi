import { AXIOS_INSTANCE } from "@/api/axios-instance";
import type { CaptureResponse } from "@/api/generated/model";

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
