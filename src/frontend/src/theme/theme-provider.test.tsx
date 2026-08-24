import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ThemeProvider, useTheme } from "./theme-provider";

function Probe() {
  const { theme, toggle } = useTheme();
  return <button onClick={toggle}>theme:{theme}</button>;
}

test("toggles dark class on html and persists", async () => {
  render(
    <ThemeProvider>
      <Probe />
    </ThemeProvider>,
  );
  expect(screen.getByText("theme:light")).toBeInTheDocument();
  expect(document.documentElement.classList.contains("dark")).toBe(false);
  await act(async () => {
    await userEvent.click(screen.getByRole("button"));
  });
  expect(document.documentElement.classList.contains("dark")).toBe(true);
  expect(localStorage.getItem("theme")).toBe("dark");
});
