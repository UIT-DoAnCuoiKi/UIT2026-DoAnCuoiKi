import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { CameraView } from "./camera-view";
import { MultiCameraView } from "./multi-camera-view";
import { CapturePreview } from "@/components/capture-preview";
import { CameraImageGrid, type CameraImage } from "@/components/camera-image-grid";
import { DecisionPanel, type DecisionPanelHandle } from "./decision-panel";
import { useCamera } from "./use-camera";
import { useCameras } from "./use-cameras";
import { postInfer } from "./infer-capture";
import type { GateCapture } from "./use-gate-socket";
import type { LaneCameraOut } from "@/api/generated/model";
import { useGetToggles } from "@/api/generated/config/config";
import { cameraRoleLabel } from "@/lib/labels";
import { SurfaceCard } from "@/components/surface-card";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";

export type GatePanelHandle = {
  capture: () => void;
  focusPlate: () => void;
  confirm: () => void;
  manual: () => void;
  reset: () => void;
  cancel: () => void;
  payMethod: (n: number) => void;
};

export const GatePanel = forwardRef<
  GatePanelHandle,
  {
    direction: "in" | "out";
    wsCapture: GateCapture | null;
    active: boolean;
    onActivate: () => void;
    onPayOpenChange?: (open: boolean) => void;
    wide?: boolean;
    /** Làn đang trực + camera đã cấu hình. Không cấu hình camera nào (mặc định,
     * hoặc chưa chọn làn) thì dùng webcam đơn như trước — không đổi hành vi cũ. */
    laneName?: string | null;
    laneCameras?: LaneCameraOut[];
  }
>(function GatePanel(
  { direction, wsCapture, active, onActivate, onPayOpenChange, wide = false, laneName, laneCameras = [] },
  ref,
) {
  // Tải ảnh thay camera thật chỉ để test — ẩn khỏi vận hành thật trừ khi bật
  // dev_mode ở màn Cấu hình (tránh ai đó thay ảnh gốc bằng ảnh tuỳ ý).
  const { data: toggles } = useGetToggles();
  const allowUpload = toggles?.dev_mode ?? false;

  const hasMultiCam = laneCameras.length > 0;
  const laneCameraKey = laneCameras.map((c) => c.id).join(",");
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const roles = useMemo(() => laneCameras.map((c) => c.role), [laneCameraKey]);
  const multi = useCameras(roles);
  // "Chụp" chỉ có nghĩa khi có ít nhất 1 camera đang live — nếu cả làn đều
  // chưa kết nối (đang test bằng tải ảnh tay), nút gửi phải gọi đúng tên việc
  // nó làm (gửi ảnh đã tải), không phải "Chụp" vào chỗ không có camera nào.
  const anyLiveCamera = multi.slots.some((s) => s.status === "streaming");
  const sendActionLabel = anyLiveCamera ? `Chụp (${laneCameras.length} cam)` : "Gửi ảnh đã tải";
  const cam = useCamera();
  const [capture, setCapture] = useState<GateCapture | null>(null);
  const [busy, setBusy] = useState(false);
  const decisionRef = useRef<DecisionPanelHandle | null>(null);

  // Giữ object URL của khung hình cục bộ; thu hồi khi thay/đóng để tránh rò bộ nhớ.
  const localUrlRef = useRef<string | null>(null);
  const setCaptureWithUrl = (next: GateCapture | null, localUrl?: string) => {
    if (localUrlRef.current) URL.revokeObjectURL(localUrlRef.current);
    localUrlRef.current = localUrl ?? null;
    setCapture(next);
  };

  // Không cấu hình camera cho làn: webcam đơn như trước, tự xin quyền lúc mount.
  useEffect(() => {
    if (!hasMultiCam) cam.requestPermission();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasMultiCam]);
  useEffect(() => {
    if (!hasMultiCam && cam.deviceId) cam.start(cam.deviceId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasMultiCam, cam.deviceId]);
  // Có cấu hình camera cho làn: tự xin quyền cho từng camera loại "browser"
  // (RTSP không mở stream ở trình duyệt, xem MultiCameraView).
  useEffect(() => {
    if (!hasMultiCam) return;
    for (const c of laneCameras) {
      if (c.source_kind === "browser") multi.requestPermission(c.role);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasMultiCam, laneCameraKey]);
  useEffect(() => {
    if (wsCapture) setCaptureWithUrl(wsCapture);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [wsCapture]);
  useEffect(
    () => () => {
      if (localUrlRef.current) URL.revokeObjectURL(localUrlRef.current);
    },
    [],
  );

  const doInfer = async (blob: Blob, extraImages?: { role: string; blob: Blob }[], primaryRole?: string) => {
    if (busy) return;
    setBusy(true);
    try {
      const localUrl = URL.createObjectURL(blob);
      const res = await postInfer(blob, direction, crypto.randomUUID(), laneName ?? undefined, extraImages, primaryRole);
      setCaptureWithUrl({ ...(res as unknown as GateCapture), local_image_url: localUrl }, localUrl);
    } catch {
      toast.error("Nhận dạng thất bại");
    } finally {
      setBusy(false);
    }
  };

  // Ảnh tải tay theo từng ô camera (khi ô đó không có luồng trực tiếp) — giữ lại
  // để gộp cùng ảnh vừa chụp từ các camera khác, không gửi riêng lẻ ngay.
  const [uploadedByRole, setUploadedByRole] = useState<Record<string, File>>({});

  /** Gộp ảnh: ưu tiên khung hình trực tiếp vừa chụp, thiếu thì lấy ảnh đã tải
   * tay cho đúng vai trò đó. `requireAllBrowserRoles` bắt chờ đủ ảnh của MỌI
   * camera nguồn browser của làn rồi mới gửi — dùng cho luồng tải tay, vì tải
   * xong 1 ô là 1 lần gọi riêng, gửi ngay theo ô đầu tiên sẽ bỏ sót ô sau (đã
   * xảy ra thật: tải "Trước" trước thì gửi liền với 0 ảnh phụ, tải "Sau" sau
   * đó lại thiếu ảnh chính nên bị treo, không bao giờ gửi). Nút "Chụp (N cam)"
   * là hành động chủ động của người dùng nên vẫn gửi ngay với ảnh đang có. */
  const submitMultiShots = async (uploaded: Record<string, File>, requireAllBrowserRoles = false) => {
    if (busy) return;
    const live = await multi.captureAll();
    const liveRoles = new Set(live.map((s) => s.role));
    const shots = [
      ...live,
      ...Object.entries(uploaded)
        .filter(([role]) => !liveRoles.has(role))
        .map(([role, file]) => ({ role, blob: file as Blob })),
    ];
    if (shots.length === 0) {
      toast.error("Chưa có khung hình từ camera nào của làn");
      return;
    }
    if (requireAllBrowserRoles) {
      const gotRoles = new Set(shots.map((s) => s.role));
      const missing = laneCameras
        .filter((c) => c.source_kind === "browser" && !gotRoles.has(c.role))
        .map((c) => cameraRoleLabel(c.role));
      if (missing.length > 0) {
        toast.message(`Đã lưu ảnh, còn thiếu: ${missing.join(", ")}. Bấm "${sendActionLabel}" để gửi ngay nếu vậy là đủ.`);
        return;
      }
    }
    const primaryRole = laneCameras.find((c) => c.is_primary)?.role ?? shots[0].role;
    const primaryShot = shots.find((s) => s.role === primaryRole);
    if (!primaryShot) return; // còn thiếu ảnh camera chính, chờ chụp/tải nốt
    const extras = shots.filter((s) => s !== primaryShot);
    await doInfer(primaryShot.blob, extras, primaryShot.role);
    setUploadedByRole({});
  };

  const doCapture = async () => {
    if (hasMultiCam) {
      await submitMultiShots(uploadedByRole);
      return;
    }
    const blob = await cam.capture();
    if (!blob) {
      toast.error("Chưa có khung hình từ camera");
      return;
    }
    await doInfer(blob);
  };

  // Tạm thời cho máy không có camera vẫn test được luồng nhận dạng bằng ảnh có
  // sẵn (chọn file). Dùng chung đường xử lý với doCapture (postInfer), chỉ khác
  // nguồn ảnh; dễ bỏ khi không cần nữa.
  const doUpload = (file: File) => void doInfer(file);
  const doUploadForRole = (role: string, file: File) => {
    const next = { ...uploadedByRole, [role]: file };
    setUploadedByRole(next);
    void submitMultiShots(next, true);
  };

  useImperativeHandle(ref, () => ({
    capture: doCapture,
    focusPlate: () => decisionRef.current?.focusPlate(),
    confirm: () => decisionRef.current?.confirm(),
    manual: () => decisionRef.current?.manual(),
    reset: () => decisionRef.current?.reset(),
    cancel: () => decisionRef.current?.cancel(),
    payMethod: (n) => decisionRef.current?.payMethod(n),
  }));

  // Dải ảnh cao cố định theo viewport: đủ to để nhìn biển, nhưng không ăn hết
  // chỗ của thanh thao tác ghim đáy (nguyên nhân cũ khiến phải cuộn).
  const figureClass = "relative m-0 h-full overflow-hidden";

  const cameraFigure = (
    <figure className={figureClass}>
      {hasMultiCam ? (
        <MultiCameraView
          cameras={laneCameras}
          slots={multi.slots}
          onRequestPermission={multi.requestPermission}
          onUploadForRole={doUploadForRole}
          allowUpload={allowUpload}
        />
      ) : (
        <CameraView
          videoRef={cam.videoRef}
          devices={cam.devices}
          deviceId={cam.deviceId}
          status={cam.status}
          onSelectDevice={cam.setDeviceId}
          onCapture={doCapture}
          onRequestPermission={cam.requestPermission}
          onManual={() => decisionRef.current?.manual()}
          onUpload={doUpload}
          allowUpload={allowUpload}
          error={cam.error}
        />
      )}
    </figure>
  );

  // Ảnh của mọi camera đã lưu cùng lượt này (làn đa camera) — trước đây lưu
  // đúng ở DB (đã kiểm tra) nhưng không có chỗ nào hiện ra màn hình, nhân viên
  // tưởng chỉ 1 ảnh được lưu. >1 ảnh thì chia đều (2 cam là đúng tỉ lệ 50/50)
  // thay vì chỉ hiện ảnh chính; ảnh chính vẫn dùng object URL cục bộ sẵn có.
  const capturedImages: CameraImage[] =
    capture && capture.images && capture.images.length > 1
      ? capture.images.map((img) => ({
          role: img.role,
          imageAssetId: img.image_asset_id,
          localUrl: img.is_primary ? capture.local_image_url : null,
        }))
      : [];

  const captureFigure = (
    <figure className={figureClass}>
      {capturedImages.length > 0 ? (
        <CameraImageGrid images={capturedImages} />
      ) : (
        <>
          <CapturePreview localUrl={capture?.local_image_url} imageAssetId={capture?.image_asset_id} />
          {capture && (
            <figcaption className="absolute bottom-1.5 left-2 rounded bg-black/55 px-1.5 py-0.5 text-[11px] font-medium text-white">
              Ảnh đã chụp
            </figcaption>
          )}
        </>
      )}
    </figure>
  );

  const decisionArea = capture ? (
    <DecisionPanel
      ref={decisionRef}
      capture={capture}
      direction={direction}
      onDone={() => setCaptureWithUrl(null)}
      onRecapture={doCapture}
      onPayOpenChange={onPayOpenChange}
    />
  ) : (
    <EmptyState title="Chưa có lượt chụp" hint="Bấm Chụp hoặc chờ sự kiện cổng" />
  );

  return (
    <div
      onClick={onActivate}
      className={active ? "h-full rounded-[var(--radius-card)] ring-2 ring-ink" : "h-full"}
    >
      <SurfaceCard variant="white" className="flex h-full flex-col gap-3 overflow-hidden">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-sm font-semibold">
            {direction === "in" ? "Hướng VÀO" : "Hướng RA"}
            {laneName && <span className="ml-1.5 font-normal text-muted">· làn {laneName}</span>}
          </h2>
          {hasMultiCam && (
            <Button className="h-8 shrink-0 px-3 text-[13px]" onClick={doCapture} disabled={busy}>
              {sendActionLabel}
            </Button>
          )}
        </div>

        {/* Ảnh trên (chiều cao cố định, không co), thao tác dưới (tự ghim đáy
            bên trong DecisionPanel). Cùng một bố cục cho cả 2 chế độ hiển thị:
            chia đôi thì mỗi panel hẹp hơn nhưng thứ tự ưu tiên vẫn y hệt. */}
        <div
          className={`grid shrink-0 grid-cols-2 gap-2 ${wide ? "h-[34dvh]" : "h-[22dvh]"}`}
        >
          {cameraFigure}
          {captureFigure}
        </div>
        <div className="min-h-0 flex-1">{decisionArea}</div>
      </SurfaceCard>
    </div>
  );
});
