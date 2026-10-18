const STACK = ["FastAPI", "FAISS", "BM25", "Jev", "OpenRouter", "React"];

export function StackStrip() {
  return (
    <section aria-label="Built with" className="border-y-2 border-ink bg-primary text-primary-foreground">
      <ul className="mx-auto flex max-w-6xl flex-wrap justify-center gap-x-10 gap-y-3 px-4 py-6 font-mono text-sm font-bold tracking-wide sm:px-6">
        {STACK.map((name) => (
          <li key={name}>{name}</li>
        ))}
      </ul>
    </section>
  );
}
