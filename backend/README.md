# piscope-api

**Status: ACTIVE**

FastAPI service that exposes [piscope-engine](../engine/README.md) under `/api/v1`:
Pydantic schemas, request limits, a small search cache and the experiment log. No
mathematics lives here.

```bash
uv run piscope-api                      # http://localhost:8000, docs at /api/v1/docs
```

Configuration (`PISCOPE_*` variables) and commands are in
[docs/development.md](../docs/development.md).
