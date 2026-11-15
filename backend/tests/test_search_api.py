import itertools

import pytest
from fastapi.testclient import TestClient

from api_support import naive_positions


def search(client: TestClient, **body: object) -> dict:
    response = client.post("/api/v1/search", json=body)
    assert response.status_code == 200, response.text
    return response.json()


def test_first_digits_are_found_at_position_one(client: TestClient) -> None:
    body = search(client, pattern="14159")
    assert body["first_position"] == 1
    assert body["matches"][0] == {"index": 0, "position": 1, "gap_from_previous": None}


@pytest.mark.parametrize("pattern", ["999999", "2718", "123", "00", "7", "8979323846"])
def test_results_match_naive_scan(client: TestClient, pi_text: str, pattern: str) -> None:
    expected = naive_positions(pi_text, pattern)
    body = search(client, pattern=pattern, limit=50)
    assert body["total_count"] == len(expected)
    assert body["first_position"] == (expected[0] if expected else None)
    assert body["last_position"] == (expected[-1] if expected else None)
    assert [match["position"] for match in body["matches"]] == expected[:50]
    assert body["pattern_length"] == len(pattern)
    assert body["expected_count"] == pytest.approx((10_000 - len(pattern) + 1) / 10 ** len(pattern))
    assert body["elapsed_ms"] >= 0


def test_absent_pattern(client: TestClient, pi_text: str) -> None:
    assert naive_positions(pi_text, "1234567") == []
    body = search(client, pattern="1234567")
    assert body["total_count"] == 0
    assert body["first_position"] is None
    assert body["matches"] == []
    assert body["gaps"] is None
    assert body["has_more"] is False


def test_pagination_walks_every_match_once(client: TestClient, pi_text: str) -> None:
    expected = naive_positions(pi_text, "12")
    collected: list[int] = []
    offset = 0
    while True:
        body = search(client, pattern="12", offset=offset, limit=7)
        collected.extend(match["position"] for match in body["matches"])
        assert [match["index"] for match in body["matches"]] == list(
            range(offset, offset + len(body["matches"]))
        )
        if not body["has_more"]:
            break
        offset += 7
    assert collected == expected
    beyond = search(client, pattern="12", offset=len(expected) + 5, limit=7)
    assert beyond["matches"] == []
    assert beyond["total_count"] == len(expected)


def test_gaps(client: TestClient, pi_text: str) -> None:
    expected = naive_positions(pi_text, "33")
    gaps = [later - earlier for earlier, later in itertools.pairwise(expected)]
    body = search(client, pattern="33", offset=3, limit=5)
    assert [match["gap_from_previous"] for match in body["matches"]] == gaps[2:7]
    assert body["gaps"]["count"] == len(gaps)
    assert body["gaps"]["minimum"] == min(gaps)
    assert body["gaps"]["maximum"] == max(gaps)
    assert body["gaps"]["mean"] == pytest.approx(sum(gaps) / len(gaps))
    assert body["gaps"]["expected_mean"] == 100


def test_search_within_range(client: TestClient, pi_text: str) -> None:
    body = search(client, pattern="5", start=995, end=1_010)
    assert [m["position"] for m in body["matches"]] == naive_positions(pi_text, "5", 995, 1_010)
    assert (body["range_start"], body["range_end"]) == (995, 1_010)


def test_second_request_is_served_from_cache(client: TestClient) -> None:
    assert search(client, pattern="4242")["cached"] is False
    assert search(client, pattern="4242", offset=1)["cached"] is True


@pytest.mark.parametrize(
    "body",
    [
        {"pattern": ""},
        {"pattern": "12a"},
        {"pattern": "3.14"},
        {"pattern": " 1"},
        {"pattern": "12", "offset": -1},
        {"pattern": "12", "limit": 0},
        {"pattern": "12", "start": 0},
        {"pattern": "12", "unknown": 1},
        {},
    ],
)
def test_invalid_requests(client: TestClient, body: dict) -> None:
    response = client.post("/api/v1/search", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_limits_are_enforced(client: TestClient) -> None:
    too_many = client.post("/api/v1/search", json={"pattern": "1", "limit": 51})
    assert too_many.json()["error"]["code"] == "limit_exceeded"
    too_long = client.post("/api/v1/search", json={"pattern": "1" * 1_001})
    assert too_long.json()["error"]["code"] == "limit_exceeded"
    bad_range = client.post("/api/v1/search", json={"pattern": "1", "start": 50, "end": 20})
    assert bad_range.json()["error"]["code"] == "position_out_of_range"
    outside = client.post("/api/v1/search", json={"pattern": "1", "end": 10_001})
    assert outside.json()["error"]["code"] == "position_out_of_range"


def test_searches_are_logged_as_experiments(client: TestClient) -> None:
    assert client.get("/api/v1/experiments").json() == {"experiments": []}
    search(client, pattern="999999")
    search(client, pattern="999999", offset=0)  # cached repeat is not logged twice
    search(client, pattern="2718")
    experiments = client.get("/api/v1/experiments").json()["experiments"]
    assert [item["parameters"]["pattern"] for item in experiments] == ["2718", "999999"]
    assert experiments[1]["kind"] == "search"
    assert experiments[1]["summary"]["first_position"] == 762
    assert (
        client.get("/api/v1/experiments", params={"limit": 1}).json()["experiments"][0][
            "parameters"
        ]["pattern"]
        == "2718"
    )
    assert client.delete("/api/v1/experiments").status_code == 204
    assert client.get("/api/v1/experiments").json() == {"experiments": []}
