# Development

## Requirements

- [uv](https://docs.astral.sh/uv/) 0.11 or newer. It installs Python 3.12 itself.
- Node 22 and pnpm 11 for the frontend.
- Docker, only if you want to run the Compose setup.

## First run

```bash
git clone <repository-url> piscope && cd piscope

uv sync --all-packages --all-extras     # engine, API, dev tools, gmpy2 for generation
uv run piscope-digits generate          # writes data/ (about 1 second)
uv run piscope-api                      # http://localhost:8000

cd frontend
pnpm install
pnpm dev                                # http://localhost:3000
```

`data/` is not committed. Until digits are generated the API still starts, reports
`dataset_available: false` at `/api/v1/health` and answers data requests with 503; the
interface shows how to fix it.

## Commands

From the repository root:

| Command | Purpose |
| --- | --- |
| `uv run pytest` | Engine and API tests |
| `uv run pytest -m "not slow"` | Skip tests that generate large digit counts |
| `uv run ruff check . && uv run ruff format --check .` | Lint and formatting |
| `uv run ty check` | Type checking |
| `uv run piscope-digits info` | Summary of the stored dataset |
| `uv run piscope-digits verify` | Recompute and check every chunk checksum |
| `uv run python engine/benchmarks/search_algorithms.py` | Search algorithm benchmark |
| `uv run python engine/benchmarks/analysis_operations.py` | Benchmark of the main operations |
| `uv run python scripts/export_openapi.py` | Write the OpenAPI schema for the frontend |

From `frontend/`:

| Command | Purpose |
| --- | --- |
| `pnpm dev` | Development server |
| `pnpm build` then `pnpm start:standalone` | Production build and server |
| `pnpm lint`, `pnpm typecheck`, `pnpm format:check` | Static checks |
| `pnpm test` | Vitest unit and component tests |
| `pnpm test:e2e` | Playwright tests (see below) |
| `pnpm api:types` | Regenerate `lib/api/schema.d.ts` from `lib/api/openapi.json` |
| `pnpm fixtures` | Re-record the unit test fixtures from a running API |

## Changing the API

The frontend's types are generated from the API schema, and CI fails if they are stale.
After changing a Pydantic model or an endpoint:

```bash
uv run python scripts/export_openapi.py
cd frontend && pnpm api:types
```

Commit both generated files. If response shapes changed, also run `pnpm fixtures` with the
API running so the unit tests use real responses.

## Tests

**Python.** Reference values are never typed from memory. Digits are checked against a
published file (`engine/tests/fixtures/README.md` records the source and checksum), and
statistics are checked against SciPy or values derived by hand in the test.

**Frontend unit tests** mock `fetch` with responses recorded from the real API
(`frontend/tests/fixtures/`). Charts are replaced by a labelled placeholder because jsdom
has no canvas.

**End-to-end tests** start the real API on port 8100 against `data/` and a production
build of the frontend on port 3100, so they do not collide with a running development
setup. Expected search positions and digit counts are computed in the test from the
published digit file, not hard-coded. The experiment log is redirected to a temporary
file, so running them never touches your own log. They need the dataset to exist:

```bash
uv run piscope-digits generate
cd frontend
pnpm exec playwright install chromium   # once
pnpm test:e2e
```

## Configuration

The API reads `PISCOPE_*` environment variables, or a `.env` file in the directory it is
started from. The ones you are most likely to need:

| Variable | Default | Meaning |
| --- | --- | --- |
| `PISCOPE_DATA_DIR` | `data` | Dataset directory |
| `PISCOPE_EXPERIMENTS_FILE` | `<data dir>/experiments.jsonl` | Experiment log |
| `PISCOPE_CORS_ORIGINS` | `["http://localhost:3000", "http://127.0.0.1:3000"]` | Browser origins allowed to call the API, as a JSON list |
| `PISCOPE_VERIFY_CHECKSUMS_ON_STARTUP` | `true` | Recompute chunk checksums at startup |
| `PISCOPE_MAX_STATISTICS_DIGITS` | `10000000` | Digits per in-memory analysis |

Every request limit is a setting; `backend/src/piscope_api/settings.py` lists them all and
`/api/v1/dataset/info` reports the values in force.

The frontend has one setting, `NEXT_PUBLIC_API_URL` (default `http://localhost:8000`):
the address the browser uses to reach the API. It is inlined at build time, so set it
before `pnpm build` and rebuild to change it. See `frontend/.env.example`.

## Docker

```bash
docker compose up --build        # interface on :3000, API on :8000
docker compose down              # stop; the digits stay in the piscope-data volume
docker compose down -v           # stop and delete the digits
```

`API_PORT`, `WEB_PORT` and `PISCOPE_DIGITS` can be set in the environment, for example
`API_PORT=8200 WEB_PORT=3200 docker compose up --build`. The frontend image is built with
the API address the browser will use, so changing `API_PORT` needs `--build`.

## Hosted deployment

The project is archived and the public copy is no longer running: the Modal app is stopped
and the Vercel project is paused. When it ran, the frontend on Vercel called the API on
Modal. Both were deployed by hand from a checkout, and the commands below still work to
bring it back.

```bash
uv run modal deploy deploy/modal_app.py      # API; prints its URL
cd frontend && vercel deploy --prod          # interface
```

- `deploy/modal_app.py` builds an image from `uv.lock`, generates and verifies the first
  million digits at build time, and serves the API from at most one container that scales
  to zero after five minutes idle. The first request after that takes about five seconds.
- The Vercel project has one production variable, `NEXT_PUBLIC_API_URL`, set to the Modal
  URL. `WEB_ORIGINS` in `deploy/modal_app.py` must list the interface's origin, or the
  browser will refuse the API's responses.
- Request limits are lower than the local defaults (`PUBLIC_LIMITS` in the same file),
  because the URL is open to anyone.
- The experiment log is on the container's own disk. Every visitor shares it, any visitor
  can clear it, and it is emptied whenever the container stops.

To take it down: `uv run modal app stop piscope-api` and `vercel project rm piscope`.

## Larger datasets

```bash
uv run piscope-digits generate --digits 10000000
```

This recomputes pi to the new length, checks that the result agrees with every chunk
already stored, and writes only the new chunks. Ten million digits take about 22 seconds
and 310 MB of memory. To compare against a published file as well, add
`--reference-file path/to/digits.txt --reference-source <url>`.

Restart the API afterwards; it reads the manifest at startup. `docs/architecture.md`
describes what does and does not scale beyond that.

## Conventions

- Position 1 is the first digit after the decimal point, in every public function, API
  field and label.
- The engine does not import FastAPI or Pydantic. A lint rule and a test enforce it.
- Commits follow Conventional Commits.
