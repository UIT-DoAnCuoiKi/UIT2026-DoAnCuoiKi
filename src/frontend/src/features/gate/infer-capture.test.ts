import { postInfer, newCaptureId } from "./infer-capture";
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

// Lỗi thật đã gặp: mở portal qua IP trong LAN (http://192.168.x.x, không phải
// localhost) thì trình duyệt coi là ngữ cảnh không an toàn và không có
// crypto.randomUUID. Gọi thẳng vào là ném lỗi trước khi kịp gửi request, người
// dùng chỉ thấy "Nhận dạng thất bại" mà không có request nào tới backend.
describe("newCaptureId", () => {
  const realCrypto = globalThis.crypto;
  afterEach(() => {
    Object.defineProperty(globalThis, "crypto", { value: realCrypto, configurable: true });
  });

  test("dùng randomUUID khi có (ngữ cảnh an toàn)", () => {
    Object.defineProperty(globalThis, "crypto", {
      value: { randomUUID: () => "uuid-tu-trinh-duyet" },
      configurable: true,
    });
    expect(newCaptureId()).toBe("uuid-tu-trinh-duyet");
  });

  test("lùi về getRandomValues khi thiếu randomUUID", () => {
    Object.defineProperty(globalThis, "crypto", {
      value: {
        getRandomValues: (arr: Uint8Array) => {
          arr.fill(0xab);
          return arr;
        },
      },
      configurable: true,
    });
    expect(newCaptureId()).toBe("ab".repeat(16));
  });

  test("vẫn sinh được id khi không có crypto nào", () => {
    Object.defineProperty(globalThis, "crypto", { value: undefined, configurable: true });
    const id = newCaptureId();
    expect(id).toMatch(/^[0-9a-f]+-[0-9a-z]+$/);
    expect(id.length).toBeGreaterThan(8);
  });
});
