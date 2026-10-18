const STACK = ["FastAPI", "FAISS", "BM25", "Jev", "OpenRouter", "React"];

export function StackStrip() {
  return (
    <section aria-label="Built with" className="border-t">
      <ul className="mx-auto flex max-w-6xl flex-wrap justify-center gap-x-10 gap-y-3 px-4 py-10 font-mono text-sm font-medium tracking-wide text-muted-foreground sm:px-6">
        {STACK.map((name) => (
          <li key={name}>{name}</li>
        ))}
      </ul>
    </section>
  );
}
