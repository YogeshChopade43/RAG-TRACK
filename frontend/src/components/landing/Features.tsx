import { Activity, FileText, GitMerge, Lock, ShieldCheck, Sparkles, type LucideIcon } from "lucide-react";

// Pastel blocks keep near-black text in both themes
const FEATURES: { title: string; text: string; icon: LucideIcon; tone: string }[] = [
  { title: "Hybrid retrieval", text: "FAISS vectors + BM25 keywords, fused per query.", icon: GitMerge, tone: "bg-[#fde68a]" },
  { title: "Jev decisions", text: "Typed probabilities route, rerank and guard.", icon: Sparkles, tone: "bg-[#fbcfe8]" },
  { title: "Full traces", text: "Timings, scores and context for every answer.", icon: Activity, tone: "bg-[#bae6fd]" },
  { title: "Citations", text: "Every answer names its file and page.", icon: FileText, tone: "bg-[#d9f99d]" },
  { title: "Guardrails", text: "Jailbreak, harmful and unsupported checks.", icon: ShieldCheck, tone: "bg-[#ddd6fe]" },
  { title: "Private documents", text: "Each upload belongs to its owner.", icon: Lock, tone: "bg-[#fed7aa]" },
];

export function Features() {
  return (
    <section aria-labelledby="features-heading" className="border-t-2 border-ink">
      <div className="mx-auto max-w-6xl px-4 py-20 sm:px-6">
        <p className="font-mono text-xs font-semibold tracking-widest text-highlight uppercase">Features</p>
        <h2 id="features-heading" className="mt-2 text-3xl font-bold tracking-tight sm:text-4xl">
          What's inside
        </h2>
        <div className="mt-10 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map(({ title, text, icon: Icon, tone }) => (
            <div
              key={title}
              className={`rounded-xl border-2 border-ink p-6 text-[#030712] shadow-[5px_5px_0_var(--ink)] transition-[translate,box-shadow] hover:translate-x-1 hover:translate-y-1 hover:shadow-[1px_1px_0_var(--ink)] ${tone}`}
            >
              <span className="grid size-10 place-items-center rounded-lg border-2 border-[#030712] bg-white">
                <Icon aria-hidden className="size-5" />
              </span>
              <h3 className="mt-4 text-lg font-bold">{title}</h3>
              <p className="mt-1 text-sm text-[#292524]">{text}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
