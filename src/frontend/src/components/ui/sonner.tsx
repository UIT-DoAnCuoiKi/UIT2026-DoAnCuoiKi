import { Toaster as Sonner, type ToasterProps } from "sonner";
import { useTheme } from "@/theme/theme-provider";

export function Toaster(props: ToasterProps) {
  const { theme } = useTheme();
  return <Sonner theme={theme} richColors closeButton {...props} />;
}

export { toast } from "sonner";
