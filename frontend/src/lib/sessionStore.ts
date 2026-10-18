/**
 * A tiny store over sessionStorage keys that React can subscribe to with
 * useSyncExternalStore, so several components share the same state without a provider.
 */
const listeners = new Set<() => void>();
let version = 0;

export function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/** Changes on every write; components re-read their keys when it changes. */
export function getVersion(): number {
  return version;
}

export function writeSession(values: Record<string, string | null>): void {
  for (const [key, value] of Object.entries(values)) {
    if (value === null) sessionStorage.removeItem(key);
    else sessionStorage.setItem(key, value);
  }
  version++;
  listeners.forEach((l) => l());
}

/** Call after something else (e.g. sign-out) changed sessionStorage directly. */
export function notifySessionChanged(): void {
  version++;
  listeners.forEach((l) => l());
}
