import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Pencil,
  LogIn,
  Clock,
  HelpCircle,
  type LucideIcon,
} from "lucide-react";

type Meta = { token: string; Icon: LucideIcon; label: string };
const GREY: Meta = { token: "st-grey", Icon: HelpCircle, label: "Không rõ" };

const REVIEW: Record<string, Meta> = {
  confident: { token: "st-green", Icon: CheckCircle2, label: "Tin cậy" },
  needs_review: { token: "st-amber", Icon: AlertTriangle, label: "Cần soát" },
  disputed: { token: "st-red", Icon: XCircle, label: "Tranh chấp" },
  manual: { token: "st-purple", Icon: Pencil, label: "Nhập tay" },
};

const SESSION: Record<string, Meta> = {
  completed: { token: "st-green", Icon: CheckCircle2, label: "Hoàn tất" },
  in_lot: { token: "st-blue", Icon: LogIn, label: "Trong bãi" },
  disputed: { token: "st-red", Icon: XCircle, label: "Tranh chấp" },
  pending_manual: { token: "st-purple", Icon: Clock, label: "Chờ xử lý tay" },
};

export function reviewStateMeta(s: string): Meta {
  return REVIEW[s] ?? GREY;
}

export function sessionStatusMeta(s: string): Meta {
  return SESSION[s] ?? GREY;
}
