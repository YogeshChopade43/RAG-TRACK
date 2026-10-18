import { Link } from "react-router";
import { cn } from "@/lib/utils";

export function Logo({ className }: { className?: string }) {
  return (
    <Link
      to="/"
      className={cn(
        "inline-flex items-center gap-2 font-heading font-bold tracking-tight text-foreground rounded-md focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring",
        className
      )}
    >
      <span
        aria-hidden
        className="grid size-7 place-items-center rounded-md border-2 border-ink bg-primary text-xs text-primary-foreground shadow-[2px_2px_0_var(--ink)]"
      >
        ◆
      </span>
      RAG-TRACK
    </Link>
  );
}
