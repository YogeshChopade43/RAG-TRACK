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
      {/* The one accent glow on the page */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-x-0 -top-40 h-[480px] bg-[radial-gradient(ellipse_at_top,color-mix(in_oklab,var(--primary)_18%,transparent),transparent_65%)]"
      />
      <div className="relative mx-auto grid max-w-6xl items-center gap-12 px-4 py-16 sm:px-6 md:py-24 lg:grid-cols-2">
        <div>
          <Badge variant="outline" className="mb-5 text-muted-foreground">
            Open-source RAG system · FastAPI + React
          </Badge>
          <h1 className="text-4xl font-semibold tracking-tight text-balance sm:text-5xl">
            Ask your documents. See every step.
          </h1>
          <p className="mt-5 max-w-xl text-lg text-muted-foreground text-pretty">
            Upload a PDF, ask questions, and get cited answers — with a full trace of how each answer was
            retrieved, ranked and checked.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
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
