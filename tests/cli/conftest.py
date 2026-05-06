"""Fixtures for CLI tests — isolated ESGVOC_HOME per test."""
import pytest
from typer.testing import CliRunner

runner = CliRunner()


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    monkeypatch.setenv("ESGVOC_HOME", str(tmp_path))
    monkeypatch.delenv("ESGVOC_OFFLINE", raising=False)
    monkeypatch.delenv("ESGVOC_DB_DIR", raising=False)
    yield tmp_path
