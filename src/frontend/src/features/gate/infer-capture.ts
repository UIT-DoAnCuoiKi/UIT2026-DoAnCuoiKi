import { AXIOS_INSTANCE } from "@/api/axios-instance";
import type { CaptureResponse } from "@/api/generated/model";

export async function postInfer(
  blob: Blob,
  direction: "in" | "out",
  captureId: string,
  lane?: string,
): Promise<CaptureResponse> {
  const form = new FormData();
  form.append("capture_id", captureId);
  form.append("direction", direction);
  if (lane) form.append("lane", lane);
  form.append("image", blob, `${captureId}.jpg`);
  const res = await AXIOS_INSTANCE.post<CaptureResponse>("/captures/infer", form);
  return res.data;
}
