import { api, ApiError, configureApi, type ApiConfig } from "@/lib/api";

type Reply = { status: number; body?: string };

/** Queue fetch replies per path prefix, in order. */
function mockFetch(routes: Record<string, Reply[]>) {
  const fn = vi.fn(async (input: RequestInfo | URL, _init?: RequestInit) => {
    const url = String(input);
    const key = Object.keys(routes).find((k) => url.includes(k));
    const reply = key ? routes[key].shift() : undefined;
    if (!reply) throw new Error(`unexpected fetch ${url}`);
    return new Response(reply.body ?? "", { status: reply.status });
  });
  vi.stubGlobal("fetch", fn);
  return fn;
}

const tokens = { access_token: "A2", refresh_token: "R2", token_type: "bearer" };
const user = JSON.stringify({ id: "u1", email: "a@b.co", full_name: null, is_active: true });

let config: ApiConfig;
let access: string | null;

beforeEach(() => {
  access = "A";
  config = {
    getAccessToken: () => access,
    getRefreshToken: () => "R",
    onTokens: vi.fn((t) => {
      access = t.access_token;
    }),
    onAuthFailure: vi.fn(),
    getLlm: () => ({ key: "K", model: "M" }),
  };
  configureApi(config);
});

afterEach(() => vi.unstubAllGlobals());

test("empty 500 body gives ApiError(500) with fallback message", async () => {
  mockFetch({ "/auth/me": [{ status: 500 }] });
  await expect(api.me()).rejects.toMatchObject({ status: 500, message: "Server error (500)" });
});

test("HTML error body does not throw a JSON SyntaxError", async () => {
  mockFetch({ "/auth/me": [{ status: 502, body: "<html>Bad gateway</html>" }] });
  const err = await api.me().catch((e) => e);
  expect(err).toBeInstanceOf(ApiError);
  expect(err.status).toBe(502);
});

test("uses detail from JSON errors", async () => {
  mockFetch({ "/ingest": [{ status: 400, body: JSON.stringify({ detail: "Unsupported file type" }) }] });
  await expect(api.uploadDocument(new File(["x"], "a.txt"))).rejects.toMatchObject({
    status: 400,
    message: "Unsupported file type",
  });
});

test("network failure becomes status 0 with a friendly message", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
  await expect(api.me()).rejects.toMatchObject({ status: 0, message: "Can't reach the server" });
});

test("adds auth and LLM headers and the JSON body", async () => {
  const fetch = mockFetch({
    "/query": [{ status: 200, body: JSON.stringify({ trace_id: "t", question: "q", answer: "a", sources: [] }) }],
  });
  await api.query("doc", "q");
  const init = fetch.mock.calls[0][1] as RequestInit;
  const headers = new Headers(init.headers);
  expect(headers.get("Authorization")).toBe("Bearer A");
  expect(headers.get("X-User-OpenRouter-Key")).toBe("K");
  expect(headers.get("X-User-OpenRouter-Model")).toBe("M");
  expect(init.body).toBe(JSON.stringify({ document_id: "doc", question: "q" }));
});

test("401 refreshes once and retries with the new token", async () => {
  const fetch = mockFetch({
    "/query": [
      { status: 401 },
      { status: 200, body: JSON.stringify({ trace_id: "t", question: "q", answer: "a", sources: [] }) },
    ],
    "/auth/refresh": [{ status: 200, body: JSON.stringify(tokens) }],
  });
  await expect(api.query("doc", "q")).resolves.toMatchObject({ answer: "a" });
  expect(config.onTokens).toHaveBeenCalledWith(tokens);
  const retry = fetch.mock.calls.filter((c) => String(c[0]).includes("/query"))[1][1] as RequestInit;
  expect(new Headers(retry.headers).get("Authorization")).toBe("Bearer A2");
});

test("parallel 401s share one refresh", async () => {
  const fetch = mockFetch({
    "/auth/me": [{ status: 401 }, { status: 401 }, { status: 200, body: user }, { status: 200, body: user }],
    "/auth/refresh": [{ status: 200, body: JSON.stringify(tokens) }],
  });
  await Promise.all([api.me(), api.me()]);
  expect(fetch.mock.calls.filter((c) => String(c[0]).includes("/auth/refresh"))).toHaveLength(1);
});

test("refresh failure rejects both calls and signs out once", async () => {
  mockFetch({
    "/auth/me": [{ status: 401 }, { status: 401 }],
    "/auth/refresh": [{ status: 401 }],
  });
  const results = await Promise.allSettled([api.me(), api.me()]);
  expect(results.map((r) => r.status)).toEqual(["rejected", "rejected"]);
  expect((results[0] as PromiseRejectedResult).reason.status).toBe(401);
  expect(config.onAuthFailure).toHaveBeenCalledTimes(1);
});

/** A JWT whose payload has the given exp (seconds); signature irrelevant to the client. */
function jwt(exp: number) {
  const b64 = (o: object) => btoa(JSON.stringify(o)).replace(/=+$/, "").replace(/\+/g, "-").replace(/\//g, "_");
  return `${b64({ alg: "HS256" })}.${b64({ sub: "u1", exp, type: "access" })}.sig`;
}

test("an expired access token is refreshed before the request is sent", async () => {
  // /query and /ingest treat an expired token as anonymous (no 401), so the
  // client must not wait for a 401 to refresh
  access = jwt(Math.floor(Date.now() / 1000) - 10);
  const fetch = mockFetch({
    "/auth/refresh": [{ status: 200, body: JSON.stringify(tokens) }],
    "/query": [{ status: 200, body: JSON.stringify({ trace_id: "t", question: "q", answer: "a", sources: [] }) }],
  });
  await api.query("doc", "q");
  const urls = fetch.mock.calls.map((c) => String(c[0]));
  expect(urls[0]).toContain("/auth/refresh");
  const queryCall = fetch.mock.calls.find((c) => String(c[0]).includes("/query"))!;
  expect(new Headers((queryCall[1] as RequestInit).headers).get("Authorization")).toBe("Bearer A2");
});

test("a token that is still valid is not refreshed before sending", async () => {
  access = jwt(Math.floor(Date.now() / 1000) + 600);
  const fetch = mockFetch({
    "/query": [{ status: 200, body: JSON.stringify({ trace_id: "t", question: "q", answer: "a", sources: [] }) }],
  });
  await api.query("doc", "q");
  expect(fetch.mock.calls.some((c) => String(c[0]).includes("/auth/refresh"))).toBe(false);
});

test("a server error during refresh does not sign the user out", async () => {
  mockFetch({ "/auth/me": [{ status: 401 }], "/auth/refresh": [{ status: 503 }] });
  await expect(api.me()).rejects.toMatchObject({ status: 401 });
  expect(config.onAuthFailure).not.toHaveBeenCalled();
});

test("a 401 with no refresh token signs out instead of leaving a dead session", async () => {
  configureApi({ ...config, getRefreshToken: () => null });
  mockFetch({ "/auth/me": [{ status: 401 }] });
  await expect(api.me()).rejects.toMatchObject({ status: 401 });
  expect(config.onAuthFailure).toHaveBeenCalledTimes(1);
});

test("no refresh for a failed login", async () => {
  const fetch = mockFetch({
    "/auth/login": [{ status: 401, body: JSON.stringify({ detail: "Incorrect email or password" }) }],
  });
  await expect(api.login("a@b.co", "x")).rejects.toMatchObject({ message: "Incorrect email or password" });
  expect(fetch.mock.calls.some((c) => String(c[0]).includes("/auth/refresh"))).toBe(false);
});

test("uploadDocument sends FormData without a JSON content type", async () => {
  const fetch = mockFetch({
    "/ingest": [{ status: 200, body: JSON.stringify({ filename: "a.txt", document_id: "d", status: "completed" }) }],
  });
  await api.uploadDocument(new File(["x"], "a.txt"));
  const init = fetch.mock.calls[0][1] as RequestInit;
  expect(init.body).toBeInstanceOf(FormData);
  expect(new Headers(init.headers).get("Content-Type")).toBeNull();
});
