import { Activity, FileText, GitMerge, Lock, ShieldCheck, Sparkles, type LucideIcon } from "lucide-react";

const FEATURES: { title: string; text: string; icon: LucideIcon }[] = [
  { title: "Hybrid retrieval", text: "FAISS vectors + BM25 keywords, fused per query.", icon: GitMerge },
  { title: "Jev decisions", text: "Typed probabilities route, rerank and guard.", icon: Sparkles },
  { title: "Full traces", text: "Timings, scores and context for every answer.", icon: Activity },
  { title: "Citations", text: "Every answer names its file and page.", icon: FileText },
  { title: "Guardrails", text: "Jailbreak, harmful and unsupported checks.", icon: ShieldCheck },
  { title: "Private documents", text: "Each upload belongs to its owner.", icon: Lock },
];

export function Features() {
  return (
    <section aria-labelledby="features-heading" className="border-t">
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6">
        <h2 id="features-heading" className="text-2xl font-semibold tracking-tight">
          What's inside
        </h2>
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ title, text, icon: Icon }) => (
            <div key={title} className="rounded-xl border bg-card p-5 transition-colors hover:border-primary/40">
              <Icon aria-hidden className="size-5 text-primary" />
              <h3 className="mt-3 font-medium">{title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">{text}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
