import { screen, within } from "@testing-library/react";
import { GITHUB_URL } from "@/lib/constants";
import { mockFetch, renderApp, signIn, TEST_USER } from "@/test/render";

afterEach(() => vi.unstubAllGlobals());

test("signed-out: headline, Get started and Sign in", async () => {
  mockFetch({});
  renderApp("/");
  expect(
    await screen.findByRole("heading", { level: 1, name: "Ask your documents. See every step." })
  ).toBeInTheDocument();
  for (const link of screen.getAllByRole("link", { name: "Get started" })) {
    expect(link).toHaveAttribute("href", "/register");
  }
  expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/login");
  const github = screen.getAllByRole("link", { name: /github/i });
  expect(github.length).toBeGreaterThan(0);
  github.forEach((l) => expect(l).toHaveAttribute("href", GITHUB_URL));
});

test("signed-in: Open app replaces Get started", async () => {
  signIn();
  mockFetch({ "/auth/me": [{ status: 200, body: TEST_USER }] });
  renderApp("/");
  const open = await screen.findAllByRole("link", { name: "Open app" });
  open.forEach((l) => expect(l).toHaveAttribute("href", "/app"));
  expect(screen.queryByRole("link", { name: "Get started" })).not.toBeInTheDocument();
});

test("pipeline lists the nine steps in order", async () => {
  mockFetch({});
  renderApp("/");
  const pipeline = await screen.findByRole("list", { name: "RAG pipeline" });
  expect(within(pipeline).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
    "Upload",
    "Chunk",
    "FAISS + BM25",
    "Question",
    "Jev analysis",
    "Hybrid search",
    "Jev rerank",
    "LLM answer",
    "Jev guard",
  ]);
});

test("six feature cards and the privacy footer", async () => {
  mockFetch({});
  renderApp("/");
  const features = await screen.findByRole("region", { name: "What's inside" });
  expect(within(features).getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual([
    "Hybrid retrieval",
    "Jev decisions",
    "Full traces",
    "Citations",
    "Guardrails",
    "Private documents",
  ]);
  expect(screen.getByRole("contentinfo")).toHaveTextContent(
    "Document text is sent to OpenRouter and TypeSafe to answer questions."
  );
});
