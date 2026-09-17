import { useRef } from "react";

/** Chỉ in đúng khối này: đánh dấu trước khi mở hộp thoại in rồi gỡ ngay sau đó. */
export function usePrintOnly() {
  const ref = useRef<HTMLDivElement>(null);
  const print = () => {
    const el = ref.current;
    if (!el) return;
    el.setAttribute("data-print-now", "");
    window.print();
    el.removeAttribute("data-print-now");
  };
  return { ref, print };
}
