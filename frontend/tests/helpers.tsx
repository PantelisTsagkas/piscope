import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { vi } from "vitest";

import { TooltipProvider } from "@/components/ui/tooltip";

import compare from "./fixtures/compare.json";
import datasetInfo from "./fixtures/dataset-info.json";
import digitsRange from "./fixtures/digits-range.json";
import experiments from "./fixtures/experiments.json";
import frequency from "./fixtures/frequency.json";
import ngrams from "./fixtures/ngrams-2.json";
import observations from "./fixtures/observations.json";
import runs from "./fixtures/runs.json";
import search from "./fixtures/search-314159.json";
import statistics from "./fixtures/statistics.json";
import windows from "./fixtures/windows.json";

/** Responses recorded from the real API (see tests/fixtures/README.md). */
export const fixtures = {
  compare,
  datasetInfo,
  digitsRange,
  experiments,
  frequency,
  ngrams,
  observations,
  runs,
  search,
  statistics,
  windows,
};

export function renderWithProviders(ui: ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>{ui}</TooltipProvider>
    </QueryClientProvider>,
  );
}

export interface RecordedRequest {
  method: string;
  path: string;
  query: URLSearchParams;
  body: unknown;
}

type Reply = { status?: number; body?: unknown } | "network-error";
type Handler = Reply | ((request: RecordedRequest) => Reply);

export function errorBody(code: string, message: string) {
  return { error: { code, message } };
}

/** The recorded fixtures, keyed the way `mockApi` expects. */
export function defaultRoutes(): Record<string, Handler> {
  return {
    "GET /dataset/info": { body: datasetInfo },
    "GET /digits/range": { body: digitsRange },
    "POST /search": { body: search },
    "GET /analysis/frequency": { body: frequency },
    "GET /analysis/ngrams": { body: ngrams },
    "GET /analysis/windows": { body: windows },
    "GET /analysis/runs": { body: runs },
    "GET /analysis/observations": { body: observations },
    "POST /analysis/statistics": { body: statistics },
    "POST /analysis/compare": { body: compare },
    "GET /experiments": { body: experiments },
    "DELETE /experiments": { status: 204 },
  };
}

/**
 * Replace `fetch` with a router over "METHOD /path" keys (paths relative to /api/v1).
 * Returns the list of requests made, for assertions. Unknown routes fail the test.
 */
export function mockApi(overrides: Record<string, Handler> = {}): RecordedRequest[] {
  const routes = { ...defaultRoutes(), ...overrides };
  const requests: RecordedRequest[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: string | URL, init?: RequestInit) => {
      const url = new URL(String(input));
      const request: RecordedRequest = {
        method: init?.method ?? "GET",
        path: url.pathname.replace(/^\/api\/v1/, ""),
        query: url.searchParams,
        body: typeof init?.body === "string" ? JSON.parse(init.body) : undefined,
      };
      requests.push(request);
      const handler = routes[`${request.method} ${request.path}`];
      if (handler === undefined) {
        throw new Error(`unexpected request: ${request.method} ${request.path}`);
      }
      const reply = typeof handler === "function" ? handler(request) : handler;
      if (reply === "network-error") throw new TypeError("Failed to fetch");
      const status = reply.status ?? 200;
      return new Response(status === 204 ? null : JSON.stringify(reply.body ?? {}), {
        status,
        headers: { "Content-Type": "application/json" },
      });
    }),
  );
  return requests;
}
