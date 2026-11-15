from collections import Counter

import pytest
from fastapi.testclient import TestClient


def test_frequency_of_whole_dataset(client: TestClient, pi_text: str) -> None:
    body = client.get("/api/v1/analysis/frequency").json()
    counts = Counter(pi_text)
    assert [entry["count"] for entry in body["digits"]] == [counts[str(d)] for d in range(10)]
    assert (body["range_start"], body["range_end"], body["sample_size"]) == (1, 10_000, 10_000)
    assert body["expected_relative_frequency"] == 0.1
    for entry in body["digits"]:
        assert entry["expected_count"] == pytest.approx(1_000)
        assert entry["deviation"] == pytest.approx(entry["count"] - 1_000)
        assert entry["relative_frequency"] == pytest.approx(entry["count"] / 10_000)
    highest = max(counts.values())
    assert body["most_frequent"] == [d for d in range(10) if counts[str(d)] == highest]


def test_frequency_of_sub_range(client: TestClient, pi_text: str) -> None:
    body = client.get("/api/v1/analysis/frequency", params={"start": 901, "count": 250}).json()
    counts = Counter(pi_text[900:1_150])
    assert [entry["count"] for entry in body["digits"]] == [
        counts.get(str(d), 0) for d in range(10)
    ]
    assert (body["range_start"], body["range_end"]) == (901, 1_150)


def test_frequency_errors(client: TestClient) -> None:
    response = client.get("/api/v1/analysis/frequency", params={"start": 9_000, "count": 5_000})
    assert response.json()["error"]["code"] == "position_out_of_range"
    response = client.get("/api/v1/analysis/frequency", params={"count": 0})
    assert response.json()["error"]["code"] == "validation_error"
    response = client.get("/api/v1/analysis/frequency", params={"start": 10_001})
    assert response.status_code == 422
