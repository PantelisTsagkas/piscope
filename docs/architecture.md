# Architecture

## Layers

```text
frontend/   Next.js UI. Talks to the API over HTTP only; computes nothing itself.
backend/    piscope-api: FastAPI routers, Pydantic schemas, request limits,
            search cache, experiment log. No mathematics lives here.
engine/     piscope-engine: digit storage, generation, search, statistics,
            pattern analysis. NumPy and SciPy only.
data/       Chunk files and manifest.json. Generated, not committed.
```

Dependencies point one way: frontend -> API -> engine -> files. The engine never imports
FastAPI, Pydantic or the API package. Two checks enforce that: a ruff banned-import rule
and `engine/tests/test_architecture.py`, which parses every engine module.

### Deviation from the suggested layout

The brief suggested `backend/piscope_engine/` as a folder inside the backend. The engine
is instead its own installable package (`engine/`, src layout, own `pyproject.toml`) in a
uv workspace with the API. Reason: "can be distributed as a standalone package" is then
true by construction, and the API can only reach the engine through its public imports.
One `uv.lock` at the repository root covers both packages.

Engine modules:

| Module | Responsibility |
| --- | --- |
| `digits.indexing` | Position, chunk index and offset conversions |
| `digits.manifest` | `manifest.json` schema, validation, atomic save |
| `digits.store` | Read-only memory-mapped retrieval, checksum verification |
| `digits.writer` | Chunked, atomic writing and expansion |
| `digits.generation` | Chudnovsky generator and Gauss-Legendre verifier |
| `digits.build` | Generate, verify, store; reference-file comparison |
| `search.sequence` | Exact sequence search across chunk boundaries |
| `statistics.*` | Frequency, n-grams, hypothesis tests, corrections, simulation |
| `patterns.*` | Runs of repeated digits, windowed concentration |

Storage, generation, indexing and search do not depend on each other except through
`DigitStore` (search reads from it) and plain NumPy arrays (generation hands arrays to the
writer).

## Indexing convention

Position 1 is the first digit after the decimal point: in 3.14159, position 1 holds 1.
The integer digit 3 is not stored and has no position. Every public function, API field
and UI label uses this convention. Chunk indices and byte offsets are 0-based and stay
inside the storage layer.

    chunk_index = (position - 1) // chunk_size
    offset      = (position - 1) %  chunk_size

## Storage format

```text
data/
  manifest.json
  chunk-000000.bin     positions         1 .. 1,000,000
  chunk-000001.bin     positions 1,000,001 .. 2,000,000
```

- One unsigned byte per digit, value 0-9 (not ASCII). A chunk file is exactly as many
  bytes as it has digits, so file size is a free integrity check.
- Chunks hold 1,000,000 digits. Only the last chunk may be shorter, and the manifest flags
  it `complete: false`, so a partial dataset is never presented as complete.
- `manifest.json` records total digits, chunk size, per-chunk SHA-256 and digit count, the
  generator and its parameters, and every verification that was run.
- `DigitStore` memory-maps chunks lazily and keeps at most 64 maps open (LRU, guarded by a
  lock). Memory and file handles stay bounded at any dataset size.
- Opening a store checks the manifest and every chunk's size. The API also recomputes all
  SHA-256 checksums at startup and refuses to serve a dataset that fails.

One byte per digit is 2.4 times larger than a packed encoding, and deliberately so: a
digit is addressable without decoding, NumPy can operate on a mapped chunk directly, and
`bytes.find` works on the raw bytes. One billion digits is 1 GB on disk, which is
acceptable.

### Scaling

Nothing in the format or the store depends on dataset size. 10 million digits is 10
chunks, 1 billion is 1,000 chunks, read through the same code. What does not scale to a
billion digits is listed here rather than hidden:

- **Generation is in memory.** `chudnovsky_digits` holds the whole number as one big
  integer. Generating and verifying takes about 1 s for 1 million digits and 22 s for
  10 million, with a peak of about 310 MB of memory at 10 million (both measured). The
  practical ceiling of roughly 100 million is an extrapolation from that memory use, not a
  measurement. Beyond that, digits should come from a dedicated program such as y-cruncher
  and be streamed in: `write_dataset` accepts an iterator of blocks, and
  `iter_digits_from_text` streams a text file.
- **Array-based analyses** (n-grams, tests, windows, runs) load their range into memory and
  are capped by `PISCOPE_MAX_STATISTICS_DIGITS` (default 10 million). Frequency counting
  and search stream chunk by chunk and have no such ceiling.
- **Search is a linear scan**, about 0.6 ms per million digits: 6 ms for `314159` over
  10 million digits (measured). Extrapolated, not measured, a billion digits would take
  around half a second per uncached pattern; an index (suffix array or n-gram index) is the
  next step if that becomes too slow.

### Checked at 10 million digits

Chunk boundaries are unit-tested with small synthetic chunks, and
`engine/tests/test_real_chunks.py` (marked `slow`, about 5 s) repeats the checks on three
real one-million-digit chunks in every test run. They were also exercised once by hand on
a larger dataset: the 1 million digit dataset was expanded to 10 million (10 chunks; chunk 0 was
recognised by checksum and left untouched) and compared with a flat scan of the
concatenated chunk files. Ranges crossing real boundaries and 14 searches, including nine
sequences that straddle a boundary, matched exactly. Through the API on that dataset,
measured on an Apple M-series laptop: frequency 25 ms, the full test battery 62 ms, 5-gram
counts 79 ms, runs 289 ms, dashboard observations 429 ms.

### Expanding a dataset

Chudnovsky cannot resume from a previous run: the series is evaluated for a target
precision as a whole. Expansion therefore means computing the larger number from scratch
and then proving it agrees with what is stored:

1. Compute N new digits and verify them (see below).
2. For every stored complete chunk, compare the SHA-256 of the new prefix with the stored
   checksum, and the stored file with its own checksum. Any disagreement aborts.
3. Leave matching complete chunks untouched. Write new chunks to temp files and rename.
4. A previously partial last chunk is replaced only after the whole stream is accepted,
   so a failed expansion leaves the old dataset readable.
5. Save the manifest atomically, last.

`uv run piscope-digits generate --digits 10000000` on an existing 1 million digit dataset
does exactly this.

## Digit generation and verification

Generator: the Chudnovsky series evaluated by binary splitting with GMP integers
(`gmpy2`), about 14.18 digits per term. The computation is fixed-point integer arithmetic
with 64 guard digits and the result is truncated, never rounded. If the guard digits come
out all 0 or all 9, a rounding error could carry into the kept digits, so the result is
rejected instead of trusted.

Nothing is written until the digits pass:

1. **Gauss-Legendre (Brent-Salamin)**: a second, unrelated algorithm (arithmetic-geometric
   mean iteration), implemented independently, compared digit for digit over the full
   length.
2. **Published checksum**: the engine ships the SHA-256 of the first million digits derived
   from two published files (`digits/reference.py` records the sources). Every build that
   covers the first million is compared against it, including offline and CI builds.
3. **Reference file** (optional): `--reference-file` compares against any published digit
   file and records its SHA-256 in the manifest.

### Why not BBP

The Bailey-Borwein-Plouffe formula extracts digits of pi at an arbitrary position without
computing the preceding ones, but only in base 16 (or other powers of 2). No comparable
digit-extraction formula is known for base 10, and converting hexadecimal digits to
decimal requires all the preceding digits anyway, which removes the advantage. For a
contiguous block of decimal digits, Chudnovsky with binary splitting is asymptotically
and practically faster. BBP remains useful as a spot check of hexadecimal expansions and
could be added as a verifier of a binary computation; it is not a decimal generator.

## Search

`search_sequence` scans one chunk at a time. Each scan window is the chunk plus the next
`len(pattern) - 1` digits, and a match belongs to the chunk it starts in. A sequence that
straddles a boundary is therefore found exactly once. Matches are reported by the position
of their first digit; overlapping matches all count (`000` occurs twice in `0000`), which
is why the loop advances by one after each hit instead of using `bytes.count`.

Algorithm choice, measured on the first million digits (`engine/benchmarks/search_algorithms.py`,
Apple M-series, milliseconds, best of 3):

| Pattern | Matches | bytes.find | NumPy | regex | KMP (pure Python) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 7 | 99,800 | 5.73 | 1.77 | 10.58 | 27.91 |
| 14 | 9,875 | 1.68 | 1.31 | 5.70 | 27.54 |
| 999 | 1,003 | 0.90 | 0.52 | 5.51 | 28.64 |
| 1234 | 78 | 0.98 | 1.49 | 5.36 | 26.60 |
| 314159 | 1 | 0.62 | 0.48 | 5.23 | 26.95 |
| 14159265358979 | 1 | 0.46 | 1.34 | 5.31 | 26.48 |

Decision: `bytes.find` (CPython's C two-way search) for patterns of two or more digits,
and a NumPy equality scan for single digits, where the Python-level loop over about n/10
matches dominates. A pure-Python KMP is 30 to 50 times slower; a C implementation would
at best match `bytes.find`. Aho-Corasick solves a different problem (many patterns in one
pass) and for a single pattern reduces to KMP. It becomes the right tool if PiScope adds
multi-pattern search, and should be benchmarked then against repeated `bytes.find`.

The API keeps the positions of recent searches in a small LRU cache keyed by pattern,
range and the dataset's `updated_at`, so paging through results does not rescan. At most
5 million positions are kept per search; the total count is always exact and the response
says when positions were truncated.

## API

Versioned under `/api/v1`. OpenAPI at `/api/v1/openapi.json`, interactive docs at
`/api/v1/docs`.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness and dataset availability |
| GET | `/dataset/info` | Size, provenance, verification, limits |
| GET | `/digits` | One digit |
| GET | `/digits/range` | A run of digits |
| POST | `/search` | Sequence search with paging and gap statistics |
| GET | `/analysis/frequency` | Digit counts against a uniform model |
| GET | `/analysis/ngrams` | N-gram table, pair matrix, block test |
| POST | `/analysis/statistics` | Test battery with multiple-testing correction |
| POST | `/analysis/compare` | Pi against seeded simulated sequences |
| GET | `/analysis/windows` | Digit concentration by window |
| GET | `/analysis/runs` | Longest runs and run-length distribution |
| GET | `/analysis/observations` | Computed dashboard facts |
| GET, DELETE | `/experiments` | Experiment log |

Design points:

- Endpoints are synchronous functions. FastAPI runs them in a thread pool, which suits
  CPU-bound NumPy work that releases the GIL.
- A running thread cannot be cancelled, so there are no per-request timeouts. Cost is
  bounded up front instead: every expensive input (range size, pattern length, page size,
  lag, n, simulations, windows) has a limit in `Settings`, overridable through
  `PISCOPE_*` environment variables and reported by `/dataset/info`.
- Errors share one envelope: `{"error": {"code", "message", "details"}}`. A missing or
  corrupt dataset gives 503 with instructions; invalid input gives 422.
- Experiments (searches, test runs, comparisons) are appended to a JSON Lines file with
  the parameters needed to repeat them, including the seed, bit generator and NumPy
  version of every simulation. A file is enough; there is no database.

## Frontend

Next.js (App Router), TypeScript in strict mode, Tailwind CSS, shadcn/ui components and
Apache ECharts. Decisions worth knowing:

- **The browser calls the API directly.** There is no server-side data fetching and no
  proxy, so there is one API address (`NEXT_PUBLIC_API_URL`) instead of one for the
  browser and another for a server inside Docker. The cost is that the address is inlined
  at build time: changing it means rebuilding, and the API must allow the frontend's
  origin through CORS (`PISCOPE_CORS_ORIGINS`).
- **Pages render in the browser only.** Each route prerenders a skeleton and mounts its
  view after hydration (`components/shared/client-page.tsx`). Every view depends on the URL
  and on live API data, so a server render would have nothing to show, and waiting for
  hydration avoids markup mismatches when cached data arrives first.
- **Types come from the API.** `scripts/export_openapi.py` writes the OpenAPI schema and
  `openapi-typescript` turns it into `frontend/lib/api/schema.d.ts`. Both files are
  committed and CI fails if they drift from the Pydantic models.
- **State lives in the URL.** The analysis range, search pattern, result page and explorer
  position are query parameters, so any view can be bookmarked, shared and repeated.
  Experiments link back to the page with their recorded parameters, including the seed.
- **Limits come from the server.** Forms validate against the `limits` reported by
  `/dataset/info`, not constants copied into the frontend.
- **No mathematics in the frontend.** Counts, deviations, p-values and interpretations
  are displayed as the API returns them. The one exception is highlighting a sequence
  within the digits already on screen in the explorer, which is a plain substring search.
- **Tests run only when asked.** Frequency and n-gram views load with the page. The test
  battery and random comparison need a button press, because each run is logged and adds
  to the number of comparisons a user has made.
- **Charts say what they hide.** Count axes that do not start at zero are labelled as
  truncated, heatmaps use a fixed -3 to +3 scale so ordinary noise is not stretched, and
  each chart has an accessible description and a table or summary of the same numbers.

## Performance

`engine/benchmarks/analysis_operations.py` on the first million digits (Apple M-series,
best of 5):

| Operation | Time |
| --- | ---: |
| Generate and verify 1,000,000 digits | about 1 s |
| Open store and verify checksums | 0.4 ms |
| Search `314159` | 0.6 ms |
| Search `7` (99,800 matches) | 1.2 ms |
| Digit frequency | 1.3 ms |
| 5-gram counts | 3.6 ms |
| Full test battery, 20 lags | 4.9 ms |
| Longest runs | 18.9 ms |
| Compare with 20 simulations | 111 ms |
