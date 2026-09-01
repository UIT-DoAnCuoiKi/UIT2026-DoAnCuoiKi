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

test("status is no-device when there are no video inputs", async () => {
  const { enumerate } = mockMediaDevices();
  enumerate.mockResolvedValueOnce([{ kind: "audioinput", deviceId: "mic", label: "Mic" }]);
  const { result } = renderHook(() => useCamera());
  await act(async () => {
    await result.current.listDevices();
  });
  await waitFor(() => expect(result.current.status).toBe("no-device"));
});

test("status becomes streaming after successful start", async () => {
  mockMediaDevices();
  const { result } = renderHook(() => useCamera());
  await act(async () => {
    await result.current.start("cam-a");
  });
  await waitFor(() => expect(result.current.status).toBe("streaming"));
});

test("status becomes denied when getUserMedia rejects with NotAllowedError", async () => {
  const { getUserMedia } = mockMediaDevices();
  getUserMedia.mockRejectedValueOnce(Object.assign(new Error("no"), { name: "NotAllowedError" }));
  const { result } = renderHook(() => useCamera());
  await act(async () => {
    await result.current.start("cam-a");
  });
  await waitFor(() => expect(result.current.status).toBe("denied"));
});

test("requestPermission keeps denied status and skips listing on failure", async () => {
  const { getUserMedia, enumerate } = mockMediaDevices();
  getUserMedia.mockRejectedValueOnce(Object.assign(new Error("no"), { name: "NotAllowedError" }));
  const { result } = renderHook(() => useCamera());
  await act(async () => {
    await result.current.requestPermission();
  });
  await waitFor(() => expect(result.current.status).toBe("denied"));
  expect(enumerate).not.toHaveBeenCalled();
});

test("requestPermission lists devices and ends streaming on success", async () => {
  mockMediaDevices();
  const { result } = renderHook(() => useCamera());
  await act(async () => {
    await result.current.requestPermission();
  });
  await waitFor(() => expect(result.current.status).toBe("streaming"));
  expect(result.current.devices).toHaveLength(1);
});
