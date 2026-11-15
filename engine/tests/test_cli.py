from pathlib import Path

import pytest

from piscope_engine.cli import main
from piscope_engine.digits.store import DigitStore


def test_generate_verify_info(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    data_dir = str(tmp_path / "data")
    assert (
        main(["--data-dir", data_dir, "generate", "--digits", "1500", "--chunk-size", "1000"]) == 0
    )
    assert DigitStore(Path(data_dir)).total_digits == 1_500
    assert main(["--data-dir", data_dir, "verify"]) == 0
    with caplog.at_level("INFO"):
        assert main(["--data-dir", data_dir, "info"]) == 0
    assert "14159265358979323846" in caplog.text


def test_errors_return_nonzero(tmp_path: Path) -> None:
    assert main(["--data-dir", str(tmp_path), "verify"]) == 1
    assert main(["--data-dir", str(tmp_path), "generate", "--digits", "0"]) == 1
