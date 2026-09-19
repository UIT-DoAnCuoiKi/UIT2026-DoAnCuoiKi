import { useEffect } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

// Portal ra document.body để các cha (z-index, transform) không che hoặc lệch lớp phủ.
export function ImageLightbox({ src, alt, onClose }: { src: string; alt: string; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return createPortal(
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/80 p-4"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <img src={src} alt={alt} className="max-h-full max-w-full rounded-[var(--radius-control)] object-contain" />
      <button
        type="button"
        className="absolute right-4 top-4 rounded-full bg-black/55 p-2 text-white hover:bg-black/70"
        aria-label="Đóng"
        onClick={onClose}
      >
        <X size={20} />
      </button>
    </div>,
    document.body,
  );
}
