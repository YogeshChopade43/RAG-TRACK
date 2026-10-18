import { MessageSquare } from "lucide-react";

const STARTERS = ["Summarise this document", "Who is this about?", "What are the key points?"];

export function EmptyState(props: { fileName: string; onPick(question: string): void }) {
  return (
    <div className="grid place-items-center gap-4 py-12 text-center">
      <span aria-hidden className="grid size-12 place-items-center rounded-lg border-2 border-ink bg-primary text-primary-foreground shadow-[3px_3px_0_var(--ink)]">
        <MessageSquare className="size-6" />
      </span>
      <h1 className="text-2xl font-bold tracking-tight text-balance">Ask anything about {props.fileName}</h1>
      <p className="text-sm text-muted-foreground">Every answer cites its pages and comes with a full trace.</p>
      <div className="mt-2 flex flex-wrap justify-center gap-2">
        {STARTERS.map((q) => (
          <button
            key={q}
            type="button"
            onClick={() => props.onPick(q)}
            className="rounded-lg border-2 border-ink bg-card px-4 py-2 text-sm font-medium shadow-[2px_2px_0_var(--ink)] transition-[translate,box-shadow,background-color] hover:bg-primary hover:text-primary-foreground hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}
