import type { GateCapture } from "./use-gate-socket";
import { CapturePreview } from "./capture-preview";

const pct = (v?: number | null) => (v == null ? null : `${Math.round(v * 100)}%`);

// Dải thông tin độ tin cậy + cảnh báo định dạng cho kết quả nhận dạng.
// Ảnh khung hình và các trường sửa tay (loại xe, màu biển, nhóm phí) nằm ở
// DecisionPanel; component này chỉ tóm tắt độ tin và cảnh báo.
export function RecognitionResult({ capture }: { capture: GateCapture }) {
  const ocr = pct(capture.ocr_conf);
  const color = pct(capture.color_conf);
  return (
    <>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[13px] text-muted">
        {ocr && (
          <span>
            Độ tin OCR: <span className="font-medium text-ink">{ocr}</span>
          </span>
        )}
        {color && (
          <span>
            Độ tin màu: <span className="font-medium text-ink">{color}</span>
          </span>
        )}
        {capture.plate_valid === false && (
          <span className="text-st-amber">Cảnh báo: biển sai định dạng (vẫn cho xác nhận)</span>
        )}
      </div>
      {capture.plate_crop_asset_id != null && (
        <div className="space-y-1">
          <p className="text-[13px] text-muted">Biển đã xử lý màu</p>
          <div className="h-24 w-full max-w-sm overflow-hidden">
            <CapturePreview imageAssetId={capture.plate_crop_asset_id} fit="contain" />
          </div>
        </div>
      )}
    </>
  );
}
