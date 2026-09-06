import { cn } from "@/lib/cn";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function PlateField({
  value,
  onChange,
  highlight = false,
  size = "md",
  disabled = false,
  // Màn Trạm cổng mount đồng thời 2 panel (VÀO và RA); nếu id cố định thì trùng
  // id trong cùng trang và focus sẽ nhảy vào ô của panel khác.
  id = "plate",
}: {
  value: string;
  onChange: (v: string) => void;
  highlight?: boolean;
  size?: "md" | "lg";
  disabled?: boolean;
  id?: string;
}) {
  return (
    <div className={cn("space-y-1.5", size === "lg" && "w-full max-w-[220px] shrink-0")}>
      <Label htmlFor={id}>Biển số</Label>
      <Input
        id={id}
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value.toUpperCase())}
        className={cn(
          "tnum font-semibold tracking-wide",
          size === "lg" ? "h-12 text-center text-[26px]" : "text-base",
          highlight && "border-st-amber ring-1 ring-st-amber",
        )}
      />
    </div>
  );
}
