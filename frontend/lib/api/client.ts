import type {
  CompareRequest,
  CompareResponse,
  DatasetInfo,
  DigitRange,
  ErrorEnvelope,
  ExperimentList,
  FrequencyResponse,
  HealthResponse,
  NgramResponse,
  NgramSort,
  ObservationsResponse,
  RunsResponse,
  SearchRequest,
  SearchResponse,
  StatisticsRequest,
  StatisticsResponse,
  WindowResponse,
} from "./types";

/** Origin of the PiScope API. Inlined at build time, so it must be set when building. */
export const API_ORIGIN = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
  /\/+$/,
  "",
);
export const API_BASE = `${API_ORIGIN}/api/v1`;

/** An error reported by the API, or a failure to reach it (status 0). */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(status: number, code: string, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }

  /** True when the API is up but has no usable digits to serve. */
  get datasetUnavailable(): boolean {
    return this.status === 503;
  }

  /** True when the request never reached the API. */
  get unreachable(): boolean {
    return this.status === 0;
  }
}

type QueryValue = string | number | boolean | null | undefined;

function buildUrl(path: string, query?: Record<string, QueryValue>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value !== null && value !== undefined) params.set(key, String(value));
  }
  const suffix = params.size > 0 ? `?${params.toString()}` : "";
  return `${API_BASE}${path}${suffix}`;
}

function isErrorEnvelope(value: unknown): value is ErrorEnvelope {
  if (typeof value !== "object" || value === null || !("error" in value)) return false;
  const error = (value as { error: unknown }).error;
  return typeof error === "object" && error !== null && "message" in error && "code" in error;
}

async function request<T>(
  path: string,
  options: {
    method?: "GET" | "POST" | "DELETE";
    query?: Record<string, QueryValue>;
    body?: unknown;
    signal?: AbortSignal;
  } = {},
): Promise<T> {
  const { method = "GET", query, body, signal } = options;
  let response: Response;
  try {
    response = await fetch(buildUrl(path, query), {
      method,
      signal,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch (cause) {
    if (cause instanceof DOMException && cause.name === "AbortError") throw cause;
    throw new ApiError(0, "network_error", `Could not reach the PiScope API at ${API_ORIGIN}.`);
  }

  if (response.status === 204) return undefined as T;

  let payload: unknown = null;
  try {
    payload = await response.json();
  } catch {
    // A non-JSON body is handled below as an unexpected response.
  }

  if (!response.ok) {
    if (isErrorEnvelope(payload)) {
      throw new ApiError(response.status, payload.error.code, payload.error.message);
    }
    throw new ApiError(response.status, "unexpected_response", `HTTP ${response.status}`);
  }
  return payload as T;
}

export interface RangeParams {
  start: number;
  count: number | null;
}

export const api = {
  health: (signal?: AbortSignal) => request<HealthResponse>("/health", { signal }),
  datasetInfo: (signal?: AbortSignal) => request<DatasetInfo>("/dataset/info", { signal }),
  digitRange: (start: number, count: number, signal?: AbortSignal) =>
    request<DigitRange>("/digits/range", { query: { start, count }, signal }),
  search: (body: SearchRequest, signal?: AbortSignal) =>
    request<SearchResponse>("/search", { method: "POST", body, signal }),
  frequency: (range: RangeParams, signal?: AbortSignal) =>
    request<FrequencyResponse>("/analysis/frequency", { query: { ...range }, signal }),
  ngrams: (
    params: RangeParams & { n: number; sort: NgramSort; offset: number; limit: number },
    signal?: AbortSignal,
  ) => request<NgramResponse>("/analysis/ngrams", { query: { ...params }, signal }),
  statistics: (body: StatisticsRequest) =>
    request<StatisticsResponse>("/analysis/statistics", { method: "POST", body }),
  compare: (body: CompareRequest) =>
    request<CompareResponse>("/analysis/compare", { method: "POST", body }),
  windows: (params: RangeParams & { windows: number }, signal?: AbortSignal) =>
    request<WindowResponse>("/analysis/windows", { query: { ...params }, signal }),
  runs: (params: RangeParams & { top: number }, signal?: AbortSignal) =>
    request<RunsResponse>("/analysis/runs", { query: { ...params }, signal }),
  observations: (range: RangeParams, signal?: AbortSignal) =>
    request<ObservationsResponse>("/analysis/observations", { query: { ...range }, signal }),
  experiments: (limit: number, kind: string | null, signal?: AbortSignal) =>
    request<ExperimentList>("/experiments", { query: { limit, kind }, signal }),
  clearExperiments: () => request<void>("/experiments", { method: "DELETE" }),
};
