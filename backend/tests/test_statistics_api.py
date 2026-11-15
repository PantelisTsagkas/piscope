from collections import Counter

import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy import stats

from piscope_engine.statistics.simulation import random_digit_sequences

from api_support import text_to_digits


def test_statistics_default_battery(client: TestClient, pi_text: str) -> None:
    response = client.post("/api/v1/analysis/statistics", json={})
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["range_start"], body["range_end"], body["sample_size"]) == (1, 10_000, 10_000)
    keys = [result["key"] for result in body["results"]]
    assert keys == ["chi_square", "shannon_entropy", "autocorrelation", "runs", "ngram_blocks"]
    assert body["family_size"] == 4
    assert body["correction"] == "holm"

    counts = [Counter(pi_text)[str(d)] for d in range(10)]
    reference = stats.chisquare(counts)
    chi = body["results"][0]
    assert chi["statistic"] == pytest.approx(float(reference.statistic))
    assert chi["p_value"] == pytest.approx(float(reference.pvalue))
    assert chi["adjusted_p_value"] >= chi["p_value"]

    for result in body["results"]:
        for field in [
            "name",
            "statistic",
            "sample_size",
            "interpretation",
            "assumptions",
            "limitations",
        ]:
            assert result[field] not in (None, "", []), (result["key"], field)
    entropy = body["results"][1]
    assert entropy["p_value"] is None
    assert entropy["adjusted_p_value"] is None
    assert "normality of pi has not been proven" in body["scope_note"]
    assert "chance" in body["multiple_testing_note"]


def test_statistics_options(client: TestClient) -> None:
    body = client.post(
        "/api/v1/analysis/statistics",
        json={
            "start": 501,
            "count": 2_000,
            "tests": ["autocorrelation", "runs"],
            "max_lag": 5,
            "runs_dichotomy": "parity",
            "correction": "bonferroni",
        },
    ).json()
    assert (body["range_start"], body["range_end"]) == (501, 2_500)
    assert [r["key"] for r in body["results"]] == ["autocorrelation", "runs"]
    assert len(body["results"][0]["details"]["lags"]) == 5
    assert body["results"][1]["details"]["dichotomy"] == "parity"
    for result in body["results"]:
        assert result["adjusted_p_value"] == pytest.approx(min(1.0, result["p_value"] * 2))


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"tests": []}, "validation_error"),
        ({"tests": ["tarot"]}, "validation_error"),
        ({"max_lag": 0}, "validation_error"),
        ({"max_lag": 101}, "limit_exceeded"),
        ({"ngram_length": 7}, "limit_exceeded"),
        ({"start": 9_000, "count": 2_000}, "position_out_of_range"),
        ({"start": 1, "count": 10, "max_lag": 20}, "invalid_request"),
        ({"runs_dichotomy": "vibes"}, "validation_error"),
    ],
)
def test_statistics_invalid_requests(client: TestClient, body: dict, code: str) -> None:
    response = client.post("/api/v1/analysis/statistics", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == code


def test_ngrams_table(client: TestClient, pi_text: str) -> None:
    body = client.get("/api/v1/analysis/ngrams", params={"n": 2}).json()
    expected = Counter(pi_text[i : i + 2] for i in range(9_999))
    assert body["windows"] == 9_999
    assert body["possible"] == 100
    assert body["total_rows"] == 100
    assert len(body["rows"]) == 100
    assert {row["ngram"]: row["count"] for row in body["rows"]} == dict(expected)
    counts = [row["count"] for row in body["rows"]]
    assert counts == sorted(counts, reverse=True)
    assert body["matrix"][1][4] == expected["14"]
    assert body["most_common"][0]["count"] == max(expected.values())
    assert body["least_common"][0]["count"] == min(expected.values())
    assert body["block_test"]["key"] == "ngram_blocks"
    assert body["block_test"]["sample_size"] == 5_000
    assert "not independent" in body["note"]


def test_ngrams_paging_sorting_and_blocks(client: TestClient, pi_text: str) -> None:
    body = client.get(
        "/api/v1/analysis/ngrams",
        params={"n": 3, "sort": "ngram", "offset": 140, "limit": 3, "overlapping": "false"},
    ).json()
    blocks = Counter(pi_text[i : i + 3] for i in range(0, 9_999, 3))
    assert [row["ngram"] for row in body["rows"]] == ["140", "141", "142"]
    assert [row["count"] for row in body["rows"]] == [
        blocks.get(k, 0) for k in ["140", "141", "142"]
    ]
    assert body["windows"] == 3_333
    assert body["matrix"] is None
    assert body["has_more"] is True
    assert body["missing"] == 1_000 - len(blocks)
    assert "non-overlapping" in body["note"]


def test_ngram_limits(client: TestClient) -> None:
    assert client.get("/api/v1/analysis/ngrams", params={"n": 7}).json()["error"]["code"] == (
        "limit_exceeded"
    )
    assert client.get("/api/v1/analysis/ngrams", params={"n": 0}).status_code == 422
    assert (
        client.get("/api/v1/analysis/ngrams", params={"limit": 1_001}).json()["error"]["code"]
        == "limit_exceeded"
    )
    assert client.get("/api/v1/analysis/ngrams", params={"sort": "random"}).status_code == 422


def test_compare_is_reproducible_and_recorded(client: TestClient, pi_text: str) -> None:
    request = {"start": 1, "count": 3_000, "seed": 1234, "simulations": 6}
    first = client.post("/api/v1/analysis/compare", json=request).json()
    second = client.post("/api/v1/analysis/compare", json=request).json()
    assert first["statistics"] == second["statistics"]
    assert first["random_counts"] == second["random_counts"]
    assert first["source"]["seed"] == 1234
    assert first["source"]["bit_generator"] == "PCG64"
    assert first["source"]["numpy_version"] == np.__version__
    assert first["simulations"] == 6
    assert first["length"] == 3_000

    simulated = random_digit_sequences(3_000, seed=1234, count=6)
    assert first["random_counts"] == np.bincount(simulated[0], minlength=10).tolist()
    assert first["pi_counts"] == np.bincount(text_to_digits(pi_text[:3_000]), minlength=10).tolist()
    chi = first["statistics"][0]
    assert chi["key"] == "chi_square"
    assert len(chi["simulated"]) == 6
    assert chi["simulated"][0] == pytest.approx(first["random_results"][0]["statistic"])
    assert chi["observed"] == pytest.approx(first["pi_results"][0]["statistic"])
    assert 0.0 <= chi["fraction_at_or_below"] <= 1.0
    assert "not that pi is random" in first["note"]

    other = client.post("/api/v1/analysis/compare", json={**request, "seed": 1235}).json()
    assert other["random_counts"] != first["random_counts"]

    logged = client.get("/api/v1/experiments", params={"kind": "comparison"}).json()["experiments"]
    assert logged[0]["parameters"]["seed"] == 1235
    assert logged[0]["parameters"]["numpy_version"] == np.__version__


def test_compare_reports_the_seed_it_chose(client: TestClient) -> None:
    body = client.post("/api/v1/analysis/compare", json={"count": 1_000, "simulations": 2}).json()
    seed = body["source"]["seed"]
    assert isinstance(seed, int)
    repeat = client.post(
        "/api/v1/analysis/compare", json={"count": 1_000, "simulations": 2, "seed": seed}
    ).json()
    assert repeat["statistics"] == body["statistics"]


@pytest.mark.parametrize(
    ("body", "code"),
    [
        ({"count": 5}, "validation_error"),
        ({"simulations": 0}, "validation_error"),
        ({"seed": -1}, "validation_error"),
        ({"seed": 2**53}, "validation_error"),
        ({"simulations": 201, "count": 100}, "limit_exceeded"),
        ({"count": 20_000}, "position_out_of_range"),
    ],
)
def test_compare_invalid_requests(client: TestClient, body: dict, code: str) -> None:
    response = client.post("/api/v1/analysis/compare", json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == code


def test_windows(client: TestClient, pi_text: str) -> None:
    body = client.get("/api/v1/analysis/windows", params={"windows": 8}).json()
    assert body["window_size"] == 1_250
    assert body["window_count"] == 8
    assert body["cells"] == 80
    row = body["rows"][2]
    assert (row["start"], row["end"]) == (2_501, 3_750)
    window_counts = Counter(pi_text[2_500:3_750])
    assert row["counts"] == [window_counts[str(d)] for d in range(10)]
    assert row["standardized"][0] == pytest.approx((row["counts"][0] - 125) / (1_250 * 0.09) ** 0.5)
    assert body["expected_cells_beyond_two"] == pytest.approx(80 * 0.0455)
    assert body["approximation_reliable"] is True
    tiny = client.get("/api/v1/analysis/windows", params={"count": 400, "windows": 10}).json()
    assert tiny["window_size"] == 40
    assert tiny["approximation_reliable"] is False
    assert (
        client.get("/api/v1/analysis/windows", params={"windows": 201}).json()["error"]["code"]
        == "limit_exceeded"
    )


def test_runs(client: TestClient) -> None:
    body = client.get("/api/v1/analysis/runs", params={"top": 3}).json()
    assert body["longest"][0] == {"digit": 9, "length": 6, "position": 762}
    assert len(body["longest"]) == 3
    assert body["distribution"][0]["length"] == 1
    assert sum(r["observed"] * r["length"] for r in body["distribution"]) == 10_000
    offset = client.get(
        "/api/v1/analysis/runs", params={"start": 700, "count": 100, "top": 1}
    ).json()
    assert offset["longest"][0]["position"] == 762


def test_observations_are_computed_from_the_digits(client: TestClient, pi_text: str) -> None:
    body = client.get("/api/v1/analysis/observations").json()
    assert body["sample_size"] == 10_000
    by_key = {item["key"]: item for item in body["observations"]}
    assert by_key["longest_run"]["value"] == "999999"
    assert "762" in by_key["longest_run"]["detail"]
    assert (by_key["longest_run"]["position"], by_key["longest_run"]["length"]) == (762, 6)
    counts = [Counter(pi_text)[str(d)] for d in range(10)]
    p_value = float(stats.chisquare(counts).pvalue)
    assert by_key["chi_square"]["value"] == f"p = {p_value:.3f}"
    # Shortest length with a missing sequence, found by brute force on the fixture.
    length = 1
    while True:
        seen = {pi_text[i : i + length] for i in range(len(pi_text) - length + 1)}
        if len(seen) < 10**length:
            break
        length += 1
    expected_value = f"all {length - 1}-digit, {len(seen):,} of {10**length:,} {length}-digit"
    assert by_key["ngram_coverage"]["value"] == expected_value
    assert "not evidence of hidden structure" in body["caveat"]

    part = client.get("/api/v1/analysis/observations", params={"start": 1, "count": 500}).json()
    assert part["range_end"] == 500
    assert part["observations"] != body["observations"]


def test_in_memory_limit_is_enforced(settings, pi_text: str) -> None:
    from piscope_api.main import create_app

    small = settings.model_copy(update={"max_statistics_digits": 1_000})
    with TestClient(create_app(small)) as limited:
        response = limited.post("/api/v1/analysis/statistics", json={})
        assert response.json()["error"]["code"] == "limit_exceeded"
        assert limited.post("/api/v1/analysis/statistics", json={"count": 1_000}).status_code == 200
        observations = limited.get("/api/v1/analysis/observations").json()
        assert observations["sample_size"] == 1_000  # capped, and reported as such


def test_largest_accepted_seed_round_trips(client: TestClient) -> None:
    seed = 2**53 - 1
    body = client.post(
        "/api/v1/analysis/compare", json={"count": 500, "simulations": 1, "seed": seed}
    ).json()
    assert body["source"]["seed"] == seed


def test_response_model_bug_is_a_server_error(settings, monkeypatch: pytest.MonkeyPatch) -> None:
    from piscope_api.main import create_app
    from piscope_api.routers import dataset

    monkeypatch.setattr(dataset, "api_version", None)  # makes HealthResponse invalid
    with TestClient(create_app(settings), raise_server_exceptions=False) as broken:
        response = broken.get("/api/v1/health")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
