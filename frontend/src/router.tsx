import { lazy, Suspense } from "react";
import { createBrowserRouter, createMemoryRouter, type RouteObject } from "react-router";
import { FullPageSpinner, RedirectIfAuthed, RequireAuth } from "@/components/RouteGuards";
import Login from "@/pages/Login";
import NotFound from "@/pages/NotFound";
import Register from "@/pages/Register";
import RouteError from "@/pages/RouteError";

// Code-split pages: the landing page never downloads the app's code
const Landing = lazy(() => import("@/pages/Landing"));
const AppPage = lazy(() => import("@/pages/AppPage"));

const routes: RouteObject[] = [
  {
    errorElement: <RouteError />,
    children: [
      {
        path: "/",
        element: (
          <Suspense fallback={<FullPageSpinner />}>
            <Landing />
          </Suspense>
        ),
      },
      {
        path: "/login",
        element: (
          <RedirectIfAuthed>
            <Login />
          </RedirectIfAuthed>
        ),
      },
      {
        path: "/register",
        element: (
          <RedirectIfAuthed>
            <Register />
          </RedirectIfAuthed>
        ),
      },
      {
        path: "/app",
        element: (
          <RequireAuth>
            <Suspense fallback={<FullPageSpinner />}>
              <AppPage />
            </Suspense>
          </RequireAuth>
        ),
      },
      { path: "*", element: <NotFound /> },
    ],
  },
];

export function createAppRouter(opts?: { initialEntries?: string[] }) {
  return opts?.initialEntries ? createMemoryRouter(routes, opts) : createBrowserRouter(routes);
}
