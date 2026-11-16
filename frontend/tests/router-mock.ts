/**
 * A minimal in-memory stand-in for next/navigation. It keeps one URL, re-renders
 * subscribers when the URL changes, and records every navigation for assertions.
 */
import { useSyncExternalStore } from "react";

let current = new URL("http://localhost/");
const listeners = new Set<() => void>();
export const navigations: { method: "push" | "replace"; url: string }[] = [];

function navigate(method: "push" | "replace", url: string) {
  current = new URL(url, "http://localhost");
  navigations.push({ method, url });
  for (const listener of listeners) listener();
}

/** Set the URL a test starts from, e.g. "/search?q=314159". */
export function setUrl(url: string) {
  current = new URL(url, "http://localhost");
  for (const listener of listeners) listener();
}

export function currentUrl(): string {
  return `${current.pathname}${current.search}`;
}

export function resetRouter() {
  current = new URL("http://localhost/");
  navigations.length = 0;
  listeners.clear();
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

const router = {
  push: (url: string) => navigate("push", url),
  replace: (url: string) => navigate("replace", url),
  back: () => {},
  forward: () => {},
  refresh: () => {},
  prefetch: () => {},
};

export function useRouter() {
  return router;
}

export function usePathname(): string {
  return useSyncExternalStore(subscribe, () => current.pathname);
}

export function useSearchParams(): URLSearchParams {
  const search = useSyncExternalStore(subscribe, () => current.search);
  return new URLSearchParams(search);
}
