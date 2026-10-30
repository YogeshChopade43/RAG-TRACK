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

describe("transparency fields", () => {
  const candidate = (i: number, jev: number, status: "kept" | "dropped") => ({
    chunk_id: `c${i}`,
    file_name: "cv.pdf",
    page_number: i,
    content: `passage ${i}`,
    found_by: ["Yogesh"],
    vector: 0.4,
    bm25: null,
    fused: 0.5,
    jev,
    status,
    reason: status === "kept" ? null : ("below_min_relevance" as const),
  });
  const v2: Trace = {
    ...base,
    expanded_queries: ["Yogesh"],
    candidates: [
      candidate(1, 0.92, "kept"),
      ...Array.from({ length: 14 }, (_, i) => candidate(i + 2, 0.05, "dropped")),
    ],
    calls: [
      {
        kind: "jev",
        purpose: "analysis",
        model: "typesafe/jev-1.14",
        start_ms: 0,
        duration_ms: 300,
        prompt_tokens: null,
        completion_tokens: null,
        cost_usd: null,
        ok: true,
        error: null,
      },
      {
        kind: "llm",
        purpose: "answer",
        model: "openai/gpt-4o-mini",
        start_ms: 900,
        duration_ms: 1600,
        prompt_tokens: 1500,
        completion_tokens: 400,
        cost_usd: 0.0004,
        ok: true,
        error: null,
      },
    ],
    decision_sources: { analysis: "jev", rerank: "fusion", guard: "jev" },
    answer_status: "answered",
  };

  async function openTab(name: RegExp) {
    show(v2);
    await userEvent.click(await screen.findByRole("tab", { name }));
    return screen.getByRole("tabpanel");
  }

  test("retrieval lists every candidate with a found → kept headline", async () => {
    const panel = await openTab(/Retrieval/);
    expect(within(panel).getByText("15 found → 1 kept")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Retrieval · 1/15" })).toBeInTheDocument();
    const list = within(panel).getByRole("list", { name: "Candidates" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(15);
    expect(within(list).getAllByText("below relevance bar")).toHaveLength(14);
  });

  test("OCR-derived candidates carry an OCR badge", async () => {
    show({ ...v2, candidates: [{ ...candidate(1, 0.9, "kept"), ocr: true }, candidate(2, 0.05, "dropped")] });
    await userEvent.click(await screen.findByRole("tab", { name: /Retrieval/ }));
    const items = within(screen.getByRole("list", { name: "Candidates" })).getAllByRole("listitem");
    expect(within(items[0]).getByTitle("Text read from an image by OCR")).toHaveTextContent("OCR");
    expect(within(items[1]).queryByText("OCR")).not.toBeInTheDocument();
  });

  test("the dropped filter hides kept candidates", async () => {
    const panel = await openTab(/Retrieval/);
    await userEvent.click(within(panel).getByRole("button", { name: "Dropped" }));
    const list = within(panel).getByRole("list", { name: "Candidates" });
    expect(within(list).getAllByRole("listitem")).toHaveLength(14);
    expect(within(list).queryByText("kept")).not.toBeInTheDocument();
  });

  test("overview shows one timeline row per model call with tokens, cost and a total", async () => {
    show(v2);
    const panel = await screen.findByRole("tabpanel");
    const calls = within(panel).getByRole("list", { name: "Model calls" });
    const rows = within(calls).getAllByRole("listitem");
    expect(rows).toHaveLength(2);
    expect(within(rows[1]).getByText(/1\.9k tokens/)).toBeInTheDocument();
    expect(within(rows[1]).getByText("$0.0004")).toBeInTheDocument();
    expect(within(panel).getByText(/Total: 1\.9k tokens · \$0\.0004 excl\. Jev/)).toBeInTheDocument();
  });

  test("overview flags decisions that fell back to the built-in rules", async () => {
    show(v2);
    const panel = await screen.findByRole("tabpanel");
    expect(within(panel).getByText("Jev fallback: rerank")).toBeInTheDocument();
  });

  test("an old trace without these fields keeps the previous views", async () => {
    show(base);
    const panel = await screen.findByRole("tabpanel");
    expect(within(panel).queryByRole("list", { name: "Model calls" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: /Retrieval/ }));
    expect(within(screen.getByRole("tabpanel")).getByText(/Chunks sent to the model/)).toBeInTheDocument();
  });
});

test("overview names document-specific settings when they answered the question", async () => {
  show({ ...base, settings_used: { top_k: 6, min_relevance: 0.05, source: "document" } });
  const panel = await screen.findByRole("tabpanel");
  expect(within(panel).getByText(/Document settings: relevance bar 0\.05 · top-k 6/)).toBeInTheDocument();
});
