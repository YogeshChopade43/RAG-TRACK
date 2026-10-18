import { Link } from "react-router";
import { GithubIcon } from "@/components/GithubIcon";
import { ThemeToggle } from "@/components/app/ThemeToggle";
import { Logo } from "@/components/Logo";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import { GITHUB_URL } from "@/lib/constants";

export function Nav() {
  const { isAuthenticated } = useAuth();
  return (
    <header className="sticky top-0 z-40 border-b bg-background/80 backdrop-blur">
      <nav aria-label="Main" className="mx-auto flex h-14 max-w-6xl items-center gap-2 px-4 sm:px-6">
        <Logo />
        <div className="ml-auto flex items-center gap-1 sm:gap-2">
          <Button variant="ghost" size="sm" asChild className="hidden sm:inline-flex">
            <a href={GITHUB_URL} target="_blank" rel="noreferrer">
              <GithubIcon />
              GitHub
            </a>
          </Button>
          <ThemeToggle />
          {isAuthenticated ? (
            <Button size="sm" asChild>
              <Link to="/app">Open app</Link>
            </Button>
          ) : (
            <>
              <Button variant="ghost" size="sm" asChild>
                <Link to="/login">Sign in</Link>
              </Button>
              <Button size="sm" asChild>
                <Link to="/register">Get started</Link>
              </Button>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}
