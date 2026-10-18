import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";

// React Router's data router builds `new Request(url, { signal })` on every
// navigation. Under jsdom the signal comes from jsdom's AbortController, which
// Node's own Request rejects ("Expected signal to be an instance of AbortSignal").
// Browsers don't have this mismatch; in tests we drop the foreign signal.
const NodeRequest = globalThis.Request;
globalThis.Request = class extends NodeRequest {
  constructor(input: RequestInfo | URL, init?: RequestInit) {
    if (init?.signal) {
      const { signal, ...rest } = init;
      super(input, rest);
    } else {
      super(input, init);
    }
  }
} as typeof Request;

afterEach(() => {
  cleanup();
  localStorage.clear();
  sessionStorage.clear();
});
