import { useEffect, useState } from "react";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, ApiError } from "@/lib/api";
import { rankedChunks } from "@/lib/trace";
import type { Trace } from "@/lib/types";
import { CheckTab } from "./CheckTab";
import { ContextTab } from "./ContextTab";
import { OverviewTab } from "./OverviewTab";
import { RetrievalTab } from "./RetrievalTab";

// Traces never change once saved, so each is fetched once per page load
const cache = new Map<string, Trace>();

type State = { status: "loading" } | { status: "ready"; trace: Trace } | { status: "error"; message: string };

export function TracePanel({ traceId }: { traceId: string }) {
  const [state, setState] = useState<State>(() => {
    const cached = cache.get(traceId);
    return cached ? { status: "ready", trace: cached } : { status: "loading" };
  });

  useEffect(() => {
    if (cache.has(traceId)) return;
    let cancelled = false;
    api
      .getTrace(traceId)
      .then((trace) => {
        cache.set(traceId, trace);
        if (!cancelled) setState({ status: "ready", trace });
      })
      .catch((err) => {
        if (cancelled) return;
        const message =
          err instanceof ApiError && err.status === 404 ? "Trace not available" : "Couldn't load the trace";
        setState({ status: "error", message });
      });
    return () => {
      cancelled = true;
    };
  }, [traceId]);

  return (
    <section aria-label="Answer trace" className="mt-3 rounded-xl border bg-background">
      {state.status === "loading" && (
        <div data-testid="trace-loading" className="grid gap-2 p-4" aria-busy="true">
          <Skeleton className="h-8 w-72" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-2/3" />
        </div>
      )}
      {state.status === "error" && <p className="p-4 text-sm text-muted-foreground">{state.message}</p>}
      {state.status === "ready" && (
        <Tabs defaultValue="overview" className="gap-0">
          <div className="overflow-x-auto border-b p-1.5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            <TabsList variant="line">
              <TabsTrigger value="overview">Overview</TabsTrigger>
              <TabsTrigger value="retrieval">Retrieval · {rankedChunks(state.trace).length}</TabsTrigger>
              <TabsTrigger value="context">Context</TabsTrigger>
              <TabsTrigger value="check">Answer check</TabsTrigger>
            </TabsList>
          </div>
          <TabsContent value="overview" className="p-4">
            <OverviewTab trace={state.trace} />
          </TabsContent>
          <TabsContent value="retrieval" className="p-4">
            <RetrievalTab trace={state.trace} />
          </TabsContent>
          <TabsContent value="context" className="p-4">
            <ContextTab trace={state.trace} />
          </TabsContent>
          <TabsContent value="check" className="p-4">
            <CheckTab trace={state.trace} />
          </TabsContent>
        </Tabs>
      )}
    </section>
  );
}
