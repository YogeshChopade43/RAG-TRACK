import { render } from "@testing-library/react";
import { RouterProvider } from "react-router";
import { AppProviders } from "@/providers";
import { createAppRouter } from "@/router";

/** Render the real app (providers + routes) at a URL using an in-memory router. */
export function renderApp(path: string) {
  const router = createAppRouter({ initialEntries: [path] });
  render(
    <AppProviders>
      <RouterProvider router={router} />
    </AppProviders>
  );
  return router;
}

type Reply = { status: number; body?: unknown } | Error;

/** Mock fetch by path prefix; each path has a queue of replies (the last one repeats). */
export function mockFetch(routes: Record<string, Reply[]>) {
  const fn = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
    const url = String(input);
    const key = Object.keys(routes)
      .sort((a, b) => b.length - a.length)
      .find((k) => url.includes(k));
    if (!key) throw new Error(`unexpected fetch ${url}`);
    const queue = routes[key];
    const reply = queue.length > 1 ? queue.shift()! : queue[0];
    if (reply instanceof Error) throw reply;
    const body = reply.body === undefined ? "" : JSON.stringify(reply.body);
    return new Response(body, { status: reply.status });
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

export const TEST_USER = { id: "u1", email: "jane@example.com", full_name: "Jane", is_active: true };
export const TEST_TOKENS = { access_token: "A", refresh_token: "R", token_type: "bearer" };

export function signIn() {
  localStorage.setItem("access_token", "A");
  localStorage.setItem("refresh_token", "R");
  localStorage.setItem("user", JSON.stringify(TEST_USER));
}
