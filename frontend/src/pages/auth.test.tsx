import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { mockFetch, renderApp } from "@/test/render";

afterEach(() => vi.unstubAllGlobals());

test("register validates fields in the browser and sends nothing when invalid", async () => {
  const fetch = mockFetch({});
  renderApp("/register");

  await userEvent.type(await screen.findByLabelText("Email"), "not-an-email");
  await userEvent.type(screen.getByLabelText("Password"), "short");
  await userEvent.type(screen.getByLabelText("Confirm password"), "different");
  await userEvent.click(screen.getByRole("button", { name: "Create account" }));

  expect(screen.getByText("Enter a valid email address")).toBeInTheDocument();
  expect(screen.getByText("Password must be at least 8 characters")).toBeInTheDocument();
  expect(screen.getByText("Passwords don't match")).toBeInTheDocument();
  expect(fetch).not.toHaveBeenCalled();
});

test("login shows the server's error above the form", async () => {
  mockFetch({ "/auth/login": [{ status: 401, body: { detail: "Incorrect email or password" } }] });
  renderApp("/login");

  await userEvent.type(await screen.findByLabelText("Email"), "jane@example.com");
  await userEvent.type(screen.getByLabelText("Password"), "wrongpass");
  await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Incorrect email or password");
});

test("password field has a show/hide toggle", async () => {
  mockFetch({});
  renderApp("/login");
  const input = await screen.findByLabelText("Password");
  expect(input).toHaveAttribute("type", "password");
  await userEvent.click(screen.getByRole("button", { name: "Show password" }));
  expect(input).toHaveAttribute("type", "text");
});
