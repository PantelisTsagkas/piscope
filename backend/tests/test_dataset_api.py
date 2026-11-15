from pathlib import Path

from fastapi.testclient import TestClient

from piscope_api.main import create_app
from piscope_api.settings import Settings


def test_health(client: TestClient) -> None:
    body = client.get("/api/v1/health").json()
    assert body["status"] == "ok"
    assert body["dataset_available"] is True
    assert body["dataset_error"] is None


def test_dataset_info(client: TestClient) -> None:
    body = client.get("/api/v1/dataset/info").json()
    assert body["total_digits"] == 10_000
    assert (body["first_position"], body["last_position"]) == (1, 10_000)
    assert body["chunk_size"] == 1_000
    assert body["chunk_count"] == 10
    assert body["has_partial_chunk"] is False
    assert body["integer_part"] == "3"
    assert body["checksums_verified_at_startup"] is True
    assert "position 1 is the first digit after the decimal point" in body["indexing"]
    assert body["chunks"][3]["first_position"] == 3_001
    assert len(body["chunks"][0]["sha256"]) == 64
    assert body["limits"]["max_range_digits"] == 2_000
    assert body["verifications"][0]["method"] == "fixture"


def test_single_digit(client: TestClient, pi_text: str) -> None:
    assert client.get("/api/v1/digits", params={"position": 1}).json() == {
        "position": 1,
        "digit": 1,
    }
    for position in [2, 1_000, 1_001, 10_000]:
        body = client.get("/api/v1/digits", params={"position": position}).json()
        assert body["digit"] == int(pi_text[position - 1])


def test_digit_range_across_chunks(client: TestClient, pi_text: str) -> None:
    body = client.get("/api/v1/digits/range", params={"start": 990, "count": 1_500}).json()
    assert body["digits"] == pi_text[989:2_489]
    assert (body["start"], body["end"], body["count"]) == (990, 2_489, 1_500)
    assert body["has_previous"] is True
    assert body["has_next"] is True
    assert body["total_digits"] == 10_000


def test_digit_range_defaults_and_edges(client: TestClient, pi_text: str) -> None:
    first = client.get("/api/v1/digits/range").json()
    assert first["digits"] == pi_text[:1_000]
    assert first["digits"].startswith("1415926535")
    assert first["has_previous"] is False
    last = client.get("/api/v1/digits/range", params={"start": 9_991, "count": 10}).json()
    assert last["digits"] == pi_text[-10:]
    assert last["has_next"] is False


def test_out_of_range_requests(client: TestClient) -> None:
    for params in [{"start": 9_995, "count": 10}, {"start": 10_001, "count": 1}]:
        response = client.get("/api/v1/digits/range", params=params)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "position_out_of_range"
    response = client.get("/api/v1/digits", params={"position": 10_001})
    assert response.json()["error"]["code"] == "position_out_of_range"


def test_validation_errors_use_error_envelope(client: TestClient) -> None:
    for url, params in [
        ("/api/v1/digits", {"position": 0}),
        ("/api/v1/digits", {"position": "abc"}),
        ("/api/v1/digits", {}),
        ("/api/v1/digits/range", {"start": -3}),
        ("/api/v1/digits/range", {"count": 0}),
    ]:
        response = client.get(url, params=params)
        assert response.status_code == 422, (url, params)
        error = response.json()["error"]
        assert error["code"] == "validation_error"
        assert error["details"]


def test_range_limit_is_enforced(client: TestClient) -> None:
    response = client.get("/api/v1/digits/range", params={"start": 1, "count": 2_001})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "limit_exceeded"


def test_missing_dataset_gives_503(tmp_path: Path) -> None:
    app = create_app(Settings(data_dir=tmp_path / "nothing", _env_file=None))
    with TestClient(app) as client:
        health = client.get("/api/v1/health").json()
        assert health["status"] == "degraded"
        assert health["dataset_available"] is False
        for url in [
            "/api/v1/dataset/info",
            "/api/v1/digits?position=1",
            "/api/v1/analysis/frequency",
        ]:
            response = client.get(url)
            assert response.status_code == 503
            assert response.json()["error"]["code"] == "dataset_unavailable"
            assert "piscope-digits generate" in response.json()["error"]["message"]


def test_corrupt_dataset_is_not_served(settings: Settings) -> None:
    chunk = settings.data_dir / "chunk-000002.bin"
    content = bytearray(chunk.read_bytes())
    content[5] = (content[5] + 1) % 10
    chunk.write_bytes(bytes(content))
    with TestClient(create_app(settings)) as client:
        assert client.get("/api/v1/health").json()["dataset_available"] is False
        response = client.get("/api/v1/digits", params={"position": 1})
        assert response.status_code == 503
        assert "checksum mismatch" in response.json()["error"]["message"]


def test_openapi_is_exposed(client: TestClient) -> None:
    schema = client.get("/api/v1/openapi.json").json()
    for path in [
        "/api/v1/health",
        "/api/v1/dataset/info",
        "/api/v1/digits/range",
        "/api/v1/search",
    ]:
        assert path in schema["paths"]
    assert client.get("/api/v1/docs").status_code == 200
