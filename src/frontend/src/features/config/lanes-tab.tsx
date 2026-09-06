import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import {
  useListLanes, useUpdateLane, useCreateLane, getListLanesQueryKey,
  useCreateLaneCamera, useUpdateLaneCamera, useDeleteLaneCamera,
} from "@/api/generated/config/config";
import type { LaneCameraOut, LaneOut } from "@/api/generated/model";
import { DataTable } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const ROLE_LABEL: Record<string, string> = { front: "Trước", rear: "Sau", overview: "Toàn cảnh" };
const RECOGNITION_MODE_LABEL: Record<string, string> = {
  primary: "Chỉ camera chính",
  best_of: "Cả 2, lấy kết quả tin cậy hơn",
};
const SELECT_CLASS = "h-8 rounded-[var(--radius-control)] border border-line bg-bg px-2 text-[13px]";

export function LanesTab() {
  const qc = useQueryClient();
  const refresh = () => qc.invalidateQueries({ queryKey: getListLanesQueryKey() });
  const { data, isLoading } = useListLanes();
  const update = useUpdateLane();
  const create = useCreateLane();

  const [name, setName] = useState("");
  const [rtsp, setRtsp] = useState("");
  const [openLaneId, setOpenLaneId] = useState<number | null>(null);

  const addLane = async () => {
    if (!name.trim()) {
      toast.error("Nhập tên lane");
      return;
    }
    await create.mutateAsync({ data: { name: name.trim(), rtsp_url: rtsp.trim() || null, active: true } });
    await refresh();
    setName("");
    setRtsp("");
    toast.success("Đã tạo lane");
  };

  const cols: ColumnDef<LaneOut, unknown>[] = [
    {
      header: "Tên",
      cell: ({ row }) => (
        <EditableCell
          value={row.original.name}
          ariaLabel={`Tên lane ${row.original.name}`}
          className="w-[150px]"
          onSave={async (v) => {
            if (!v.trim()) {
              toast.error("Tên lane không được trống");
              return;
            }
            await update.mutateAsync({ laneId: row.original.id, data: { name: v.trim() } });
            await refresh();
            toast.success("Đã cập nhật tên");
          }}
        />
      ),
    },
    {
      header: "RTSP",
      cell: ({ row }) => (
        <EditableCell
          value={row.original.rtsp_url ?? ""}
          ariaLabel={`RTSP ${row.original.name}`}
          placeholder="rtsp://..."
          className="w-[220px]"
          onSave={async (v) => {
            await update.mutateAsync({ laneId: row.original.id, data: { rtsp_url: v.trim() || null } });
            await refresh();
            toast.success("Đã cập nhật RTSP");
          }}
        />
      ),
    },
    {
      header: "Camera",
      cell: ({ row }) => {
        const n = row.original.cameras?.length ?? 0;
        return (
          <Button
            variant="outline"
            size="sm"
            onClick={() => setOpenLaneId((id) => (id === row.original.id ? null : row.original.id))}
          >
            {n > 0 ? `${n} camera` : "Chưa có camera"}
          </Button>
        );
      },
    },
    {
      header: "Cách nhận dạng",
      cell: ({ row }) => (
        <select
          aria-label={`Cách nhận dạng ${row.original.name}`}
          className={SELECT_CLASS}
          value={row.original.recognition_mode}
          disabled={(row.original.cameras?.length ?? 0) < 2}
          onChange={async (e) => {
            await update.mutateAsync({ laneId: row.original.id, data: { recognition_mode: e.target.value } });
            await refresh();
            toast.success("Đã cập nhật");
          }}
        >
          {Object.entries(RECOGNITION_MODE_LABEL).map(([code, label]) => (
            <option key={code} value={code}>
              {label}
            </option>
          ))}
        </select>
      ),
    },
    {
      header: "Kích hoạt",
      cell: ({ row }) => (
        <Button
          variant="outline"
          size="sm"
          onClick={async () => {
            await update.mutateAsync({ laneId: row.original.id, data: { active: !row.original.active } });
            await refresh();
            toast.success("Đã cập nhật");
          }}
        >
          {row.original.active ? "Bật" : "Tắt"}
        </Button>
      ),
    },
  ];

  const openLane = data?.find((l) => l.id === openLaneId);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-end gap-2">
        <Input
          placeholder="Tên lane (vd: Cổng chính)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="max-w-[200px]"
          aria-label="Tên lane mới"
        />
        <Input
          placeholder="RTSP URL (rtsp://...)"
          value={rtsp}
          onChange={(e) => setRtsp(e.target.value)}
          className="max-w-[320px]"
          aria-label="RTSP URL mới"
        />
        <Button onClick={addLane} disabled={create.isPending}>
          Tạo lane
        </Button>
      </div>
      <DataTable columns={cols} data={data ?? []} loading={isLoading} empty="Chưa có lane" />
      <p className="text-[13px] text-muted">
        Ô RTSP ở trên chỉ để ghi chú/tương thích cũ. Camera thật của lane (1-3 cái, thường trước + sau xe)
        khai báo riêng ở bảng "Camera" bên dưới mỗi lane.
      </p>

      {openLane && <LaneCameraPanel lane={openLane} onChange={refresh} />}
    </div>
  );
}

function LaneCameraPanel({ lane, onChange }: { lane: LaneOut; onChange: () => Promise<unknown> }) {
  const createCam = useCreateLaneCamera();
  const updateCam = useUpdateLaneCamera();
  const deleteCam = useDeleteLaneCamera();

  const [role, setRole] = useState("front");
  const [sourceKind, setSourceKind] = useState<"browser" | "rtsp">("browser");
  const [deviceId, setDeviceId] = useState("");
  const [deviceLabel, setDeviceLabel] = useState("");
  const [rtspUrl, setRtspUrl] = useState("");

  const addCamera = async () => {
    if (sourceKind === "rtsp" && !rtspUrl.trim()) {
      toast.error("Nguồn RTSP cần địa chỉ luồng");
      return;
    }
    await createCam.mutateAsync({
      laneId: lane.id,
      data: {
        role,
        source_kind: sourceKind,
        device_id: sourceKind === "browser" ? deviceId || null : null,
        rtsp_url: sourceKind === "rtsp" ? rtspUrl.trim() : null,
        is_primary: (lane.cameras?.length ?? 0) === 0, // camera đầu tiên mặc định là chính
        active: true,
      },
    });
    await onChange();
    setDeviceId("");
    setDeviceLabel("");
    setRtspUrl("");
    toast.success("Đã thêm camera");
  };

  return (
    <div className="space-y-3 rounded-[var(--radius-card)] border border-line bg-surface p-4">
      <p className="text-sm font-semibold">Camera của làn "{lane.name}"</p>

      {(lane.cameras?.length ?? 0) > 0 && (
        <div className="space-y-2">
          {lane.cameras!.map((cam) => (
            <CameraRow
              key={cam.id}
              cam={cam}
              onSetPrimary={async () => {
                await updateCam.mutateAsync({ cameraId: cam.id, data: { is_primary: true } });
                await onChange();
              }}
              onToggleActive={async () => {
                await updateCam.mutateAsync({ cameraId: cam.id, data: { active: !cam.active } });
                await onChange();
              }}
              onDelete={async () => {
                await deleteCam.mutateAsync({ cameraId: cam.id });
                await onChange();
                toast.success("Đã xoá camera");
              }}
            />
          ))}
        </div>
      )}

      <div className="flex flex-wrap items-end gap-2 border-t border-line pt-3">
        <div>
          <label htmlFor="cam-role" className="mb-1 block text-[12px] text-muted">
            Vai trò
          </label>
          <select id="cam-role" className={SELECT_CLASS} value={role} onChange={(e) => setRole(e.target.value)}>
            {Object.entries(ROLE_LABEL).map(([code, label]) => (
              <option key={code} value={code}>
                {label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="cam-source" className="mb-1 block text-[12px] text-muted">
            Nguồn
          </label>
          <select
            id="cam-source"
            className={SELECT_CLASS}
            value={sourceKind}
            onChange={(e) => setSourceKind(e.target.value as "browser" | "rtsp")}
          >
            <option value="browser">Webcam (trình duyệt)</option>
            <option value="rtsp">RTSP (qua thiết bị biên)</option>
          </select>
        </div>

        {sourceKind === "browser" ? (
          <CameraTester
            deviceId={deviceId}
            deviceLabel={deviceLabel}
            onPick={(id, label) => {
              setDeviceId(id);
              setDeviceLabel(label);
            }}
          />
        ) : (
          <div>
            <label htmlFor="cam-rtsp" className="mb-1 block text-[12px] text-muted">
              RTSP URL
            </label>
            <Input
              id="cam-rtsp"
              className="h-8 w-[240px]"
              placeholder="rtsp://user:pass@ip:554/stream"
              value={rtspUrl}
              onChange={(e) => setRtspUrl(e.target.value)}
            />
          </div>
        )}

        <Button className="h-8" onClick={addCamera} disabled={createCam.isPending}>
          Thêm camera
        </Button>
      </div>
      {sourceKind === "rtsp" && (
        <p className="text-[12px] text-muted">
          Trình duyệt không phát được luồng RTSP trực tiếp — cấu hình này chỉ lưu lại để thiết bị biên (edge
          worker) đọc, chưa xem trước được ở đây.
        </p>
      )}
    </div>
  );
}

function CameraRow({
  cam, onSetPrimary, onToggleActive, onDelete,
}: {
  cam: LaneCameraOut;
  onSetPrimary: () => Promise<void>;
  onToggleActive: () => Promise<void>;
  onDelete: () => Promise<void>;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-[var(--radius-control)] border border-line bg-bg px-3 py-2 text-[13px]">
      <span className="font-medium text-ink">{ROLE_LABEL[cam.role] ?? cam.role}</span>
      <span className="text-muted">{cam.source_kind === "browser" ? "Webcam" : "RTSP"}</span>
      <span className="tnum truncate text-muted" title={cam.device_id ?? cam.rtsp_url ?? ""}>
        {cam.source_kind === "browser" ? (cam.device_id ? "đã chọn thiết bị" : "chưa chọn thiết bị") : (cam.rtsp_url ?? "—")}
      </span>
      {cam.is_primary ? (
        <span className="rounded bg-tile-blue px-1.5 py-0.5 text-[11px] font-medium text-[#1c1c1c]">Chính</span>
      ) : (
        <Button variant="ghost" size="sm" onClick={onSetPrimary}>
          Đặt làm chính
        </Button>
      )}
      <Button variant="outline" size="sm" onClick={onToggleActive}>
        {cam.active ? "Bật" : "Tắt"}
      </Button>
      <Button variant="ghost" size="sm" onClick={onDelete} className="ml-auto text-st-red">
        Xoá
      </Button>
    </div>
  );
}

/** Mở webcam tạm thời để chọn đúng thiết bị (không lưu ảnh gì) — nhân viên cấu
 * hình cần biết đang trỏ đúng camera nào trước khi lưu, không phải đoán theo tên. */
function CameraTester({
  deviceId, deviceLabel, onPick,
}: {
  deviceId: string;
  deviceLabel: string;
  onPick: (id: string, label: string) => void;
}) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [devices, setDevicesList] = useState<{ deviceId: string; label: string }[]>([]);
  const [testing, setTesting] = useState(false);

  const stop = () => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    setTesting(false);
  };
  useEffect(() => stop, []);

  const startTest = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
      const all = await navigator.mediaDevices.enumerateDevices();
      setDevicesList(all.filter((d) => d.kind === "videoinput").map((d) => ({ deviceId: d.deviceId, label: d.label || "Camera" })));
      setTesting(true);
    } catch {
      toast.error("Không mở được camera (kiểm tra quyền trình duyệt)");
    }
  };

  // Trước đây đổi camera trong dropdown chỉ ghi nhớ deviceId, không mở lại
  // stream — khung xem trước vẫn kẹt ở camera mặc định lúc bấm "Thử camera"
  // (thường là webcam laptop), khiến nhân viên tưởng camera USB không nhận
  // được dù thiết bị vẫn được liệt kê đúng.
  const switchDevice = async (id: string, label: string) => {
    onPick(id, label);
    if (!id) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { deviceId: { exact: id } } });
      streamRef.current?.getTracks().forEach((t) => t.stop());
      streamRef.current = stream;
      if (videoRef.current) videoRef.current.srcObject = stream;
    } catch {
      toast.error("Không mở được camera này (kiểm tra quyền hoặc thiết bị)");
    }
  };

  return (
    <div>
      <label className="mb-1 block text-[12px] text-muted">Thiết bị</label>
      {testing ? (
        <div className="space-y-1">
          <video ref={videoRef} autoPlay muted playsInline className="h-16 w-28 rounded border border-line object-cover" />
          <select
            aria-label="Chọn thiết bị camera"
            className={SELECT_CLASS}
            value={deviceId}
            onChange={(e) => {
              const d = devices.find((x) => x.deviceId === e.target.value);
              void switchDevice(e.target.value, d?.label ?? "");
            }}
          >
            <option value="">— chọn —</option>
            {devices.map((d) => (
              <option key={d.deviceId} value={d.deviceId}>
                {d.label}
              </option>
            ))}
          </select>
          <Button variant="ghost" size="sm" onClick={stop}>
            Đóng
          </Button>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <span className="text-[13px] text-muted">{deviceLabel || "Chưa chọn"}</span>
          <Button variant="outline" size="sm" onClick={startTest}>
            Thử camera
          </Button>
        </div>
      )}
    </div>
  );
}

function EditableCell({
  value,
  onSave,
  ariaLabel,
  placeholder,
  className,
}: {
  value: string;
  onSave: (v: string) => Promise<void>;
  ariaLabel: string;
  placeholder?: string;
  className?: string;
}) {
  const [v, setV] = useState(value);
  const [busy, setBusy] = useState(false);
  const dirty = v !== value;
  return (
    <div className="flex items-center gap-1">
      <Input
        value={v}
        onChange={(e) => setV(e.target.value)}
        aria-label={ariaLabel}
        placeholder={placeholder}
        className={`h-8 ${className ?? ""}`}
      />
      <Button
        variant="outline"
        size="sm"
        disabled={!dirty || busy}
        onClick={async () => {
          setBusy(true);
          try {
            await onSave(v);
          } finally {
            setBusy(false);
          }
        }}
      >
        Lưu
      </Button>
    </div>
  );
}
