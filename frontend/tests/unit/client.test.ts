import { describe, expect, it, vi } from "vitest";

import { api, API_BASE, ApiError } from "@/lib/api/client";

import { errorBody, fixtures, mockApi } from "../helpers";

describe("api client", () => {
  it("calls the versioned API and returns the parsed body", async () => {
    const requests = mockApi();
    const info = await api.datasetInfo();
    expect(info.total_digits).toBe(1_000_000);
    expect(API_BASE).toMatch(/\/api\/v1$/);
    expect(requests).toHaveLength(1);
    expect(requests[0]?.path).toBe("/dataset/info");
  });

  it("sends range parameters in the query string and omits null ones", async () => {
    const requests = mockApi();
    await api.frequency({ start: 5, count: null });
    await api.ngrams({ start: 1, count: 1000, n: 3, sort: "ngram", offset: 25, limit: 25 });
    expect(requests[0]?.query.toString()).toBe("start=5");
    expect(Object.fromEntries(requests[1]?.query ?? [])).toEqual({
      start: "1",
      count: "1000",
      n: "3",
      sort: "ngram",
      offset: "25",
      limit: "25",
    });
  });

  it("posts JSON bodies", async () => {
    const requests = mockApi();
    await api.search({ pattern: "314159", start: 1, offset: 0, limit: 100 });
    expect(requests[0]?.method).toBe("POST");
    expect(requests[0]?.body).toEqual({ pattern: "314159", start: 1, offset: 0, limit: 100 });
  });

  it("turns the API error envelope into an ApiError", async () => {
    mockApi({
      "GET /digits/range": {
        status: 422,
        body: errorBody("position_out_of_range", "position 2000000 is beyond the last digit"),
      },
    });
    const error = await api.digitRange(2_000_000, 10).catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({
      status: 422,
      code: "position_out_of_range",
      message: "position 2000000 is beyond the last digit",
      datasetUnavailable: false,
      unreachable: false,
    });
  });

  it("flags a missing dataset", async () => {
    mockApi({
      "GET /dataset/info": {
        status: 503,
        body: errorBody("dataset_unavailable", "no dataset found in data"),
      },
    });
    const error = await api.datasetInfo().catch((caught: unknown) => caught);
    expect(error).toMatchObject({ status: 503, datasetUnavailable: true });
  });

  it("reports an unreachable API as status 0", async () => {
    mockApi({ "GET /dataset/info": "network-error" });
    const error = await api.datasetInfo().catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 0, code: "network_error", unreachable: true });
  });

  it("handles a non-JSON error body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("<html>Bad Gateway</html>", { status: 502 })),
    );
    const error = await api.datasetInfo().catch((caught: unknown) => caught);
    expect(error).toMatchObject({ status: 502, code: "unexpected_response" });
  });

  it("resolves an empty 204 response", async () => {
    mockApi();
    await expect(api.clearExperiments()).resolves.toBeUndefined();
  });

  it("returns the recorded search fixture unchanged", async () => {
    mockApi();
    const result = await api.search({ pattern: "314159", start: 1, offset: 0 });
    expect(result).toEqual(fixtures.search);
  });
});
