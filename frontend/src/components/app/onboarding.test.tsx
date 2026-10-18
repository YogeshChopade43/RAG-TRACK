import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { mockFetch, renderApp, signIn, TEST_USER } from "@/test/render";

afterEach(() => vi.unstubAllGlobals());

function verifiedSession() {
  sessionStorage.setItem("llm_api_key", "sk-or-old");
  sessionStorage.setItem("llm_model", "openai/gpt-4o-mini");
  sessionStorage.setItem("llm_verified", "1");
}

async function fillKey(key = "sk-or-test", model = "openai/gpt-4o-mini") {
  await userEvent.type(await screen.findByLabelText("OpenRouter API key"), key);
  await userEvent.type(screen.getByLabelText("Model"), model);
}

function currentStep() {
  const steps = screen.getByRole("list", { name: "Setup progress" });
  return within(steps)
    .getAllByRole("listitem")
    .find((li) => li.getAttribute("aria-current") === "step")?.textContent;
}

test("failed key test shows the server message and stays on step 1", async () => {
  signIn();
  mockFetch({
    "/auth/me": [{ status: 200, body: TEST_USER }],
    "/auth/test-api-key": [{ status: 200, body: { valid: false, message: "Invalid API key" } }],
  });
  renderApp("/app");
  await fillKey();
  await userEvent.click(screen.getByRole("button", { name: "Test & continue" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("Invalid API key");
  expect(currentStep()).toContain("Connect model");
  expect(sessionStorage.getItem("llm_verified")).toBeNull();
});

test("a valid key advances to upload and is kept for the session", async () => {
  signIn();
  mockFetch({
    "/auth/me": [{ status: 200, body: TEST_USER }],
    "/auth/test-api-key": [{ status: 200, body: { valid: true, message: "ok", model: "openai/gpt-4o-mini" } }],
  });
  renderApp("/app");
  await fillKey();
  await userEvent.click(screen.getByRole("button", { name: "Test & continue" }));

  expect(await screen.findByTestId("upload-step")).toBeInTheDocument();
  expect(currentStep()).toContain("Upload a document");
  expect(sessionStorage.getItem("llm_verified")).toBe("1");
  expect(sessionStorage.getItem("llm_api_key")).toBe("sk-or-test");
  expect(sessionStorage.getItem("llm_model")).toBe("openai/gpt-4o-mini");
});

test("Test & continue is disabled until key and model are entered", async () => {
  signIn();
  mockFetch({ "/auth/me": [{ status: 200, body: TEST_USER }] });
  renderApp("/app");
  const button = await screen.findByRole("button", { name: "Test & continue" });
  expect(button).toBeDisabled();
  await userEvent.type(screen.getByLabelText("OpenRouter API key"), "sk-or-test");
  expect(button).toBeDisabled();
  await userEvent.type(screen.getByLabelText("Model"), "openai/gpt-4o-mini");
  expect(button).toBeEnabled();
});

test("Settings saves a new key only after it passes the test", async () => {
  signIn();
  verifiedSession();
  mockFetch({
    "/auth/me": [{ status: 200, body: TEST_USER }],
    "/auth/test-api-key": [{ status: 200, body: { valid: false, message: "Invalid API key" } }],
  });
  renderApp("/app");
  await userEvent.click(await screen.findByRole("button", { name: "Settings" }));
  const dialog = await screen.findByRole("dialog", { name: "Model settings" });
  const key = within(dialog).getByLabelText("OpenRouter API key");
  await userEvent.clear(key);
  await userEvent.type(key, "sk-or-new");
  await userEvent.click(within(dialog).getByRole("button", { name: "Test & save" }));

  expect(await within(dialog).findByRole("alert")).toHaveTextContent("Invalid API key");
  expect(sessionStorage.getItem("llm_api_key")).toBe("sk-or-old");
  expect(sessionStorage.getItem("llm_verified")).toBe("1");
});

test("model chip shows the model when connected and opens Settings", async () => {
  signIn();
  verifiedSession();
  mockFetch({ "/auth/me": [{ status: 200, body: TEST_USER }] });
  renderApp("/app");
  await userEvent.click(await screen.findByRole("button", { name: /openai\/gpt-4o-mini/ }));
  expect(await screen.findByRole("dialog", { name: "Model settings" })).toBeInTheDocument();
});

test("model chip says Not connected before a key is verified", async () => {
  signIn();
  mockFetch({ "/auth/me": [{ status: 200, body: TEST_USER }] });
  renderApp("/app");
  expect(await screen.findByRole("button", { name: /Not connected/ })).toBeInTheDocument();
});

test("the account menu can change the document (the top-bar chip is hidden on phones)", async () => {
  signIn();
  verifiedSession();
  sessionStorage.setItem("active_document", JSON.stringify({ documentId: "d1", fileName: "cv.pdf" }));
  mockFetch({ "/auth/me": [{ status: 200, body: TEST_USER }] });
  renderApp("/app");
  await userEvent.click(await screen.findByRole("button", { name: "Account" }));
  await userEvent.click(await screen.findByRole("menuitem", { name: "Change document" }));
  expect(await screen.findByTestId("upload-step")).toBeInTheDocument();
  expect(sessionStorage.getItem("active_document")).toBeNull();
});

test("user menu Sign out signs out to /login", async () => {
  signIn();
  verifiedSession();
  const fetch = mockFetch({ "/auth/me": [{ status: 200, body: TEST_USER }], "/auth/logout": [{ status: 200, body: {} }] });
  const router = renderApp("/app");
  await userEvent.click(await screen.findByRole("button", { name: "Account" }));
  await userEvent.click(await screen.findByRole("menuitem", { name: "Sign out" }));

  expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  expect(router.state.location.pathname).toBe("/login");
  expect(fetch.mock.calls.some((c) => String(c[0]).includes("/auth/logout"))).toBe(true);
  expect(sessionStorage.getItem("llm_api_key")).toBeNull();
});

test("connect step advises a separate, spend-limited key", async () => {
  signIn();
  mockFetch({ "/auth/me": [{ status: 200, body: TEST_USER }] });
  renderApp("/app");
  expect(await screen.findByText(/separate OpenRouter key with a spending limit/)).toBeInTheDocument();
});
