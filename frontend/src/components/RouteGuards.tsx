import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

export function FullPageSpinner() {
  return (
    <div className="grid min-h-dvh place-items-center" role="status" aria-label="Loading">
      <Loader2 className="size-6 animate-spin text-muted-foreground" aria-hidden />
    </div>
  );
}

/** Only signed-in users; others go to /login and come back afterwards. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated, ready } = useAuth();
  const location = useLocation();
  if (!isAuthenticated) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (!ready) return <FullPageSpinner />;
  return children;
}

/** Auth pages are for signed-out users only. */
export function RedirectIfAuthed({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  return isAuthenticated ? <Navigate to="/app" replace /> : children;
}
