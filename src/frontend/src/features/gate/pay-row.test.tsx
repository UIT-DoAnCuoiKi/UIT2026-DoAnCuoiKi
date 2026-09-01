import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PayRow } from "./pay-row";

vi.mock("./receipt", () => ({
  Receipt: ({ amount }: { amount: number }) => <div>RECEIPT {amount}</div>,
}));

const base = {
  sessionId: 9,
  plate: "51F1",
  amount: 5000,
  method: "cash",
  onMethod: () => {},
  onConfirm: () => {},
  pending: false,
  paid: false,
};

test("renders amount and method buttons, fires confirm", async () => {
  const onConfirm = vi.fn();
  render(<PayRow {...base} onConfirm={onConfirm} />);
  expect(screen.getByText(/5[.,]?000/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: /Thu & in/i }));
  expect(onConfirm).toHaveBeenCalled();
});

test("shows receipt when paid", () => {
  render(<PayRow {...base} paid />);
  expect(screen.getByText(/RECEIPT 5000/)).toBeInTheDocument();
});
