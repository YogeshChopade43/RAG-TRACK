import { Link } from "react-router";
import { Logo } from "@/components/Logo";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <main className="grid min-h-dvh place-items-center px-4 text-center">
      <div className="grid gap-4">
        <Logo className="justify-self-center" />
        <p className="font-mono text-sm text-muted-foreground">404</p>
        <h1 className="text-2xl font-semibold tracking-tight">Page not found</h1>
        <p className="text-muted-foreground">The page you're looking for doesn't exist.</p>
        <Button asChild className="justify-self-center">
          <Link to="/">Back home</Link>
        </Button>
      </div>
    </main>
  );
}
