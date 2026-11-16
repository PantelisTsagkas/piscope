# piscope-engine

**Status: ACTIVE**

The mathematics behind PiScope as a standalone Python package: chunked, memory-mapped
storage of the decimal digits of pi, Chudnovsky generation with independent verification,
sequence search, frequency and n-gram counts, statistical tests and pattern analysis.
It depends on NumPy and SciPy only and never imports a web framework.

```bash
uv run piscope-digits generate          # first million digits, verified
uv run piscope-digits info
```

```python
from pathlib import Path

from piscope_engine.digits.store import DigitStore
from piscope_engine.search.sequence import search_sequence

store = DigitStore(Path("data"))
print(search_sequence(store, "999999").first_position)  # 762
```

Position 1 is the first digit after the decimal point. Design and benchmarks are in
[docs/architecture.md](../docs/architecture.md).
