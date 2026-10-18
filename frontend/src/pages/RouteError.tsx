import { useRouteError } from "react-router";
import { Button } from "@/components/ui/button";

/** Shown when a page throws while rendering or loading. */
export default function RouteError() {
  const error = useRouteError();
  console.error(error);
  return (
    <main className="grid min-h-dvh place-items-center px-4 text-center">
      <div className="grid gap-4">
        <h1 className="text-2xl font-semibold tracking-tight">Something went wrong</h1>
        <p className="text-muted-foreground">An unexpected error stopped this page from loading.</p>
        <div className="flex justify-center gap-2">
          <Button onClick={() => window.location.reload()}>Reload</Button>
          <Button variant="outline" asChild>
            {/* A plain link: the router may be the thing that failed */}
            <a href="/">Home</a>
          </Button>
        </div>
      </div>
    </main>
  );
}
