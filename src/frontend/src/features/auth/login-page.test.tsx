import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { LoginPage } from "./login-page";

const mutateAsync = vi.fn();
vi.mock("@/api/generated/auth/auth", () => ({
  useLogin: () => ({ mutateAsync, isPending: false }),
}));

const navigate = vi.fn();
vi.mock("react-router-dom", async (orig) => ({
  ...(await orig<typeof import("react-router-dom")>()),
  useNavigate: () => navigate,
}));

test("submits credentials and navigates to /gate", async () => {
  mutateAsync.mockResolvedValue({ access_token: "h.e.s", token_type: "bearer", role: "staff" });
  render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>,
  );
  await userEvent.type(screen.getByLabelText("Tên đăng nhập"), "guard1");
  await userEvent.type(screen.getByLabelText("Mật khẩu"), "secret");
  await userEvent.click(screen.getByRole("button", { name: "Đăng nhập" }));
  expect(mutateAsync).toHaveBeenCalledWith({ data: { username: "guard1", password: "secret" } });
});
