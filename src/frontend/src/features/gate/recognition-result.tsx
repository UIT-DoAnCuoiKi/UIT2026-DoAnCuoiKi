import type { GateCapture } from "./use-gate-socket";
import { groupLabel } from "@/lib/vehicle-groups";
import { vehicleTypeLabel } from "@/lib/labels";
import { plateColor } from "./plate-color";

export function RecognitionResult({
  capture,
  groupMap,
}: {
  capture: GateCapture;
  groupMap: Record<string, string>;
}) {
  const color = plateColor(capture.color);
  return (
    <div className="space-y-2">
      <dl className="grid grid-cols-3 gap-x-4 gap-y-1">
        <div>
          <dt className="text-[13px] text-muted">Loại xe</dt>
          <dd className="text-[16px] font-medium text-ink">{vehicleTypeLabel(capture.vehicle_type)}</dd>
        </div>
        <div>
          <dt className="text-[13px] text-muted">Nhóm phí</dt>
          <dd className="text-[16px] font-medium text-ink">
            {capture.vehicle_group ? groupLabel(groupMap, capture.vehicle_group) : "—"}
          </dd>
        </div>
        <div>
          <dt className="text-[13px] text-muted">Màu biển</dt>
          <dd className="flex items-center gap-2 text-[16px] font-medium text-ink">
            {color && (
              <span
                className="inline-block h-4 w-4 shrink-0 rounded-full border border-line"
                style={{ background: color.swatch }}
              />
            )}
            {color?.label ?? "—"}
          </dd>
        </div>
      </dl>
      {capture.plate_valid === false && (
        <p className="text-[13px] text-st-amber">Cảnh báo: biển sai định dạng (vẫn cho xác nhận)</p>
      )}
      {capture.duplicate && (
        <p className="text-[13px] text-st-amber">Cảnh báo: biển trùng phiên trong bãi</p>
      )}
    </div>
  );
}
