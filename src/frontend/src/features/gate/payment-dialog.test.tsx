import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PaymentDialog } from "./payment-dialog";

const pay = vi.fn().mockResolvedValue({ id: 1 });
vi.mock("@/api/generated/payments/payments", () => ({
  useCreatePayment: () => ({ mutateAsync: pay, isPending: false }),
}));

test("selecting method and confirming records a payment then shows receipt", async () => {
  render(<PaymentDialog sessionId={7} plate="51F12345" amount={5000} onClose={() => {}} />);
  await userEvent.click(screen.getByRole("button", { name: /Tiền mặt/i }));
  await userEvent.click(screen.getByRole("button", { name: /Xác nhận thu/i }));
  expect(pay).toHaveBeenCalledWith({ data: { session_id: 7, amount: 5000, method: "cash", kind: "payment" } });
  expect(await screen.findByText(/Biên lai/i)).toBeInTheDocument();
});
