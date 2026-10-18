import { MessageSquare } from "lucide-react";

const STARTERS = ["Summarise this document", "Who is this about?", "What are the key points?"];

export function EmptyState(props: { fileName: string; onPick(question: string): void }) {
  return (
    <div className="grid place-items-center gap-4 py-12 text-center">
      <MessageSquare aria-hidden className="size-8 text-primary" />
      <h1 className="text-lg font-semibold text-balance">Ask anything about {props.fileName}</h1>
      <p className="text-sm text-muted-foreground">Every answer cites its pages and comes with a full trace.</p>
      <div className="mt-2 flex flex-wrap justify-center gap-2">
        {STARTERS.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => props.onPick(q)}
            className="rounded-xl border bg-card px-4 py-2 text-sm transition-colors hover:border-primary/60 focus-visible:outline-2 focus-visible:outline-ring"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
