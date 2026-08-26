import { render, screen } from "@testing-library/react";
import { ConfigPage } from "./config-page";

vi.mock("./price-rules-tab", () => ({ PriceRulesTab: () => <div>PRICE</div> }));
vi.mock("./users-tab", () => ({ UsersTab: () => <div>USERS</div> }));
vi.mock("./lanes-tab", () => ({ LanesTab: () => <div>LANES</div> }));
vi.mock("./toggles-tab", () => ({ TogglesTab: () => <div>TOGGLES</div> }));

const roleRef = { current: "manager" as string };
vi.mock("@/lib/auth", () => ({ getRole: () => roleRef.current }));

test("manager does not see Tài khoản tab", () => {
  roleRef.current = "manager";
  render(<ConfigPage />);
  expect(screen.queryByText("Tài khoản")).toBeNull();
});

test("root sees Tài khoản tab", () => {
  roleRef.current = "root";
  render(<ConfigPage />);
  expect(screen.getByText("Tài khoản")).toBeInTheDocument();
});
