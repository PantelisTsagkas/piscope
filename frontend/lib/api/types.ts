import type { components } from "./schema";

type Schemas = components["schemas"];

export type HealthResponse = Schemas["HealthResponse"];
export type DatasetInfo = Schemas["DatasetInfoResponse"];
export type DigitRange = Schemas["DigitRangeResponse"];
export type SearchRequest = Schemas["SearchRequest"];
export type SearchResponse = Schemas["SearchResponse"];
export type SearchMatch = Schemas["SearchMatch"];
export type FrequencyResponse = Schemas["FrequencyResponse"];
export type DigitFrequency = Schemas["DigitFrequencyModel"];
export type NgramResponse = Schemas["NgramResponse"];
export type NgramRow = Schemas["NgramRow"];
export type StatisticsRequest = Schemas["StatisticsRequest"];
export type StatisticsResponse = Schemas["StatisticsResponse"];
export type TestResult = Schemas["TestResultModel"];
export type CompareRequest = Schemas["CompareRequest"];
export type CompareResponse = Schemas["CompareResponse"];
export type SimulatedStatistic = Schemas["SimulatedStatisticModel"];
export type WindowResponse = Schemas["WindowResponse"];
export type RunsResponse = Schemas["RunsResponse"];
export type ObservationsResponse = Schemas["ObservationsResponse"];
export type Observation = Schemas["Observation"];
export type Experiment = Schemas["ExperimentModel"];
export type ExperimentList = Schemas["ExperimentListResponse"];
export type ErrorEnvelope = Schemas["ErrorResponse"];

export type TestKey = NonNullable<StatisticsRequest["tests"]>[number];
export type NgramSort = "count_desc" | "count_asc" | "ngram";

export const TEST_KEYS: readonly TestKey[] = [
  "chi_square",
  "shannon_entropy",
  "autocorrelation",
  "runs",
  "ngram_blocks",
];

export const TEST_LABELS: Record<TestKey, string> = {
  chi_square: "Chi-square goodness of fit",
  shannon_entropy: "Shannon entropy",
  autocorrelation: "Autocorrelation",
  runs: "Runs test",
  ngram_blocks: "N-gram block distribution",
};
