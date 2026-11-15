"""Small LRU cache of search results so that paging does not rescan the dataset."""

import threading
from collections import OrderedDict

from piscope_engine.digits.store import DigitStore
from piscope_engine.search.sequence import SearchResult, search_sequence

type CacheKey = tuple[str, int, int, str]


class SearchCache:
    """Runs searches through the engine and remembers the most recent results.

    Entries are keyed by pattern, range and the dataset's ``updated_at`` stamp, so an
    expanded dataset never serves stale results.
    """

    def __init__(self, max_entries: int, max_stored_positions: int) -> None:
        """Create a cache holding at most ``max_entries`` results (0 disables caching)."""
        self._max_entries = max_entries
        self._max_stored_positions = max_stored_positions
        self._entries: OrderedDict[CacheKey, SearchResult] = OrderedDict()
        self._lock = threading.Lock()

    def search(
        self, store: DigitStore, pattern: str, start: int, end: int
    ) -> tuple[SearchResult, bool]:
        """Return ``(result, was_cached)`` for a search."""
        key: CacheKey = (pattern, start, end, store.manifest.updated_at)
        with self._lock:
            cached = self._entries.get(key)
            if cached is not None:
                self._entries.move_to_end(key)
                return cached, True
        result = search_sequence(
            store, pattern, start=start, end=end, max_stored_positions=self._max_stored_positions
        )
        if self._max_entries > 0:
            with self._lock:
                self._entries[key] = result
                self._entries.move_to_end(key)
                while len(self._entries) > self._max_entries:
                    self._entries.popitem(last=False)
        return result, False
