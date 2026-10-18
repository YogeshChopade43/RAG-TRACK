import { Link } from "react-router";
import { cn } from "@/lib/utils";

export function Logo({ className }: { className?: string }) {
  return (
    <Link
      to="/"
      className={cn(
        "inline-flex items-center gap-2 font-semibold tracking-tight text-foreground rounded-md focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring",
        className
      )}
    >
      <span aria-hidden className="text-primary">
        ◆
      </span>
      RAG-TRACK
    </Link>
  );
}
