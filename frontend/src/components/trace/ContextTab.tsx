import { toast } from "sonner";
import { Copy } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Trace } from "@/lib/types";

const show = (v: unknown, suffix = "") => (v === null || v === undefined ? "–" : `${v}${suffix}`);

export function ContextTab({ trace }: { trace: Trace }) {
  const settings: [string, string][] = [
    ["Provider", show(trace.llm_provider)],
    ["Model", show(trace.llm_model)],
    ["Temperature", show(trace.llm_temperature)],
    ["Max tokens", show(trace.llm_max_tokens)],
    ["Timeout", show(trace.llm_timeout_seconds, " s")],
  ];

  return (
    <div className="grid gap-5">
      <div className="grid gap-2">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium">Context sent to the model</h3>
          {trace.final_context && (
            <Button
              size="sm"
              variant="ghost"
              aria-label="Copy context"
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(trace.final_context ?? "");
                  toast.success("Copied");
                } catch {
                  toast.error("Couldn't copy to the clipboard");
                }
              }}
            >
              <Copy aria-hidden />
            </Button>
          )}
        </div>
        {trace.final_context ? (
          <pre className="max-h-80 overflow-auto rounded-lg border bg-muted/40 p-3 font-mono text-xs leading-relaxed whitespace-pre-wrap">
            {trace.final_context}
          </pre>
        ) : (
          <p className="text-sm text-muted-foreground">Not recorded</p>
        )}
      </div>

      <dl className="grid grid-cols-[8rem_1fr] gap-1.5 text-sm">
        {settings.map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="text-muted-foreground">{label}</dt>
            <dd className="font-mono text-xs leading-5">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
