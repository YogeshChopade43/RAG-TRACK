import { useState, type ReactNode } from "react";
import Markdown, { type Components } from "react-markdown";
import { toast } from "sonner";
import { AlertCircle, ChevronDown, Copy, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ChatMessage } from "@/hooks/useChat";
import { cn } from "@/lib/utils";
import { SourceChips } from "./SourceChips";

// Styles for rendered markdown; raw HTML in answers is never rendered (react-markdown default)
const MARKDOWN =
  "space-y-3 leading-relaxed break-words [&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:space-y-1 [&_ol]:pl-5 [&_strong]:font-semibold [&_code]:rounded [&_code]:bg-muted [&_code]:px-1 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-[0.85em] [&_pre]:overflow-x-auto [&_pre]:rounded-md [&_pre]:bg-muted [&_pre]:p-3 [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_a]:text-highlight [&_a]:underline";

const MARKDOWN_COMPONENTS: Components = {
  a: ({ node: _node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" />,
};

export function Message(props: {
  message: ChatMessage;
  onRetry(id: string): void;
  renderTrace?: (traceId: string) => ReactNode;
}) {
  const { message: m } = props;
  const [traceOpen, setTraceOpen] = useState(false);

  if (m.role === "user") {
    return (
      <div className="ml-auto max-w-[85%] rounded-xl border-2 border-ink bg-primary px-4 py-2.5 whitespace-pre-wrap text-primary-foreground shadow-[2px_2px_0_var(--ink)]">
        {m.content}
      </div>
    );
  }

  if (m.status === "pending") {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground" role="status">
        <span className="flex gap-1" aria-hidden>
          {[0, 150, 300].map((delay) => (
            <span
              key={delay}
              className="size-1.5 rounded-full bg-highlight motion-safe:animate-bounce"
              style={{ animationDelay: `${delay}ms` }}
            />
          ))}
        </span>
        Thinking…
      </div>
    );
  }

  if (m.status === "error") {
    return (
      <div className="flex flex-wrap items-center gap-3 rounded-xl border-2 border-destructive/60 bg-destructive/10 px-4 py-3 text-sm text-destructive">
        <AlertCircle aria-hidden className="size-4 shrink-0" />
        <span className="flex-1">{m.error}</span>
        <Button size="sm" variant="outline" onClick={() => props.onRetry(m.id)}>
          <RotateCcw aria-hidden />
          Retry
        </Button>
      </div>
    );
  }

  return (
    <article className="rounded-xl border bg-card px-4 py-3">
      <div className={MARKDOWN}>
        {/* Images are dropped: a prompt-injected document could make the model emit an
            image URL that sends text to a third party without a click */}
        <Markdown disallowedElements={["img"]} unwrapDisallowed components={MARKDOWN_COMPONENTS}>
          {m.content}
        </Markdown>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <SourceChips sources={m.sources} />
        <div className="ml-auto flex gap-1">
          <Button
            size="sm"
            variant="ghost"
            aria-label="Copy answer"
            onClick={async () => {
              try {
                await navigator.clipboard.writeText(m.content);
                toast.success("Copied");
              } catch {
                toast.error("Couldn't copy to the clipboard");
              }
            }}
          >
            <Copy aria-hidden />
          </Button>
          {m.traceId && props.renderTrace && (
            <Button
              size="sm"
              variant="ghost"
              aria-expanded={traceOpen}
              onClick={() => setTraceOpen((o) => !o)}
              className={cn(traceOpen && "text-highlight")}
            >
              Trace
              <ChevronDown aria-hidden className={cn("transition-transform", traceOpen && "rotate-180")} />
            </Button>
          )}
        </div>
      </div>
      {traceOpen && m.traceId && props.renderTrace?.(m.traceId)}
    </article>
  );
}
