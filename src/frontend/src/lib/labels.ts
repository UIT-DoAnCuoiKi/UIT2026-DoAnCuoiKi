// Ánh xạ mã kỹ thuật (giữ nguyên trong dữ liệu) sang nhãn tiếng Việt để hiển thị.
// Mã không có trong bảng ánh xạ sẽ hiển thị nguyên trạng để không giấu dữ liệu lạ.

const VEHICLE_TYPE: Record<string, string> = {
  car: "Ô tô",
  truck: "Xe tải",
  bus: "Xe khách",
  motorbike: "Xe máy",
  bicycle: "Xe đạp",
};

const MATCH_FLAG: Record<string, string> = {
  exact: "Chính xác",
  auto_corrected: "Tự động sửa",
  manual: "Thủ công",
  lost_ticket: "Mất vé",
};

const PAYMENT_METHOD: Record<string, string> = {
  cash: "Tiền mặt",
  qr: "QR",
  ewallet: "Ví điện tử",
};

export function vehicleTypeLabel(code?: string | null): string {
  if (!code) return "—";
  return VEHICLE_TYPE[code.toLowerCase()] ?? code;
}

export function matchFlagLabel(code?: string | null): string {
  if (!code) return "—";
  return MATCH_FLAG[code.toLowerCase()] ?? code;
}

export function paymentMethodLabel(code?: string | null): string {
  if (!code) return "—";
  return PAYMENT_METHOD[code.toLowerCase()] ?? code;
}
