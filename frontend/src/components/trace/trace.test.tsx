import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { TracePanel } from "@/components/trace/TracePanel";
import { api, ApiError } from "@/lib/api";
import type { Trace } from "@/lib/types";
import fixture from "@/test/fixtures/trace.json";

const base = fixture as unknown as Trace;
let n = 0;

/** Each test uses its own trace id so the panel's per-trace cache can't leak between tests. */
function show(trace: Trace | Error = base) {
  const id = `trace-${++n}`;
  const spy = vi.spyOn(api, "getTrace");
  if (trace instanceof Error) spy.mockRejectedValue(trace);
  else spy.mockResolvedValue(trace);
  render(<TracePanel traceId={id} />);
}

afterEach(() => vi.restoreAllMocks());

test("shows a skeleton while loading, then four tabs", async () => {
  show();
  expect(screen.getByTestId("trace-loading")).toBeInTheDocument();
  const tabs = await screen.findAllByRole("tab");
  expect(tabs.map((t) => t.textContent)).toEqual(["Overview", "Retrieval · 1", "Context", "Answer check"]);
});

test("overview shows stage durations and the rewrite state", async () => {
  show();
  const panel = await screen.findByRole("tabpanel");
  expect(within(panel).getByText("2.30 s")).toBeInTheDocument();
  expect(within(panel).getByText("568 ms")).toBeInTheDocument();
  expect(within(panel).getByText("1.69 s")).toBeInTheDocument();
  expect(within(panel).getByText("rewritten")).toBeInTheDocument();
});

test("overview says skipped when the query was not rewritten", async () => {
  show({ ...base, rewritten_query: base.original_query });
  const panel = await screen.findByRole("tabpanel");
  expect(within(panel).getByText("skipped")).toBeInTheDocument();
});

test("overview shows Jev decisions with their probabilities", async () => {
  show();
  const decisions = await screen.findByRole("list", { name: "Jev decisions" });
  const items = within(decisions)
    .getAllByRole("listitem")
    .map((li) => li.textContent);
  expect(items).toEqual([
    expect.stringContaining("split"),
    expect.stringContaining("rewrite"),
    expect.stringContaining("jailbreak"),
    expect.stringContaining("harmful"),
    expect.stringContaining("unsupported"),
    expect.stringContaining("harmful output"),
  ]);
  ["0.04", "0.78", "0.02", "0.06", "0.01"].forEach((v) => expect(decisions).toHaveTextContent(v));
});

test("retrieval lists ranked chunks with Jev and fusion scores; Show more expands", async () => {
  show();
  await userEvent.click(await screen.findByRole("tab", { name: /Retrieval/ }));
  const panel = screen.getByRole("tabpanel");
  expect(within(panel).getByText("0.92")).toBeInTheDocument();
  expect(within(panel).getByText("0.85")).toBeInTheDocument();
  expect(within(panel).getByText("Who is Yogesh ?")).toBeInTheDocument();
  await userEvent.click(within(panel).getByRole("button", { name: "Show more" }));
  expect(within(panel).getByRole("button", { name: "Show less" })).toBeInTheDocument();
});

test("without Jev reranking the chunk score is not labelled as a Jev score", async () => {
  show({ ...base, reranked_chunks: [] });
  await userEvent.click(await screen.findByRole("tab", { name: /Retrieval/ }));
  const panel = screen.getByRole("tabpanel");
  expect(within(panel).queryByText(/^jev/)).not.toBeInTheDocument();
  expect(within(panel).getByText(/^retrieval score/)).toBeInTheDocument();
});

test("context shows the exact context and LLM settings", async () => {
  show();
  await userEvent.click(await screen.findByRole("tab", { name: "Context" }));
  const panel = screen.getByRole("tabpanel");
  expect(within(panel).getByText(/AI \/ GenAI Engineer/)).toBeInTheDocument();
  expect(within(panel).getByText("openai/gpt-4o-mini")).toBeInTheDocument();
  expect(within(panel).getByText("0")).toBeInTheDocument();
});

test("answer check shows meters with thresholds and a verdict", async () => {
  show();
  await userEvent.click(await screen.findByRole("tab", { name: "Answer check" }));
  const panel = screen.getByRole("tabpanel");
  expect(within(panel).getByText("No issues found")).toBeInTheDocument();
  expect(within(panel).getByText(/threshold 0\.85/)).toBeInTheDocument();
  expect(within(panel).getByText(/threshold 0\.7/)).toBeInTheDocument();
});

test("missing Jev metadata renders Not recorded instead of breaking", async () => {
  show({ ...base, metadata: undefined });
  const panel = await screen.findByRole("tabpanel");
  expect(within(panel).getByText("Not recorded")).toBeInTheDocument();
  await userEvent.click(screen.getByRole("tab", { name: "Answer check" }));
  expect(within(screen.getByRole("tabpanel")).getByText("Not recorded")).toBeInTheDocument();
});

test("a missing trace says Trace not available", async () => {
  show(new ApiError(404, "Trace not found"));
  expect(await screen.findByText("Trace not available")).toBeInTheDocument();
});
