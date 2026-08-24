import { AXIOS_INSTANCE } from "@/api/axios-instance";

// Authed blob fetch for /images/{id}. Each call is audited server-side (privacy).
export async function fetchImageObjectUrl(imageId: number): Promise<string> {
  const res = await AXIOS_INSTANCE.get(`/images/${imageId}`, { responseType: "blob" });
  return URL.createObjectURL(res.data as Blob);
}
