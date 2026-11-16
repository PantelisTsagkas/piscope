# PiScope frontend

**Status: ACTIVE**

Next.js (App Router) interface for the PiScope API. It displays what the API computes and
does no mathematics of its own.

```bash
pnpm install
pnpm dev          # http://localhost:3000, expects the API on http://localhost:8000
```

Set `NEXT_PUBLIC_API_URL` to use an API elsewhere (see `.env.example`).

```text
app/                 one folder per route; each page mounts a client view
components/layout/   shell, navigation, dataset status
components/charts/   ECharts wrapper and one file per chart
components/shared/   panels, form fields, loading, empty and error states
components/...       one folder per feature area
hooks/               URL state and the shared analysis range
lib/api/             typed client, query hooks, types generated from the OpenAPI schema
tests/unit/          Vitest, against responses recorded from the real API
tests/e2e/           Playwright, against the running application
```

Setup, commands and testing are documented in
[docs/development.md](../docs/development.md); design decisions are in
[docs/architecture.md](../docs/architecture.md#frontend).
