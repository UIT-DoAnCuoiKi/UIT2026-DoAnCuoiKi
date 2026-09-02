import { useState } from "react";
import { toast } from "sonner";
import { useQueryClient } from "@tanstack/react-query";
import type { ColumnDef } from "@tanstack/react-table";
import { useListUsers, useCreateUser, useUpdateUser, getListUsersQueryKey } from "@/api/generated/users/users";
import type { UserOut } from "@/api/generated/model";
import { DataTable } from "@/components/data-table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { isAxiosError } from "axios";

const ROLES = ["staff", "manager", "root"] as const;
const ROLE_LABEL: Record<string, string> = { staff: "Nhân viên", manager: "Quản lý", root: "Quản trị" };
const MIN_PW = 6;
const SELECT_CLASS = "h-9 rounded-[var(--radius-control)] border border-line bg-bg px-2 text-sm";

export function UsersTab() {
  const qc = useQueryClient();
  const refresh = () => qc.invalidateQueries({ queryKey: getListUsersQueryKey() });
  const { data, isLoading } = useListUsers();
  const create = useCreateUser();
  const update = useUpdateUser();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<string>("staff");
  const [showPw, setShowPw] = useState(false);

  const addUser = async () => {
    if (!username.trim() || password.length < MIN_PW) {
      toast.error(`Nhập tên đăng nhập và mật khẩu tối thiểu ${MIN_PW} ký tự`);
      return;
    }
    try {
      await create.mutateAsync({ data: { username: username.trim(), password, role } });
      await refresh();
      setUsername("");
      setPassword("");
      setRole("staff");
      toast.success("Đã tạo tài khoản");
    } catch (e) {
      if (isAxiosError(e) && e.response?.status === 409) toast.error("Tên đăng nhập đã tồn tại");
      else toast.error("Tạo tài khoản thất bại");
    }
  };

  const cols: ColumnDef<UserOut, unknown>[] = [
    { header: "Tên đăng nhập", accessorKey: "username" },
    {
      header: "Vai",
      cell: ({ row }) => (
        <select
          className={SELECT_CLASS}
          value={row.original.role}
          aria-label={`Vai trò ${row.original.username}`}
          onChange={async (e) => {
            await update.mutateAsync({ userId: row.original.id, data: { role: e.target.value } });
            await refresh();
            toast.success("Đã đổi vai trò");
          }}
        >
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {ROLE_LABEL[r]}
            </option>
          ))}
        </select>
      ),
    },
    {
      header: "Đổi mật khẩu",
      cell: ({ row }) => (
        <PasswordCell
          ariaLabel={`Mật khẩu cho ${row.original.username}`}
          onSave={async (pw) => {
            await update.mutateAsync({ userId: row.original.id, data: { password: pw } });
            toast.success("Đã đổi mật khẩu");
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
            await update.mutateAsync({ userId: row.original.id, data: { active: !row.original.active } });
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
          placeholder="Tên đăng nhập"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          className="max-w-[180px]"
          aria-label="Tên đăng nhập mới"
          autoComplete="off"
        />
        <div className="relative">
          <Input
            type={showPw ? "text" : "password"}
            placeholder={`Mật khẩu (≥${MIN_PW} ký tự)`}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-[200px] pr-12"
            aria-label="Mật khẩu mới"
            autoComplete="new-password"
          />
          <button
            type="button"
            onClick={() => setShowPw((v) => !v)}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-[13px] text-muted"
            aria-label={showPw ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
          >
            {showPw ? "Ẩn" : "Hiện"}
          </button>
        </div>
        <select className={SELECT_CLASS} value={role} onChange={(e) => setRole(e.target.value)} aria-label="Vai trò mới">
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {ROLE_LABEL[r]}
            </option>
          ))}
        </select>
        <Button onClick={addUser} disabled={create.isPending}>
          Tạo tài khoản
        </Button>
      </div>
      <DataTable columns={cols} data={data ?? []} loading={isLoading} empty="Chưa có tài khoản" />
    </div>
  );
}

function PasswordCell({ ariaLabel, onSave }: { ariaLabel: string; onSave: (pw: string) => Promise<void> }) {
  const [pw, setPw] = useState("");
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  return (
    <div className="flex items-center gap-1">
      <div className="relative">
        <Input
          type={show ? "text" : "password"}
          value={pw}
          onChange={(e) => setPw(e.target.value)}
          placeholder="Mật khẩu mới"
          className="h-8 w-[150px] pr-12"
          aria-label={ariaLabel}
          autoComplete="new-password"
        />
        <button
          type="button"
          onClick={() => setShow((v) => !v)}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-[12px] text-muted"
          aria-label={show ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
        >
          {show ? "Ẩn" : "Hiện"}
        </button>
      </div>
      <Button
        variant="outline"
        size="sm"
        disabled={busy}
        onClick={async () => {
          if (pw.length < MIN_PW) {
            toast.error(`Mật khẩu tối thiểu ${MIN_PW} ký tự`);
            return;
          }
          setBusy(true);
          try {
            await onSave(pw);
            setPw("");
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
