"use client";

import { Suspense, useSyncExternalStore } from "react";

import { PageSkeleton } from "./states";

const subscribe = () => () => {};

/** False on the server and during hydration, true afterwards. */
export function useHydrated(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );
}

/**
 * Renders a page only in the browser. Every page reads its state from the URL and its data
 * from the API over HTTP, so there is nothing useful to render on the server, and waiting
 * for hydration keeps the first client render identical to the prerendered skeleton.
 */
export function ClientPage({ children }: { children: React.ReactNode }) {
  const hydrated = useHydrated();
  return <Suspense fallback={<PageSkeleton />}>{hydrated ? children : <PageSkeleton />}</Suspense>;
}
