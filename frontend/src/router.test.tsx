import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { mockFetch, renderApp, signIn, TEST_TOKENS, TEST_USER } from "@/test/render";

afterEach(() => vi.unstubAllGlobals());

test("signed-out /app redirects to /login and back to /app after signing in", async () => {
  mockFetch({ "/auth/login": [{ status: 200, body: TEST_TOKENS }], "/auth/me": [{ status: 200, body: TEST_USER }] });
  const router = renderApp("/app");

  expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  await userEvent.type(screen.getByLabelText("Email"), "jane@example.com");
  await userEvent.type(screen.getByLabelText("Password"), "secret123");
  await userEvent.click(screen.getByRole("button", { name: "Sign in" }));

  expect(await screen.findByTestId("app-page")).toBeInTheDocument();
  expect(router.state.location.pathname).toBe("/app");
});

test("signed-in /login redirects to /app", async () => {
  signIn();
  mockFetch({ "/auth/me": [{ status: 200, body: TEST_USER }] });
  const router = renderApp("/login");
  expect(await screen.findByTestId("app-page")).toBeInTheDocument();
  expect(router.state.location.pathname).toBe("/app");
});

test("unknown path shows 404 with a link home", async () => {
  mockFetch({});
  renderApp("/does-not-exist");
  expect(await screen.findByRole("heading", { name: "Page not found" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "Back home" })).toHaveAttribute("href", "/");
});

test("backend unreachable on load keeps the user signed in and says so", async () => {
  signIn();
  mockFetch({ "/auth/me": [new TypeError("Failed to fetch")] });
  const router = renderApp("/app");
  expect(await screen.findByTestId("app-page")).toBeInTheDocument();
  expect(await screen.findByText("Can't reach the server")).toBeInTheDocument();
  expect(router.state.location.pathname).toBe("/app");
});

test("an expired session (401 on load, refresh rejected) signs out to /login", async () => {
  signIn();
  mockFetch({ "/auth/me": [{ status: 401 }], "/auth/refresh": [{ status: 401 }] });
  const router = renderApp("/app");
  expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  expect(router.state.location.pathname).toBe("/login");
  expect(localStorage.getItem("access_token")).toBeNull();
});
