"""
Tests for the esgvoc_min_version enforcement: esgvoc.core.db_compat and the API.

The CLI commands are covered in test_min_version_cli.py.
"""
from __future__ import annotations

import logging
import os
import sqlite3
from pathlib import Path

import pytest

import esgvoc
from esgvoc.api import projects
from esgvoc.core.db_compat import check_db_compatibility, get_min_version, incompatibility_message
from esgvoc.core.exceptions import EsgvocException, EsgvocIncompatibleDBError
from esgvoc.core.service.user_state import UserState

from .conftest import make_db

INSTALLED = "6.2.0"


@pytest.fixture(autouse=True)
def installed_esgvoc(monkeypatch):
    monkeypatch.setattr(esgvoc, "__version__", INSTALLED)


def _install(project_id: str, version: str, min_version: str | None, activate: bool = True) -> Path:
    db_path = make_db(UserState.db_path(project_id, version), project_id, version, min_version)
    if activate:
        # Bypasses the checks, e.g. activated by an older esgvoc that did not enforce min_version.
        UserState.load().set_active(project_id, version, source="local")
    return db_path


class TestGetMinVersion:
    def test_reads_embedded_value(self, tmp_path):
        assert get_min_version(make_db(tmp_path / "p.db", min_version="6.2.0")) == "6.2.0"

    def test_missing_key(self, tmp_path):
        assert get_min_version(make_db(tmp_path / "p.db")) is None

    def test_missing_metadata_table(self, tmp_path):
        db_path = tmp_path / "old.db"
        sqlite3.connect(str(db_path)).close()
        assert get_min_version(db_path) is None

    def test_not_a_database(self, tmp_path):
        db_path = tmp_path / "garbage.db"
        db_path.write_bytes(b"this is not a sqlite file" * 100)
        assert get_min_version(db_path) is None

    def test_replaced_file_is_read_again(self, tmp_path):
        db_path = make_db(tmp_path / "p.db", min_version="6.2.0")
        assert get_min_version(db_path) == "6.2.0"
        conn = sqlite3.connect(str(db_path))
        conn.execute("UPDATE _esgvoc_metadata SET value='7.0.0' WHERE key='esgvoc_min_version'")
        conn.commit()
        conn.close()
        stat = db_path.stat()
        os.utime(db_path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
        assert get_min_version(db_path) == "7.0.0"

    def test_opens_read_only(self, tmp_path):
        db_path = make_db(tmp_path / "p.db", min_version="6.2.0")
        content = db_path.read_bytes()
        get_min_version(db_path)
        assert db_path.read_bytes() == content


class TestIncompatibilityMessage:
    @pytest.mark.parametrize(
        "min_version",
        [
            "6.2.0",  # equal
            "6.1.9",  # older patch
            "6.1.99",  # older minor, big patch
            "5.9.0",  # older major
            "v4.1.0",  # v prefix
            "6.2.0rc1",  # pre-release of the installed version
        ],
    )
    def test_compatible(self, min_version):
        assert incompatibility_message("cmip7", "2.4.0", min_version) is None

    @pytest.mark.parametrize("min_version", ["6.2.1", "6.3.0", "6.10.0", "7.0.0", "v7.0.0", "10.0.0"])
    def test_incompatible(self, min_version):
        assert incompatibility_message("cmip7", "2.4.0", min_version) is not None

    @pytest.mark.parametrize("min_version", [None, "", "not-a-version", "6.2", "latest"])
    def test_unknown_requirement_is_allowed(self, min_version):
        assert incompatibility_message("cmip7", "2.4.0", min_version) is None

    @pytest.mark.parametrize("installed", ["unknown", "", "dev"])
    def test_unknown_installed_version_is_allowed(self, monkeypatch, installed):
        monkeypatch.setattr(esgvoc, "__version__", installed)
        assert incompatibility_message("cmip7", "2.4.0", "99.0.0") is None

    def test_installed_pre_release_is_older_than_release(self, monkeypatch):
        monkeypatch.setattr(esgvoc, "__version__", "6.2.0rc1")
        assert incompatibility_message("cmip7", "2.4.0", "6.2.0") is not None

    def test_message_content(self):
        message = incompatibility_message("cmip7", "2.4.0", "7.0.0")
        assert "cmip7@2.4.0 requires esgvoc >= 7.0.0" in message
        assert f"esgvoc {INSTALLED} is installed" in message
        assert "upgrade esgvoc to 7.0.0 or later" in message
        assert 'pip install --upgrade "esgvoc>=7.0.0"' in message
        assert "esgvoc list cmip7 --available" in message

    def test_message_names_the_project_and_version(self):
        message = incompatibility_message("cordex-cmip6", "dev-latest", "7.0.0")
        assert "cordex-cmip6@dev-latest" in message
        assert "esgvoc list cordex-cmip6 --available" in message


class TestCheckDbCompatibility:
    def test_raises_on_incompatible(self, tmp_path):
        with pytest.raises(EsgvocIncompatibleDBError, match="requires esgvoc >= 7.0.0"):
            check_db_compatibility("cmip7", "2.4.0", make_db(tmp_path / "p.db", min_version="7.0.0"))

    @pytest.mark.parametrize("min_version", ["6.2.0", "1.0.0", None])
    def test_passes_on_compatible(self, tmp_path, min_version):
        check_db_compatibility("cmip7", "2.4.0", make_db(tmp_path / "p.db", min_version=min_version))

    def test_error_is_an_esgvoc_exception(self):
        assert issubclass(EsgvocIncompatibleDBError, EsgvocException)


class TestProjectConnection:
    def test_active_incompatible_raises(self):
        _install("cmip7", "future", "7.0.0")
        with pytest.raises(EsgvocIncompatibleDBError, match="cmip7@future requires esgvoc >= 7.0.0"):
            projects._resolve_project_connection("cmip7")

    def test_explicit_version_incompatible_raises(self):
        _install("cmip7", "future", "7.0.0", activate=False)
        with pytest.raises(EsgvocIncompatibleDBError):
            projects._resolve_project_connection("cmip7", "future")

    def test_explicit_compatible_version_despite_incompatible_active(self):
        _install("cmip7", "current", "6.2.0", activate=False)
        _install("cmip7", "future", "7.0.0")
        assert projects._resolve_project_connection("cmip7", "current") is not None

    @pytest.mark.parametrize("min_version", ["6.2.0", "6.0.0", None])
    def test_compatible_opens(self, min_version):
        _install("cmip7", "current", min_version)
        assert projects._resolve_project_connection("cmip7") is not None

    def test_not_installed_returns_none(self):
        assert projects._resolve_project_connection("cmip7") is None
        assert projects._resolve_project_connection("cmip7", "missing") is None

    def test_session_helper_raises_incompatible_not_not_found(self):
        _install("cmip7", "future", "7.0.0")
        with pytest.raises(EsgvocIncompatibleDBError):
            projects._get_project_session_with_exception("cmip7")


class TestPublicApi:
    def test_get_project_raises(self):
        _install("cmip7", "future", "7.0.0")
        with pytest.raises(EsgvocIncompatibleDBError, match="pip install --upgrade"):
            projects.get_project("cmip7")

    def test_get_project_of_unknown_project_still_none(self):
        assert projects.get_project("cmip7") is None

    def test_all_projects_skips_incompatible(self):
        _install("cmip7", "future", "7.0.0")
        _install("cmip6", "current", "6.2.0")
        _install("obs4ref", "old", None)
        assert sorted(projects.get_all_projects()) == ["cmip6", "obs4ref"]

    def test_all_projects_logs_the_skipped_project(self, caplog):
        _install("cmip7", "future", "7.0.0")
        # The esgvoc logger does not propagate to the root logger that caplog listens to.
        esgvoc_logger = logging.getLogger("esgvoc")
        esgvoc_logger.addHandler(caplog.handler)
        try:
            assert projects.get_all_projects() == []
        finally:
            esgvoc_logger.removeHandler(caplog.handler)
        assert "Project 'cmip7' is ignored" in caplog.text
        assert "requires esgvoc >= 7.0.0" in caplog.text

    def test_all_projects_excludes_universe(self):
        _install("universe", "current", "6.2.0")
        _install("cmip6", "current", "6.2.0")
        assert projects.get_all_projects() == ["cmip6"]


class TestInternalActivationNotBlocked:
    def test_set_active_does_not_check(self):
        # cv_tester and validator use set_active to restore the previous active version,
        # which must work even if that version is not compatible.
        _install("cmip7", "future", "7.0.0", activate=False)
        UserState.load().set_active("cmip7", "future", source="local")
        assert UserState.load().get_active("cmip7") == "future"
