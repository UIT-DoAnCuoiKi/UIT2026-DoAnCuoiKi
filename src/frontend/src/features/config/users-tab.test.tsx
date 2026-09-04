import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { UsersTab } from "./users-tab";

const createUser = vi.fn().mockResolvedValue({ id: 3 });
const updateUser = vi.fn().mockResolvedValue({});
vi.mock("@/api/generated/users/users", () => ({
  useListUsers: () => ({ data: [{ id: 1, username: "an", role: "staff", active: true }], isLoading: false }),
  useCreateUser: () => ({ mutateAsync: createUser, isPending: false }),
  useUpdateUser: () => ({ mutateAsync: updateUser, isPending: false }),
  getListUsersQueryKey: () => ["/users"],
}));
vi.mock("@tanstack/react-query", async (orig) => ({
  ...(await orig<typeof import("@tanstack/react-query")>()),
  useQueryClient: () => ({ invalidateQueries: vi.fn() }),
}));
const toastError = vi.fn();
vi.mock("sonner", () => ({ toast: { success: vi.fn(), error: (m: string) => toastError(m) } }));

beforeEach(() => {
  createUser.mockClear();
  updateUser.mockClear();
  toastError.mockClear();
});

test("creates a user with username, password and role", async () => {
  render(<UsersTab />);
  await userEvent.type(screen.getByLabelText("Tên đăng nhập mới"), "binh");
  await userEvent.type(screen.getByLabelText("Mật khẩu mới"), "secret1");
  await userEvent.selectOptions(screen.getByLabelText("Vai trò mới"), "manager");
  await userEvent.click(screen.getByRole("button", { name: /Tạo tài khoản/i }));
  expect(createUser).toHaveBeenCalledWith({ data: { username: "binh", password: "secret1", role: "manager" } });
});

test("rejects a short password before hitting the API", async () => {
  render(<UsersTab />);
  await userEvent.type(screen.getByLabelText("Tên đăng nhập mới"), "binh");
  await userEvent.type(screen.getByLabelText("Mật khẩu mới"), "123");
  await userEvent.click(screen.getByRole("button", { name: /Tạo tài khoản/i }));
  expect(createUser).not.toHaveBeenCalled();
  expect(toastError).toHaveBeenCalled();
});

test("changes an existing user's role", async () => {
  render(<UsersTab />);
  await userEvent.selectOptions(screen.getByLabelText("Vai trò an"), "root");
  expect(updateUser).toHaveBeenCalledWith({ userId: 1, data: { role: "root" } });
});

test("resets a user's password inline", async () => {
  render(<UsersTab />);
  await userEvent.type(screen.getByLabelText("Mật khẩu cho an"), "newpass1");
  await userEvent.click(screen.getByRole("button", { name: /^Lưu$/i }));
  expect(updateUser).toHaveBeenCalledWith({ userId: 1, data: { password: "newpass1" } });
});

test("active user shows a status switch that can disable the account", async () => {
  render(<UsersTab />);
  // Tài khoản đang bật (không phải account đang đăng nhập trong test): hiện "Đang bật".
  expect(screen.getByText("Đang bật")).toBeInTheDocument();
  const sw = screen.getByRole("switch", { name: /Trạng thái tài khoản an/i });
  await userEvent.click(sw);
  expect(updateUser).toHaveBeenCalledWith({ userId: 1, data: { active: false } });
});

test("password show/hide toggles input type", async () => {
  render(<UsersTab />);
  const pw = screen.getByLabelText("Mật khẩu mới");
  expect(pw).toHaveAttribute("type", "password");
  // create-form toggle is the first one in the DOM (row cell toggle comes later)
  await userEvent.click(screen.getAllByRole("button", { name: /Hiện mật khẩu/i })[0]);
  expect(pw).toHaveAttribute("type", "text");
});
