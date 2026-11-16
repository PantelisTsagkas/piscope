"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, type ApiError, type RangeParams } from "./client";
import type {
  CompareRequest,
  CompareResponse,
  NgramSort,
  SearchRequest,
  StatisticsRequest,
  StatisticsResponse,
} from "./types";

declare module "@tanstack/react-query" {
  interface Register {
    // Every query and mutation goes through lib/api/client.ts, which only throws ApiError.
    defaultError: ApiError;
  }
}

const EXPERIMENTS_KEY = ["experiments"] as const;

export function useDatasetInfo() {
  return useQuery({
    queryKey: ["dataset-info"],
    queryFn: ({ signal }) => api.datasetInfo(signal),
    staleTime: 60_000,
  });
}

export function useDigitRange(start: number, count: number, enabled = true) {
  return useQuery({
    queryKey: ["digits", start, count],
    queryFn: ({ signal }) => api.digitRange(start, count, signal),
    placeholderData: keepPreviousData,
    enabled,
  });
}

/** Search is a POST, but it is a read: identical requests return identical results. */
export function useSearch(request: SearchRequest | null) {
  const queryClient = useQueryClient();
  return useQuery({
    queryKey: ["search", request],
    queryFn: async ({ signal }) => {
      const result = await api.search(request as SearchRequest, signal);
      // A new search is appended to the experiment log by the server.
      if (!result.cached) void queryClient.invalidateQueries({ queryKey: EXPERIMENTS_KEY });
      return result;
    },
    enabled: request !== null,
    placeholderData: keepPreviousData,
  });
}

export function useFrequency(range: RangeParams | null) {
  return useQuery({
    queryKey: ["frequency", range],
    queryFn: ({ signal }) => api.frequency(range as RangeParams, signal),
    enabled: range !== null,
    placeholderData: keepPreviousData,
  });
}

export function useNgrams(
  params: (RangeParams & { n: number; sort: NgramSort; offset: number; limit: number }) | null,
) {
  return useQuery({
    queryKey: ["ngrams", params],
    queryFn: ({ signal }) => api.ngrams(params as NonNullable<typeof params>, signal),
    enabled: params !== null,
    placeholderData: keepPreviousData,
  });
}

export function useWindows(params: (RangeParams & { windows: number }) | null) {
  return useQuery({
    queryKey: ["windows", params],
    queryFn: ({ signal }) => api.windows(params as NonNullable<typeof params>, signal),
    enabled: params !== null,
    placeholderData: keepPreviousData,
  });
}

export function useRuns(params: (RangeParams & { top: number }) | null) {
  return useQuery({
    queryKey: ["runs", params],
    queryFn: ({ signal }) => api.runs(params as NonNullable<typeof params>, signal),
    enabled: params !== null,
    placeholderData: keepPreviousData,
  });
}

export function useObservations(range: RangeParams | null) {
  return useQuery({
    queryKey: ["observations", range],
    queryFn: ({ signal }) => api.observations(range as RangeParams, signal),
    enabled: range !== null,
  });
}

export function useExperiments(limit: number, kind: string | null = null) {
  return useQuery({
    queryKey: [...EXPERIMENTS_KEY, limit, kind],
    queryFn: ({ signal }) => api.experiments(limit, kind, signal),
  });
}

export function useClearExperiments() {
  const queryClient = useQueryClient();
  return useMutation<void, ApiError>({
    mutationFn: () => api.clearExperiments(),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: EXPERIMENTS_KEY }),
  });
}

/** Test batteries run only when asked: every run is logged and counts as a comparison. */
export function useRunStatistics() {
  const queryClient = useQueryClient();
  return useMutation<StatisticsResponse, ApiError, StatisticsRequest>({
    mutationFn: (body) => api.statistics(body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: EXPERIMENTS_KEY }),
  });
}

export function useRunComparison() {
  const queryClient = useQueryClient();
  return useMutation<CompareResponse, ApiError, CompareRequest>({
    mutationFn: (body) => api.compare(body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: EXPERIMENTS_KEY }),
  });
}
