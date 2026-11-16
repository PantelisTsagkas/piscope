# Test fixtures

These JSON files are responses recorded from the real PiScope API running against the
verified first million digits. They are not hand-written, so the unit tests exercise the
components against the exact shapes and values the server produces.

They are used only by the Vitest suite. The application itself never reads them.

To refresh them after an API change, start the API (`uv run piscope-api`) and run
`pnpm fixtures` from `frontend/`.
