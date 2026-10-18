import { Check } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { LlmKeyForm } from "./LlmKeyForm";

export type Step = "connect" | "upload" | "chat";

const STEPS: { id: Step; label: string }[] = [
  { id: "connect", label: "Connect model" },
  { id: "upload", label: "Upload a document" },
  { id: "chat", label: "Ask a question" },
];

export function StepIndicator({ current }: { current: Step }) {
  const currentIndex = STEPS.findIndex((s) => s.id === current);
  return (
    <ol aria-label="Setup progress" className="flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
      {STEPS.map((step, i) => {
        const done = i < currentIndex;
        const active = i === currentIndex;
        return (
          <li
            key={step.id}
            aria-current={active ? "step" : undefined}
            className={cn("flex items-center gap-2", active ? "font-semibold text-foreground" : "text-muted-foreground")}
          >
            <span
              aria-hidden
              className={cn(
                "grid size-7 place-items-center rounded-full border-2 font-mono text-xs font-bold",
                active && "border-ink bg-primary text-primary-foreground shadow-[2px_2px_0_var(--ink)]",
                done && "border-ink bg-foreground text-background"
              )}
            >
              {done ? <Check className="size-3.5" /> : i + 1}
            </span>
            {step.label}
          </li>
        );
      })}
    </ol>
  );
}

export function ConnectStep() {
  return (
    <Card className="mx-auto w-full max-w-lg">
      <CardHeader>
        <CardTitle>
          <h1 className="text-lg font-semibold">Connect your model</h1>
        </CardTitle>
        <CardDescription>
          RAG-TRACK answers with the OpenRouter model you choose. Paste your key and a model name, then test them.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <LlmKeyForm submitLabel="Test & continue" onVerified={() => {}} />
      </CardContent>
    </Card>
  );
}
