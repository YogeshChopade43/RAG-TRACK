import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DocumentHealth } from "@/components/health/DocumentHealth";
import { api } from "@/lib/api";
import type { DocSettings, StressReport } from "@/lib/types";
import trace from "@/test/fixtures/trace.json";

const base: StressReport = {
  run_id: "r1",
  document_id: "d1",
  size: 20,
  status: "done",
  progress: { done: 3, total: 3 },
  started_at: "2026-10-23T10:00:00Z",
  finished_at: "2026-10-23T10:01:30Z",
  settings_used: { top_k: 8, min_relevance: 0.1, source: "default" },
  summary: {
    correct: 1,
    answerable: 2,
    retrieval_hits: 1,
    unanswerable: 1,
    unanswerable_handled: 0,
    hallucinations: 1,
    cost_usd: 0.012,
    tokens: 9100,
    by_kind: { direct: { correct: 1, total: 1 }, messy: { correct: 0, total: 1 }, unanswerable: { correct: 0, total: 1 } },
  },
  items: [
    { id: "q1", kind: "direct", question: "Who is Yogesh?", expected_answer: "An AI engineer", page_number: 1, answer: "An AI engineer.", answer_status: "answered", correct: true, retrieval_hit: true, hallucinated: false, trace_id: "t1" },
    { id: "q2", kind: "messy", question: "wher did he studdy", expected_answer: "Pune University", page_number: 2, answer: "I could not find the answer in the document.", answer_status: "not_found", correct: false, retrieval_hit: false, hallucinated: false, trace_id: "t2" },
    { id: "q3", kind: "unanswerable", question: "What is his salary?", expected_answer: null, page_number: null, answer: "About $90k.", answer_status: "answered", correct: false, retrieval_hit: null, hallucinated: true, trace_id: "t3" },
  ],
  tune: {
    available: true,
    best: { min_relevance: 0.05, top_k: 8 },
    validation: { correct: 2, hallucinations: 1, retrieval_hits: 2, cost_usd: 0.011 },
    recommend: true,
    reason: null,
  },
  error: null,
};

function setup(opts: { history?: StressReport[]; reports?: StressReport[]; applied?: DocSettings | null } = {}) {
  vi.spyOn(api, "listStressTests").mockResolvedValue(opts.history ?? []);
  const get = vi.spyOn(api, "getStressTest");
  for (const r of opts.reports ?? [base]) get.mockResolvedValueOnce(r);
  get.mockResolvedValue((opts.reports ?? [base]).at(-1)!);
  const start = vi.spyOn(api, "startStressTest").mockResolvedValue({ run_id: "r1" });
  const docSettings = vi
    .spyOn(api, "getDocSettings")
    .mockResolvedValue({ settings: opts.applied ?? null, defaults: { top_k: 8, min_relevance: 0.1 } });
  render(<DocumentHealth open onOpenChange={() => {}} documentId="d1" fileName="cv.pdf" pollMs={5} />);
  return { start, get, docSettings };
}

afterEach(() => vi.restoreAllMocks());

test("start view shows an estimate and sends the chosen size", async () => {
  const { start } = setup();
  expect(await screen.findByText(/about 1–2 min/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "50 questions" }));
  expect(screen.getByText(/about 3–5 min/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "Start test" }));
  expect(start).toHaveBeenCalledWith("d1", 50);
});

test("polls while running, then shows the score cards", async () => {
  const running = { ...base, status: "running" as const, progress: { done: 1, total: 3 }, summary: null, tune: null };
  setup({ reports: [running, base] });
  await userEvent.click(await screen.findByRole("button", { name: "Start test" }));
  expect(await screen.findByText(/1 correct of 2/)).toBeInTheDocument();
  expect(screen.getByText("1 hallucination")).toBeInTheDocument();
  expect(screen.getByText(/1 found of 2/)).toBeInTheDocument();
});

test("failures-only filter hides the passing question", async () => {
  setup({ history: [base] });
  const list = await screen.findByRole("list", { name: "Test questions" });
  expect(within(list).getAllByRole("listitem")).toHaveLength(3);
  await userEvent.click(screen.getByRole("button", { name: "Failures only" }));
  expect(within(list).getAllByRole("listitem")).toHaveLength(2);
  expect(within(list).queryByText("Who is Yogesh?")).not.toBeInTheDocument();
});

test("a question opens its trace", async () => {
  setup({ history: [base] });
  const getTrace = vi.spyOn(api, "getTrace").mockResolvedValue(trace as never);
  const list = await screen.findByRole("list", { name: "Test questions" });
  await userEvent.click(within(list).getAllByRole("button", { name: "Open trace" })[1]);
  await waitFor(() => expect(getTrace).toHaveBeenCalledWith("t2"));
});

test("Apply saves the validated settings; Reset restores defaults", async () => {
  setup({ history: [base] });
  const save = vi.spyOn(api, "saveDocSettings").mockResolvedValue({ settings: { top_k: 8, min_relevance: 0.05 } });
  const reset = vi.spyOn(api, "resetDocSettings").mockResolvedValue({});
  const card = await screen.findByRole("region", { name: "Auto-tune" });
  expect(within(card).getByText(/0\.1 → 0\.05/)).toBeInTheDocument();
  expect(within(card).getByText(/1 → 2 correct/)).toBeInTheDocument();
  // Apply appears once the currently applied settings have loaded
  await userEvent.click(await within(card).findByRole("button", { name: "Apply" }));
  expect(save).toHaveBeenCalledWith("d1", { top_k: 8, min_relevance: 0.05, applied_from_run: "r1" });
  await userEvent.click(await within(card).findByRole("button", { name: "Reset to defaults" }));
  expect(reset).toHaveBeenCalledWith("d1");
});

test("a failed run shows its error and can be retried", async () => {
  const failed = { ...base, status: "failed" as const, error: "The model could only generate 3 of 20 test questions." };
  setup({ history: [failed], reports: [failed] });
  expect(await screen.findByText(/could only generate 3 of 20/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Start test" })).toBeInTheDocument();
});

test("the report breaks results down by question type", async () => {
  setup({ history: [base] });
  const breakdown = await screen.findByRole("list", { name: "Results by question type" });
  expect(within(breakdown).getByText("Direct")).toBeInTheDocument();
  expect(within(breakdown).getByText("1/1")).toBeInTheDocument();
  expect(within(breakdown).getByText("Messy typing")).toBeInTheDocument();
  expect(within(breakdown).getAllByText("0/1")).toHaveLength(2);
});


test("Apply is offered for a better recommendation even when other tuned settings are applied", async () => {
  const usedTuned = { ...base, settings_used: { top_k: 8, min_relevance: 0.15, source: "document" as const } };
  setup({ history: [usedTuned], reports: [usedTuned], applied: { top_k: 8, min_relevance: 0.15 } });
  const card = await screen.findByRole("region", { name: "Auto-tune" });
  expect(await within(card).findByRole("button", { name: "Apply" })).toBeInTheDocument();
  expect(within(card).getByRole("button", { name: "Reset to defaults" })).toBeInTheDocument();
});

test("no Apply once the recommended settings are already applied", async () => {
  setup({ history: [base], applied: { top_k: 8, min_relevance: 0.05 } });
  const card = await screen.findByRole("region", { name: "Auto-tune" });
  expect(await within(card).findByText("Applied")).toBeInTheDocument();
  expect(within(card).queryByRole("button", { name: "Apply" })).not.toBeInTheDocument();
});

test("the cost line says what it covers", async () => {
  setup({ history: [base] });
  expect(await screen.findByText(/answering cost.*excludes writing, grading and validating the questions/)).toBeInTheDocument();
});
