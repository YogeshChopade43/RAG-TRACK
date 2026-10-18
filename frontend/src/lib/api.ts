import type { ApiKeyTest, IngestResponse, QueryResponse, Tokens, Trace, User } from "@/lib/types";

const BASE = import.meta.env.VITE_API_URL || "";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export type ApiConfig = {
  getAccessToken(): string | null;
  getRefreshToken(): string | null;
  onTokens(t: Tokens): void;
  onAuthFailure(): void;
  getLlm(): { key?: string; model?: string };
};

let config: ApiConfig = {
  getAccessToken: () => null,
  getRefreshToken: () => null,
  onTokens: () => {},
  onAuthFailure: () => {},
  getLlm: () => ({}),
};

export function configureApi(c: ApiConfig): void {
  config = c;
}

// Paths where a 401 means "wrong credentials", not "expired token"
const NO_REFRESH = ["/auth/login", "/auth/register", "/auth/refresh"];

type RequestOptions = {
  method?: string;
  json?: unknown;
  body?: BodyInit;
  llm?: { key?: string; model?: string }; // overrides the saved LLM settings
};

/** Parse a body that may be empty, JSON, or HTML (proxies and crashes return HTML). */
function parseBody(text: string): unknown {
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function errorMessage(status: number, data: unknown): string {
  if (data && typeof data === "object") {
    const { detail, message } = data as { detail?: unknown; message?: unknown };
    if (typeof detail === "string") return detail;
    // FastAPI validation errors: [{msg: "..."}]
    if (Array.isArray(detail) && typeof detail[0]?.msg === "string") return detail[0].msg;
    if (typeof message === "string") return message;
  }
  return status >= 500 ? `Server error (${status})` : `Request failed (${status})`;
}

async function send(path: string, opts: RequestOptions): Promise<Response> {
  const headers = new Headers();
  const token = config.getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const { key, model } = opts.llm ?? config.getLlm();
  if (key) headers.set("X-User-OpenRouter-Key", key);
  if (model) headers.set("X-User-OpenRouter-Model", model);

  let body = opts.body;
  if (opts.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(opts.json);
  }
  try {
    return await fetch(BASE + path, { method: opts.method ?? "GET", headers, body });
  } catch {
    throw new ApiError(0, "Can't reach the server");
  }
}

let refreshing: Promise<boolean> | null = null;

/** Exchange the refresh token for new tokens. Concurrent callers share one request. */
function refresh(): Promise<boolean> {
  if (!refreshing) {
    refreshing = (async () => {
      const refreshToken = config.getRefreshToken();
      if (!refreshToken) {
        // Nothing to renew the session with: sign out rather than keep a dead session
        config.onAuthFailure();
        return false;
      }
      try {
        const tokens = await request<Tokens>("/auth/refresh", {
          method: "POST",
          json: { refresh_token: refreshToken },
        });
        config.onTokens(tokens);
        return true;
      } catch (e) {
        // Only a real rejection of the refresh token signs out; a network
        // hiccup or a 5xx during a backend restart must not
        if (e instanceof ApiError && (e.status === 401 || e.status === 403)) config.onAuthFailure();
        return false;
      }
    })().finally(() => {
      refreshing = null;
    });
  }
  return refreshing;
}

/** True when a JWT's `exp` is within `marginSeconds` (malformed tokens: false, let the server decide). */
function expiresSoon(token: string, marginSeconds = 60): boolean {
  try {
    const payload = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const { exp } = JSON.parse(atob(payload));
    return typeof exp === "number" && exp * 1000 - Date.now() < marginSeconds * 1000;
  } catch {
    return false;
  }
}

async function request<T>(path: string, opts: RequestOptions = {}, retried = false): Promise<T> {
  // /query and /ingest treat an expired token as anonymous instead of answering
  // 401, so refresh before sending rather than waiting for a 401 that never comes
  const token = config.getAccessToken();
  const authPath = NO_REFRESH.some((p) => path.startsWith(p));
  if (token && !authPath && expiresSoon(token)) await refresh();

  const res = await send(path, opts);
  const data = parseBody(await res.text());
  if (res.ok) return data as T;

  const canRefresh =
    res.status === 401 && !retried && config.getAccessToken() && !authPath;
  if (canRefresh && (await refresh())) return request<T>(path, opts, true);

  throw new ApiError(res.status, errorMessage(res.status, data));
}

export const api = {
  login: (email: string, password: string) =>
    request<Tokens>("/auth/login", { method: "POST", json: { email, password } }),
  register: (email: string, password: string, fullName?: string) =>
    request<User>("/auth/register", { method: "POST", json: { email, password, full_name: fullName || null } }),
  me: () => request<User>("/auth/me"),
  logout: async () => {
    await request<unknown>("/auth/logout", { method: "POST" });
  },
  refresh,
  // The key under test is sent explicitly: it is not saved yet
  testApiKey: (key: string, model: string) =>
    request<ApiKeyTest>("/auth/test-api-key", { method: "POST", llm: { key, model } }),
  uploadDocument: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<IngestResponse>("/ingest", { method: "POST", body: form });
  },
  query: (documentId: string, question: string) =>
    request<QueryResponse>("/query", { method: "POST", json: { document_id: documentId, question } }),
  getTrace: (traceId: string) => request<Trace>(`/query/trace/${encodeURIComponent(traceId)}`),
};
