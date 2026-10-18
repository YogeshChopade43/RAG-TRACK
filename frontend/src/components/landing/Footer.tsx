import { GITHUB_URL } from "@/lib/constants";

export function Footer() {
  return (
    <footer>
      <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-8 text-sm text-muted-foreground sm:flex-row sm:justify-between sm:px-6">
        <p>
          Built by Yogesh Chopade ·{" "}
          <a href={GITHUB_URL} target="_blank" rel="noreferrer" className="underline-offset-4 hover:text-foreground hover:underline">
            GitHub
          </a>
        </p>
        <p>Document text is sent to OpenRouter and TypeSafe to answer questions.</p>
      </div>
    </footer>
  );
}
