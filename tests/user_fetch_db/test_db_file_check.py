"""
Tests for the rejection of database files that are not esgvoc databases (empty, not SQLite,
or without terms table): esgvoc.core.db_compat, the API and the CLI.

Without this check such a file is opened silently and only fails on the first query, with
"no such table".
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest
from typer.testing import CliRunner

from esgvoc.admin.cli import app as admin_app
from esgvoc.api import projects
from esgvoc.api.search import get_universe_session
from esgvoc.cli.use import app as use_app
from esgvoc.core.db_compat import check_db_file, db_file_problem_message
from esgvoc.core.exceptions import EsgvocDbError
from esgvoc.core.service.user_state import UserState

from .conftest import make_db

runner = CliRunner()


def _empty(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")
    return path


def _not_sqlite(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"this is not a sqlite file" * 100)
    return path


def _sqlite_without_terms(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute("CREATE TABLE other (x INTEGER)")
    conn.commit()
    conn.close()
    return path


class TestDbFileProblemMessage:
    def test_valid_project_db(self, tmp_path):
        assert db_file_problem_message("cmip6", "2.1.0", make_db(tmp_path / "p.db", "cmip6")) is None

    def test_valid_universe_db(self, tmp_path):
        assert db_file_problem_message("universe", "3.2.5", make_db(tmp_path / "u.db", "universe")) is None

    def test_empty_file(self, tmp_path):
        message = db_file_problem_message("universe", "3.2.5", _empty(tmp_path / "u.db"))
        assert "universe@3.2.5 is not a valid esgvoc database: the file is empty" in message
        assert "esgvoc use universe@3.2.5" in message
        assert str(tmp_path / "u.db") in message

    def test_not_sqlite(self, tmp_path):
        message = db_file_problem_message("cmip6", "2.1.0", _not_sqlite(tmp_path / "p.db"))
        assert "not a valid SQLite database" in message

    def test_sqlite_without_terms_table(self, tmp_path):
        message = db_file_problem_message("cmip6", "2.1.0", _sqlite_without_terms(tmp_path / "p.db"))
        assert "it has no 'pterms' table" in message

    def test_project_db_used_as_universe(self, tmp_path):
        message = db_file_problem_message("universe", "x", make_db(tmp_path / "p.db", "cmip6"))
        assert "it has no 'uterms' table" in message

    def test_replaced_file_is_checked_again(self, tmp_path):
        db_path = _empty(tmp_path / "p.db")
        assert db_file_problem_message("cmip6", "x", db_path) is not None
        db_path.unlink()
        make_db(db_path, "cmip6")
        stat = db_path.stat()
        os.utime(db_path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
        assert db_file_problem_message("cmip6", "x", db_path) is None

    def test_opens_read_only(self, tmp_path):
        db_path = make_db(tmp_path / "p.db", "cmip6")
        content = db_path.read_bytes()
        db_file_problem_message("cmip6", "x", db_path)
        assert db_path.read_bytes() == content

    def test_check_raises_esgvoc_db_error(self, tmp_path):
        with pytest.raises(EsgvocDbError, match="the file is empty"):
            check_db_file("cmip6", "2.1.0", _empty(tmp_path / "p.db"))


class TestApi:
    def test_active_empty_project_db_raises(self):
        _empty(UserState.db_path("cmip6", "broken"))
        UserState.load().set_active("cmip6", "broken", source="local")
        with pytest.raises(EsgvocDbError, match="cmip6@broken is not a valid esgvoc database"):
            projects._resolve_project_connection("cmip6")

    def test_public_api_raises_esgvoc_error_not_sqlalchemy(self):
        _empty(UserState.db_path("cmip6", "broken"))
        UserState.load().set_active("cmip6", "broken", source="local")
        with pytest.raises(EsgvocDbError):
            projects.get_all_collections_in_project("cmip6")

    def test_active_empty_universe_db_raises(self):
        _empty(UserState.db_path("universe", "3.2.5"))
        UserState.load().set_active("universe", "3.2.5", source="registry")
        with pytest.raises(EsgvocDbError, match="universe@3.2.5 is not a valid esgvoc database: the file is empty"):
            get_universe_session()

    def test_valid_universe_db_opens(self):
        make_db(UserState.db_path("universe", "current"), "universe")
        UserState.load().set_active("universe", "current", source="local")
        get_universe_session().close()


class TestCli:
    def test_use_refuses_empty_local_db(self):
        _empty(UserState.db_path("cmip6", "broken"))
        result = runner.invoke(use_app, ["cmip6@broken"])
        assert result.exit_code == 1
        assert "the file is empty" in result.output
        assert UserState.load().get_active("cmip6") is None

    def test_admin_install_refuses_empty_db(self, tmp_path):
        result = runner.invoke(admin_app, ["install", "cmip6", str(_empty(tmp_path / "p.db")), "--name", "broken"])
        assert result.exit_code == 1
        assert "Not installed." in result.output
        assert not UserState.db_path("cmip6", "broken").exists()

    def test_admin_install_accepts_valid_db(self, tmp_path):
        db_path = make_db(tmp_path / "p.db", "cmip6")
        result = runner.invoke(admin_app, ["install", "cmip6", str(db_path), "--name", "ok"])
        assert result.exit_code == 0, result.output
        assert UserState.db_path("cmip6", "ok").exists()
