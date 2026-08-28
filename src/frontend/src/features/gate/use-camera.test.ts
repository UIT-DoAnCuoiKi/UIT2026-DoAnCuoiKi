import { renderHook, act, waitFor } from "@testing-library/react";
import { useCamera } from "./use-camera";

function mockMediaDevices() {
  const enumerate = vi.fn().mockResolvedValue([
    { kind: "videoinput", deviceId: "cam-a", label: "Cam A" },
    { kind: "audioinput", deviceId: "mic", label: "Mic" },
  ]);
  const getUserMedia = vi.fn().mockResolvedValue({ getTracks: () => [{ stop: vi.fn() }] });
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { enumerateDevices: enumerate, getUserMedia },
  });
  return { enumerate, getUserMedia };
}

test("listDevices keeps only video inputs and preselects first", async () => {
  mockMediaDevices();
  const { result } = renderHook(() => useCamera());
  await act(async () => {
    await result.current.listDevices();
  });
  await waitFor(() => expect(result.current.devices).toHaveLength(1));
  expect(result.current.devices[0].deviceId).toBe("cam-a");
  expect(result.current.deviceId).toBe("cam-a");
});

test("start sets no error on success", async () => {
  mockMediaDevices();
  const { result } = renderHook(() => useCamera());
  await act(async () => {
    await result.current.start("cam-a");
  });
  expect(result.current.error).toBeNull();
});

test("start sets error when getUserMedia rejects", async () => {
  const { getUserMedia } = mockMediaDevices();
  getUserMedia.mockRejectedValueOnce(new Error("denied"));
  const { result } = renderHook(() => useCamera());
  await act(async () => {
    await result.current.start("cam-a");
  });
  expect(result.current.error).toMatch(/camera/i);
});
