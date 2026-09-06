import { postInfer } from "./infer-capture";
import { AXIOS_INSTANCE } from "@/api/axios-instance";

vi.mock("@/api/axios-instance", () => ({
  AXIOS_INSTANCE: { post: vi.fn().mockResolvedValue({ data: { reading_id: 1, capture_id: "x", direction: "in", review_state: "confident" } }) },
}));

test("postInfer sends multipart with expected fields", async () => {
  const blob = new Blob(["fake"], { type: "image/jpeg" });
  const res = await postInfer(blob, "out", "cap-1", "lane2");
  expect(res.reading_id).toBe(1);
  const post = (AXIOS_INSTANCE as unknown as { post: ReturnType<typeof vi.fn> }).post;
  expect(post).toHaveBeenCalledTimes(1);
  const [url, form] = post.mock.calls[0];
  expect(url).toBe("/captures/infer");
  expect(form).toBeInstanceOf(FormData);
  expect(form.get("direction")).toBe("out");
  expect(form.get("capture_id")).toBe("cap-1");
  expect(form.get("lane")).toBe("lane2");
});

test("postInfer sends extra camera images with matching roles", async () => {
  const blob = new Blob(["front"], { type: "image/jpeg" });
  const rear = new Blob(["rear"], { type: "image/jpeg" });
  await postInfer(blob, "in", "cap-2", "lane1", [{ role: "rear", blob: rear }], "front");
  const post = (AXIOS_INSTANCE as unknown as { post: ReturnType<typeof vi.fn> }).post;
  const [, form] = post.mock.calls[post.mock.calls.length - 1];
  expect(form.get("primary_role")).toBe("front");
  expect(form.getAll("extra_roles")).toEqual(["rear"]);
  expect(form.getAll("extra_images")).toHaveLength(1);
});
