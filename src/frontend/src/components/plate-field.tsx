import { cn } from "@/lib/cn";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function PlateField({
  value,
  onChange,
  highlight = false,
  size = "md",
  disabled = false,
}: {
  value: string;
  onChange: (v: string) => void;
  highlight?: boolean;
  size?: "md" | "lg";
  disabled?: boolean;
}) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor="plate">Biển số</Label>
      <Input
        id="plate"
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value.toUpperCase())}
        className={cn(
          "tnum font-semibold tracking-wide",
          size === "lg" ? "h-12 text-[30px]" : "text-base",
          highlight && "border-st-amber ring-1 ring-st-amber",
        )}
      />
    </div>
  );
}
