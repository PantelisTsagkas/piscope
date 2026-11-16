// Records API responses into tests/fixtures. Usage: pnpm fixtures [api-origin]
import { writeFile } from "node:fs/promises";

const origin = process.argv[2] ?? "http://127.0.0.1:8000";
const base = `${origin}/api/v1`;
const json = (body) => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

// Order matters: experiments is recorded last so it contains the runs made above it.
const requests = [
  ["health", "/health"],
  ["dataset-info", "/dataset/info"],
  ["digits-range", "/digits/range?start=1&count=500"],
  ["search-314159", "/search", json({ pattern: "314159", limit: 50 })],
  ["search-none", "/search", json({ pattern: "99999999" })],
  ["frequency", "/analysis/frequency"],
  ["ngrams-2", "/analysis/ngrams?n=2&limit=10"],
  ["statistics", "/analysis/statistics", json({ max_lag: 5 })],
  ["compare", "/analysis/compare", json({ count: 10000, seed: 42, simulations: 5, max_lag: 3 })],
  ["windows", "/analysis/windows?windows=10"],
  ["runs", "/analysis/runs?top=5"],
  ["observations", "/analysis/observations"],
  ["experiments", "/experiments?limit=5"],
  ["error-422", "/digits?position=0"],
];

for (const [name, path, init] of requests) {
  const response = await fetch(`${base}${path}`, init);
  const body = await response.json();
  await writeFile(
    new URL(`./fixtures/${name}.json`, import.meta.url),
    `${JSON.stringify(body, null, 2)}\n`,
  );
  console.log(`${response.status} ${name}`);
}
