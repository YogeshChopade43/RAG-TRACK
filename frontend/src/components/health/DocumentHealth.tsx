import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { CheckCircle2, CircleAlert, Loader2, XCircle } from "lucide-react";
import { TracePanel } from "@/components/trace/TracePanel";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { api } from "@/lib/api";
import type { DocSettings, StressItem, StressReport, StressSummary } from "@/lib/types";
import { cn, formatCost, formatTokens } from "@/lib/utils";

const SIZES = [
  { n: 10, time: "under a minute", cost: "$0.005–0.015" },
  { n: 20, time: "1–2 min", cost: "$0.01–0.03" },
  { n: 50, time: "3–5 min", cost: "$0.03–0.08" },
] as const;
const FINAL = new Set(["done", "failed"]);
const PHASES: Record<string, string> = {
  generating: "Writing test questions…",
  running: "Answering the questions",
  tuning: "Searching for better settings…",
  validating: "Re-running with the best settings to confirm…",
};
const KIND_LABEL: Record<string, string> = {
  direct: "Direct",
  reworded: "Reworded",
  messy: "Messy typing",
  unanswerable: "Not in document",
};

/** Run a stress test on one document, show what failed, and apply validated settings. */
export function DocumentHealth(props: {
  open: boolean;
  onOpenChange(open: boolean): void;
  documentId: string;
  fileName: string;
  pollMs?: number;
}) {
  const { documentId, pollMs = 1000 } = props;
  const [report, setReport] = useState<StressReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState(false);
  const [view, setView] = useState<"start" | "report">("start");

  // Open on the latest run, if there is one
  useEffect(() => {
    if (!props.open) return;
    let cancelled = false;
    setLoading(true);
    api
      .listStressTests(documentId)
      .then(async (runs) => {
        if (!runs.length) return null;
        return api.getStressTest(documentId, runs[0].run_id);
      })
      .then((latest) => {
        if (cancelled) return;
        setReport(latest);
        setView(latest && latest.status !== "failed" ? "report" : "start");
      })
      .catch(() => !cancelled && setView("start"))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [props.open, documentId]);

  // Poll an unfinished run
  const runId = report?.run_id;
  const running = !!report && !FINAL.has(report.status);
  useEffect(() => {
    if (!running || !runId) return;
    const id = setInterval(async () => {
      try {
        const next = await api.getStressTest(documentId, runId);
        setReport(next);
        if (FINAL.has(next.status)) setView(next.status === "failed" ? "start" : "report");
      } catch {
        // transient: keep polling
      }
    }, pollMs);
    return () => clearInterval(id);
  }, [running, runId, documentId, pollMs]);

  const start = useCallback(
    async (size: number) => {
      setStarting(true);
      try {
        const { run_id } = await api.startStressTest(documentId, size);
        setReport({
          run_id,
          document_id: documentId,
          size,
          status: "generating",
          progress: { done: 0, total: size },
          started_at: new Date().toISOString(),
          finished_at: null,
          settings_used: { top_k: 0, min_relevance: 0, source: "default" },
          summary: null,
          items: [],
          tune: null,
          error: null,
        });
        setView("report");
      } catch (err) {
        toast.error(err instanceof Error ? err.message : "Couldn't start the test");
      } finally {
        setStarting(false);
      }
    },
    [documentId]
  );

  return (
    <Dialog open={props.open} onOpenChange={props.onOpenChange}>
      <DialogContent className="max-h-[88dvh] overflow-y-auto sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>Document health</DialogTitle>
          <DialogDescription>
            Test how well RAG-TRACK answers questions about <span className="font-medium">{props.fileName}</span>, see
            what fails, and apply settings that measurably do better.
          </DialogDescription>
        </DialogHeader>
        {loading ? (
          <Loader2 aria-label="Loading" className="mx-auto my-8 size-6 animate-spin text-muted-foreground" />
        ) : view === "start" || !report ? (
          <StartView failed={report?.status === "failed" ? report.error : null} starting={starting} onStart={start} />
        ) : running ? (
          <RunningView report={report} />
        ) : (
          <ReportView report={report} documentId={documentId} onRunAgain={() => setView("start")} />
        )}
      </DialogContent>
    </Dialog>
  );
}

function StartView(props: { failed: string | null; starting: boolean; onStart(size: number): void }) {
  const [size, setSize] = useState(20);
  const est = SIZES.find((s) => s.n === size)!;
  return (
    <div className="grid gap-4">
      {props.failed && (
        <p role="alert" className="flex items-start gap-2 rounded-md border-2 border-destructive/60 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <CircleAlert aria-hidden className="mt-0.5 size-4 shrink-0" />
          {props.failed}
        </p>
      )}
      <p className="text-sm text-muted-foreground">
        RAG-TRACK writes questions from your document (plus some it can't answer), runs each through the real
        pipeline on your model, and grades the answers. Each question gets a full trace.
      </p>
      <div className="flex flex-wrap gap-2" role="group" aria-label="Number of questions">
        {SIZES.map((s) => (
          <Button
            key={s.n}
            type="button"
            variant={size === s.n ? "default" : "outline"}
            aria-pressed={size === s.n}
            onClick={() => setSize(s.n)}
          >
            {s.n} questions
          </Button>
        ))}
      </div>
      <p className="font-mono text-xs text-muted-foreground">
        ~{size} questions · about {est.time} · roughly {est.cost} on a gpt-4o-mini-class model (more on larger ones)
      </p>
      <div>
        <Button size="lg" disabled={props.starting} onClick={() => props.onStart(size)}>
          {props.starting && <Loader2 className="animate-spin" aria-hidden />}
          Start test
        </Button>
      </div>
    </div>
  );
}

function RunningView({ report }: { report: StressReport }) {
  const { done, total } = report.progress;
  const answering = report.status === "running";
  return (
    <div className="grid gap-3 py-2" aria-live="polite">
      <p className="text-sm font-medium">
        {answering ? `${PHASES.running}: ${done} of ${total}` : PHASES[report.status]}
      </p>
      <Progress
        value={answering && total ? (done / total) * 100 : null}
        aria-label="Stress test progress"
        className="h-2"
      />
      <p className="text-xs text-muted-foreground">You can close this window; the test keeps running.</p>
    </div>
  );
}

function ScoreCard(props: { title: string; value: string; note?: string; warn?: boolean }) {
  return (
    <div className="rounded-xl border-2 border-ink bg-card p-4 shadow-[3px_3px_0_var(--ink)]">
      <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">{props.title}</p>
      <p className="mt-1 font-heading text-2xl font-bold">{props.value}</p>
      {props.note && (
        <p className={cn("mt-0.5 text-xs", props.warn ? "font-semibold text-destructive" : "text-muted-foreground")}>
          {props.note}
        </p>
      )}
    </div>
  );
}

function ByKind({ s }: { s: StressSummary }) {
  const kinds = Object.entries(s.by_kind);
  if (!kinds.length) return null;
  return (
    <ul aria-label="Results by question type" className="flex flex-wrap gap-2">
      {kinds.map(([kind, r]) => (
        <li key={kind} className="flex items-center gap-2 rounded-full border px-3 py-1 text-xs">
          <span>{KIND_LABEL[kind] ?? kind}</span>
          <span className="font-mono font-semibold">{`${r!.correct}/${r!.total}`}</span>
        </li>
      ))}
    </ul>
  );
}

function Scores({ s }: { s: StressSummary }) {
  return (
    <div className="grid gap-3 sm:grid-cols-3">
      <ScoreCard title="Correct answers" value={`${s.correct} correct of ${s.answerable}`} />
      <ScoreCard title="Retrieval" value={`${s.retrieval_hits} found of ${s.answerable}`} note="source passage reached the model" />
      <ScoreCard
        title="Not in document"
        value={`${s.unanswerable_handled} handled of ${s.unanswerable}`}
        note={`${s.hallucinations} hallucination${s.hallucinations === 1 ? "" : "s"}`}
        warn={s.hallucinations > 0}
      />
    </div>
  );
}

function isFailure(i: StressItem) {
  return i.correct === false || i.hallucinated;
}

function ItemRow({ item }: { item: StressItem }) {
  const [open, setOpen] = useState(false);
  const Icon = item.correct ? CheckCircle2 : item.correct === false ? XCircle : CircleAlert;
  return (
    <li className="rounded-lg border p-3">
      <div className="flex items-start gap-2">
        <Icon
          aria-label={item.correct ? "passed" : item.correct === false ? "failed" : "not graded"}
          className={cn("mt-0.5 size-4 shrink-0", item.correct ? "text-success" : item.correct === false ? "text-destructive" : "text-muted-foreground")}
        />
        <div className="grid min-w-0 flex-1 gap-1">
          <p className="text-sm font-medium break-words">{item.question}</p>
          <p className="font-mono text-[11px] text-muted-foreground">
            {KIND_LABEL[item.kind]}
            {item.page_number != null && ` · from p.${item.page_number}`}
            {item.retrieval_hit === false && " · source passage not retrieved"}
            {item.hallucinated && " · answered something not in the document"}
          </p>
          {item.expected_answer && (
            <p className="text-xs break-words">
              <span className="text-muted-foreground">Expected: </span>
              {item.expected_answer}
            </p>
          )}
          <p className="text-xs break-words">
            <span className="text-muted-foreground">Answer: </span>
            {item.answer ?? "(blocked by the safety filter)"}
          </p>
        </div>
        {item.trace_id && (
          <Button size="sm" variant="ghost" aria-expanded={open} onClick={() => setOpen((o) => !o)}>
            Open trace
          </Button>
        )}
      </div>
      {open && item.trace_id && <TracePanel traceId={item.trace_id} />}
    </li>
  );
}

function TuneCard({ report, documentId }: { report: StressReport; documentId: string }) {
  const tune = report.tune;
  // What is applied *now* (may differ from what this run used); undefined while loading
  const [current, setCurrent] = useState<DocSettings | null | undefined>(undefined);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let cancelled = false;
    api
      .getDocSettings(documentId)
      .then((r) => !cancelled && setCurrent(r.settings))
      .catch(() => !cancelled && setCurrent(null));
    return () => {
      cancelled = true;
    };
  }, [documentId]);
  if (!tune) return null;
  const cur = report.settings_used;
  const best = tune.best;
  const bestApplied =
    !!current && !!best && current.top_k === best.top_k && current.min_relevance === best.min_relevance;

  async function apply() {
    if (!best) return;
    setBusy(true);
    try {
      await api.saveDocSettings(documentId, { ...best, applied_from_run: report.run_id });
      setCurrent(best);
      toast.success("Settings applied to this document");
    } catch {
      toast.error("Couldn't apply the settings");
    } finally {
      setBusy(false);
    }
  }

  async function reset() {
    setBusy(true);
    try {
      await api.resetDocSettings(documentId);
      setCurrent(null);
      toast.success("Back to the default settings");
    } catch {
      toast.error("Couldn't reset the settings");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label="Auto-tune" className="rounded-xl border-2 border-dashed p-4">
      <h3 className="font-heading font-semibold">Auto-tune</h3>
      {tune.recommend && best && tune.validation && report.summary ? (
        <div className="mt-2 grid gap-1 text-sm">
          <p className="font-mono text-xs">
            Relevance bar {cur.min_relevance} → {best.min_relevance} · Top-k {cur.top_k} → {best.top_k}
          </p>
          <p>
            Measured on a real re-run: {report.summary.correct} → {tune.validation.correct} correct ·{" "}
            {report.summary.hallucinations} → {tune.validation.hallucinations} hallucinations
          </p>
        </div>
      ) : (
        <p className="mt-2 text-sm text-muted-foreground">{tune.reason}</p>
      )}
      <div className="mt-3 flex flex-wrap gap-2">
        {tune.recommend && best && current !== undefined && !bestApplied && (
          <Button size="sm" disabled={busy} onClick={apply}>
            Apply
          </Button>
        )}
        {bestApplied && <span className="self-center text-xs font-semibold text-success">Applied</span>}
        {current && (
          <Button size="sm" variant="outline" disabled={busy} onClick={reset}>
            Reset to defaults
          </Button>
        )}
      </div>
    </section>
  );
}

function ReportView(props: { report: StressReport; documentId: string; onRunAgain(): void }) {
  const { report } = props;
  const [failuresOnly, setFailuresOnly] = useState(false);
  const s = report.summary;
  const items = failuresOnly ? report.items.filter(isFailure) : report.items;
  return (
    <div className="grid gap-4">
      {s && <Scores s={s} />}
      {s && <ByKind s={s} />}
      {s && (
        <p className="font-mono text-xs text-muted-foreground">
          answering cost:{" "}
          {[formatTokens(s.tokens), s.cost_usd != null ? formatCost(s.cost_usd) : null].filter(Boolean).join(" · ")}{" "}
          (excludes writing, grading and validating the questions) · settings: relevance bar{" "}
          {report.settings_used.min_relevance}, top-k {report.settings_used.top_k} ({report.settings_used.source})
        </p>
      )}
      <TuneCard report={report} documentId={props.documentId} />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-medium">Questions</h3>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" aria-pressed={failuresOnly} onClick={() => setFailuresOnly((f) => !f)}>
            Failures only
          </Button>
          <Button size="sm" variant="outline" onClick={props.onRunAgain}>
            Run again
          </Button>
        </div>
      </div>
      <ol aria-label="Test questions" className="grid gap-2">
        {items.map((i) => (
          <ItemRow key={i.id} item={i} />
        ))}
      </ol>
    </div>
  );
}
