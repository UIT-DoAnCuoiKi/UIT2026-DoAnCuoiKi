import { useState } from "react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useListLanes, useUpdateLane, useCreateLane, getListLanesQueryKey } from "@/api/generated/config/config";
import type { LaneOut } from "@/api/generated/model";
import { DataTable } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function LanesTab() {
  const qc = useQueryClient();
  const refresh = () => qc.invalidateQueries({ queryKey: getListLanesQueryKey() });
  const { data, isLoading } = useListLanes();
  const update = useUpdateLane();
  const create = useCreateLane();

  const [name, setName] = useState("");
  const [rtsp, setRtsp] = useState("");

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
          className="w-[280px]"
          onSave={async (v) => {
            await update.mutateAsync({ laneId: row.original.id, data: { rtsp_url: v.trim() || null } });
            await refresh();
            toast.success("Đã cập nhật RTSP");
          }}
        />
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
        RTSP là địa chỉ luồng camera của lane (vd: rtsp://user:pass@ip:554/stream). Để trống nếu chưa đấu camera.
      </p>
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
