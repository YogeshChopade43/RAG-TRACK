import type { ReactNode } from "react";
import { Logo } from "@/components/Logo";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

/** Centred auth card with the logo above it; never stretches to the page height. */
export function AuthLayout(props: { title: string; description: string; children: ReactNode; footer: ReactNode }) {
  return (
    <main className="grid min-h-dvh place-items-center px-4 py-10">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex justify-center">
          <Logo className="text-lg" />
        </div>
        <Card>
          <CardHeader>
            <CardTitle>
              <h1 className="text-xl font-semibold tracking-tight">{props.title}</h1>
            </CardTitle>
            <CardDescription>{props.description}</CardDescription>
          </CardHeader>
          <CardContent>{props.children}</CardContent>
        </Card>
        <p className="mt-4 text-center text-sm text-muted-foreground">{props.footer}</p>
      </div>
    </main>
  );
}

export function FieldError({ id, children }: { id: string; children?: string }) {
  if (!children) return null;
  return (
    <p id={id} className="text-sm text-destructive">
      {children}
    </p>
  );
}

export function FormAlert({ children }: { children?: string | null }) {
  if (!children) return null;
  return (
    <div role="alert" className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
      {children}
    </div>
  );
}
