import { Link } from "react-router";
import { ArrowRight } from "lucide-react";
import { GithubIcon } from "@/components/GithubIcon";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import { GITHUB_URL } from "@/lib/constants";
import { ProductPreview } from "./ProductPreview";

export function Hero() {
  const { isAuthenticated } = useAuth();
  return (
    <section className="relative overflow-hidden">
      {/* Faint graph-paper grid behind the hero */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 [mask-image:linear-gradient(to_bottom,black,transparent_85%)] bg-[linear-gradient(to_right,color-mix(in_oklab,var(--ink)_7%,transparent)_1px,transparent_1px),linear-gradient(to_bottom,color-mix(in_oklab,var(--ink)_7%,transparent)_1px,transparent_1px)] bg-[size:40px_40px]"
      />
      <div className="relative mx-auto grid max-w-6xl items-center gap-14 px-4 py-16 sm:px-6 md:py-24 lg:grid-cols-[1.1fr_1fr]">
        <div>
          <Badge
            variant="outline"
            className="mb-7 h-7 gap-2 border-2 bg-card px-3 font-mono text-xs shadow-[2px_2px_0_var(--ink)]"
          >
            <span
              aria-hidden
              className="size-2 rounded-full border border-ink bg-primary"
            />
            Open-source RAG system · FastAPI + React
          </Badge>
          <h1 className="text-5xl leading-[1.05] font-bold tracking-tight text-balance sm:text-6xl lg:text-7xl">
            {/* The decorated spans can split the spoken name ("documents ."), so screen
                readers get the plain sentence and the styled copy is hidden from them */}
            <span className="sr-only">Ask your documents. See every step.</span>
            <span aria-hidden>
              Ask your{" "}
              <span className="relative inline-block text-highlight">
                documents
                {/* Hand-drawn circle around the word */}
                <svg
                  aria-hidden
                  viewBox="0 0 300 100"
                  preserveAspectRatio="none"
                  className="pointer-events-none absolute top-[-18%] left-[-8%] h-[136%] w-[116%]"
                >
                  <path
                    d="M150 8 C 60 6, 8 28, 10 54 C 12 82, 90 96, 168 92 C 250 88, 294 66, 290 42 C 286 18, 220 6, 120 12"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="4"
                    strokeLinecap="round"
                    vectorEffect="non-scaling-stroke"
                  />
                </svg>
              </span>
              . See <span className="marker">every step</span>.
            </span>
          </h1>
          <p className="mt-7 max-w-xl text-lg text-muted-foreground text-pretty">
            Upload a PDF, ask questions, and get cited answers — with a full
            trace of how each answer was retrieved, ranked and checked.
          </p>
          <div className="mt-9 flex flex-wrap gap-4">
            <Button size="lg" asChild>
              {isAuthenticated ? (
                <Link to="/app">
                  Open app <ArrowRight aria-hidden />
                </Link>
              ) : (
                <Link to="/register">
                  Get started <ArrowRight aria-hidden />
                </Link>
              )}
            </Button>
            <Button size="lg" variant="outline" asChild>
              <a href={GITHUB_URL} target="_blank" rel="noreferrer">
                <GithubIcon /> View on GitHub
              </a>
            </Button>
          </div>
        </div>
        <ProductPreview />
      </div>
    </section>
  );
}
