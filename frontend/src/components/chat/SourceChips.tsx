import { FileText } from "lucide-react";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import type { Source } from "@/lib/types";

export function SourceChips({ sources }: { sources: Source[] }) {
  if (!sources.length) return null;
  return (
    <ul aria-label="Sources" className="flex flex-wrap gap-1.5">
      {sources.map((s) => (
        <li key={`${s.file_name}-${s.page_number}`}>
          <Tooltip>
            <TooltipTrigger asChild>
              <span
                tabIndex={0}
                className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-xs text-muted-foreground focus-visible:outline-2 focus-visible:outline-ring"
              >
                <FileText aria-hidden className="size-3" />
                {s.page_number ? `p.${s.page_number}` : s.file_name}
              </span>
            </TooltipTrigger>
            <TooltipContent>{s.file_name}</TooltipContent>
          </Tooltip>
        </li>
      ))}
    </ul>
  );
}
