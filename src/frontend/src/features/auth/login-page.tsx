import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Eye, EyeOff } from "lucide-react";
import { useLogin } from "@/api/generated/auth/auth";
import { saveToken } from "@/lib/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Brand } from "@/components/brand";

const schema = z.object({
  username: z.string().min(1, "Bắt buộc"),
  password: z.string().min(1, "Bắt buộc"),
});
type Form = z.infer<typeof schema>;

export function LoginPage() {
  const nav = useNavigate();
  const { mutateAsync, isPending } = useLogin();
  const [show, setShow] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    setFocus,
    formState: { errors },
  } = useForm<Form>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: Form) => {
    setAuthError(null);
    try {
      const res = await mutateAsync({ data });
      saveToken(res.access_token);
      nav("/gate");
    } catch (err) {
      const status = (err as { response?: { status?: number } }).response?.status;
      if (status === 401) {
        setAuthError("Sai tên đăng nhập hoặc mật khẩu");
      } else if (status === undefined) {
        setAuthError("Không kết nối được máy chủ. Kiểm tra backend hoặc CORS.");
      } else {
        setAuthError("Đăng nhập thất bại, thử lại.");
      }
      setFocus("username");
    }
  };

  return (
    <div className="grid h-full grid-cols-1 md:grid-cols-2">
      <div className="relative hidden overflow-hidden bg-[#1c1c1c] md:flex md:flex-col md:justify-between md:p-12">
        <div
          className="pointer-events-none absolute -left-24 -top-24 h-96 w-96 rounded-full bg-[#95a4fc]/25 blur-3xl"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute -bottom-24 -right-16 h-80 w-80 rounded-full bg-[#a1e3cb]/15 blur-3xl"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.06]"
          aria-hidden
          style={{
            backgroundImage:
              "radial-gradient(circle at 1px 1px, #ffffff 1px, transparent 0)",
            backgroundSize: "22px 22px",
          }}
        />
        <div className="relative">
          <Brand size="lg" invert showTagline />
        </div>
        <p className="relative max-w-lg text-lg leading-relaxed text-white/60">
          Nhận diện biển số bằng thị giác máy tính và Edge AI. Quản lý ra vào, phí và
          thống kê bãi đỗ theo thời gian thực.
        </p>
        <div className="relative text-sm text-white/35">UIT · Đồ án tốt nghiệp 2026</div>
      </div>
      <div className="flex items-center justify-center p-8">
        <form onSubmit={handleSubmit(onSubmit)} className="w-full max-w-sm space-y-4" noValidate>
          <Brand size="sm" className="mb-2 md:hidden" />
          <h1 className="text-xl font-semibold">Đăng nhập</h1>
          {authError && (
            <p role="alert" className="text-sm text-st-red">
              {authError}
            </p>
          )}
          <div className="space-y-1.5">
            <Label htmlFor="username">Tên đăng nhập</Label>
            <Input id="username" autoComplete="username" {...register("username")} />
            {errors.username && <p className="text-[13px] text-st-red">{errors.username.message}</p>}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="password">Mật khẩu</Label>
            <div className="relative">
              <Input
                id="password"
                type={show ? "text" : "password"}
                autoComplete="current-password"
                {...register("password")}
              />
              <button
                type="button"
                onClick={() => setShow((s) => !s)}
                aria-label={show ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-muted"
              >
                {show ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {errors.password && <p className="text-[13px] text-st-red">{errors.password.message}</p>}
          </div>
          <Button type="submit" className="w-full" disabled={isPending}>
            {isPending ? "Đang đăng nhập..." : "Đăng nhập"}
          </Button>
          <a href="#" className="block text-[13px] text-muted">
            Quên mật khẩu
          </a>
        </form>
      </div>
    </div>
  );
}
