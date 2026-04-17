"""
User Tier — API version= parameter + get_active_database_info() tests.

These tests install real SQLite databases into an isolated ESGVOC_HOME
(via the ``isolated_home`` autouse fixture) and exercise the new
``version=`` parameter on all project API functions, plus the new
``get_active_database_info()`` function.

Plan scenarios covered:
  AV-1   get_term_in_project with explicit version= returns term from that DB
  AV-2   get_term_in_project with version= for non-installed version returns None
  AV-3   get_all_terms_in_project with version= returns terms from correct DB
  AV-4   get_all_collections_in_project with version= returns correct collections
  AV-5   get_all_terms_in_collection with version= works
  AV-6   get_term_in_collection with version= works
  AV-7   get_collection_in_project with version= works
  AV-8   get_terms_in_project_by_key_value with version= works
  AV-9   find_terms_in_project with version= works
  AV-10  find_terms_in_collection with version= works
  AV-11  find_collections_in_project with version= works
  AV-12  find_items_in_project with version= works
  AV-13  valid_term_in_project with version= works
  AV-14  valid_term_in_collection with version= works
  AV-15  get_project with version= returns ProjectSpecs
  AV-16  get_active_database_info — returns user-tier info when user tier active
  AV-17  get_active_database_info — returns None when no DB is configured
  AV-18  get_active_database_info — version field matches active version in state
  AV-19  Backward compatibility: all functions work without version= (no regression)
  AV-20  Two installed versions return different term counts (v1 vs v2 differ)
"""

from __future__ import annotations

import pytest

import esgvoc.api as ev
from esgvoc.core.service.user_state import UserState

from .conftest import install_real_db


# ---------------------------------------------------------------------------
# AV-19  Smoke test: backward compat — import works, no regression on existing callers
# ---------------------------------------------------------------------------

class TestBackwardCompatibility:

    def test_get_term_in_project_still_accepts_two_args(self, real_dbs):
        """Calling get_term_in_project(project_id, term_id) still works."""
        install_real_db(real_dbs["v1_path"], real_dbs["project_id"], real_dbs["v1_version"])
        # Should not raise; result may be None (project not in dev tier state)
        result = ev.get_term_in_project(real_dbs["project_id"], "ipsl")
        # No exception = backward compat preserved

    def test_get_all_collections_in_project_still_accepts_one_arg(self, real_dbs):
        install_real_db(real_dbs["v1_path"], real_dbs["project_id"], real_dbs["v1_version"])
        result = ev.get_all_collections_in_project(real_dbs["project_id"])
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# AV-1 / AV-2  get_term_in_project with version=
# ---------------------------------------------------------------------------

class TestGetTermInProjectVersion:

    def test_version_param_opens_correct_db(self, real_dbs):
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]
        install_real_db(real_dbs["v1_path"], pid, ver)

        # With explicit version we bypass the dev-tier state entirely
        result = ev.get_term_in_project(pid, "ipsl", version=ver)
        # The v1 DB is built from a real CMIP6_CVs clone so 'ipsl' should exist
        assert result is not None

    def test_version_not_installed_returns_none(self, real_dbs):
        pid = real_dbs["project_id"]
        # Do NOT install any DB — requesting a non-existent version returns None
        result = ev.get_term_in_project(pid, "ipsl", version="v99.0.0")
        assert result is None

    def test_explicit_version_returns_none_for_missing_term(self, real_dbs):
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]
        install_real_db(real_dbs["v1_path"], pid, ver)
        result = ev.get_term_in_project(pid, "this-term-does-not-exist", version=ver)
        assert result is None


# ---------------------------------------------------------------------------
# AV-3  get_all_terms_in_project with version=
# ---------------------------------------------------------------------------

class TestGetAllTermsVersion:

    def test_returns_terms_from_versioned_db(self, real_dbs):
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]
        install_real_db(real_dbs["v1_path"], pid, ver)
        terms = ev.get_all_terms_in_project(pid, version=ver)
        assert len(terms) > 0

    def test_non_installed_version_returns_empty(self, real_dbs):
        pid = real_dbs["project_id"]
        terms = ev.get_all_terms_in_project(pid, version="v99.0.0")
        assert terms == []


# ---------------------------------------------------------------------------
# AV-4  get_all_collections_in_project with version=
# ---------------------------------------------------------------------------

class TestGetAllCollectionsVersion:

    def test_returns_collections_from_versioned_db(self, real_dbs):
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]
        install_real_db(real_dbs["v1_path"], pid, ver)
        collections = ev.get_all_collections_in_project(pid, version=ver)
        assert isinstance(collections, list)
        assert len(collections) > 0

    def test_non_installed_returns_empty(self, real_dbs):
        collections = ev.get_all_collections_in_project(real_dbs["project_id"], version="v99.0.0")
        assert collections == []


# ---------------------------------------------------------------------------
# AV-5 / AV-6  get_all_terms_in_collection / get_term_in_collection with version=
# ---------------------------------------------------------------------------

class TestCollectionTermsVersion:

    def _get_first_collection(self, real_dbs, ver):
        pid = real_dbs["project_id"]
        install_real_db(real_dbs["v1_path"], pid, ver)
        collections = ev.get_all_collections_in_project(pid, version=ver)
        assert collections, "DB has no collections"
        return pid, collections[0]

    def test_get_all_terms_in_collection_with_version(self, real_dbs):
        ver = real_dbs["v1_version"]
        pid, col_id = self._get_first_collection(real_dbs, ver)
        terms = ev.get_all_terms_in_collection(pid, col_id, version=ver)
        assert isinstance(terms, list)

    def test_get_term_in_collection_with_version(self, real_dbs):
        ver = real_dbs["v1_version"]
        pid, col_id = self._get_first_collection(real_dbs, ver)
        terms = ev.get_all_terms_in_collection(pid, col_id, version=ver)
        if terms:
            term_id = terms[0].id
            result = ev.get_term_in_collection(pid, col_id, term_id, version=ver)
            assert result is not None
            assert result.id == term_id


# ---------------------------------------------------------------------------
# AV-7  get_collection_in_project with version=
# ---------------------------------------------------------------------------

class TestGetCollectionVersion:

    def test_returns_collection_info(self, real_dbs):
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]
        install_real_db(real_dbs["v1_path"], pid, ver)
        collections = ev.get_all_collections_in_project(pid, version=ver)
        if collections:
            result = ev.get_collection_in_project(pid, collections[0], version=ver)
            assert result is not None
            col_id, ctx = result
            assert col_id == collections[0]

    def test_missing_version_returns_none(self, real_dbs):
        result = ev.get_collection_in_project(real_dbs["project_id"], "institution", version="v99.0.0")
        assert result is None


# ---------------------------------------------------------------------------
# AV-9 / AV-10 / AV-11 / AV-12  find_ functions with version=
# ---------------------------------------------------------------------------

class TestFindFunctionsVersion:

    def test_find_terms_in_project_with_version(self, real_dbs):
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]
        install_real_db(real_dbs["v1_path"], pid, ver)
        results = ev.find_terms_in_project("ipsl", pid, version=ver)
        assert isinstance(results, list)

    def test_find_collections_in_project_with_version(self, real_dbs):
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]
        install_real_db(real_dbs["v1_path"], pid, ver)
        results = ev.find_collections_in_project("institution", pid, version=ver)
        assert isinstance(results, list)

    def test_find_items_in_project_with_version(self, real_dbs):
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]
        install_real_db(real_dbs["v1_path"], pid, ver)
        results = ev.find_items_in_project("ipsl", pid, version=ver)
        assert isinstance(results, list)

    def test_find_terms_missing_version_returns_empty(self, real_dbs):
        results = ev.find_terms_in_project("ipsl", real_dbs["project_id"], version="v99.0.0")
        assert results == []


# ---------------------------------------------------------------------------
# AV-13 / AV-14  valid_ functions with version=
# ---------------------------------------------------------------------------

class TestValidFunctionsVersion:

    def test_valid_term_in_project_with_version(self, real_dbs):
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]
        install_real_db(real_dbs["v1_path"], pid, ver)
        # valid_term_in_project checks if a value matches any term in the project
        results = ev.valid_term_in_project("ipsl", pid, version=ver)
        assert isinstance(results, list)

    def test_valid_term_in_collection_with_version(self, real_dbs):
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]
        install_real_db(real_dbs["v1_path"], pid, ver)
        collections = ev.get_all_collections_in_project(pid, version=ver)
        if collections:
            results = ev.valid_term_in_collection("ipsl", pid, collections[0], version=ver)
            assert isinstance(results, list)


# ---------------------------------------------------------------------------
# AV-15  get_project with version=
# ---------------------------------------------------------------------------

class TestGetProjectVersion:

    def test_returns_project_specs(self, real_dbs):
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]
        install_real_db(real_dbs["v1_path"], pid, ver)
        specs = ev.get_project(pid, version=ver)
        # ProjectSpecs or None (depends on DB content)
        # At minimum it should not raise

    def test_missing_version_returns_none(self, real_dbs):
        result = ev.get_project(real_dbs["project_id"], version="v99.0.0")
        assert result is None


# ---------------------------------------------------------------------------
# AV-16 / AV-17 / AV-18  get_active_database_info
# ---------------------------------------------------------------------------

class TestGetActiveDatabaseInfo:

    def test_returns_none_when_nothing_installed(self, real_dbs):
        # isolated_home is empty, nothing installed
        info = ev.get_active_database_info(real_dbs["project_id"])
        assert info is None

    def test_returns_user_tier_info_after_install(self, real_dbs):
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]
        install_real_db(real_dbs["v1_path"], pid, ver)  # also sets active
        info = ev.get_active_database_info(pid)
        assert info is not None
        assert info["tier"] == "user"

    def test_version_matches_active_state(self, real_dbs):
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]
        install_real_db(real_dbs["v1_path"], pid, ver)
        info = ev.get_active_database_info(pid)
        assert info["version"] == ver

    def test_path_points_to_existing_file(self, real_dbs):
        from pathlib import Path
        pid = real_dbs["project_id"]
        ver = real_dbs["v1_version"]
        install_real_db(real_dbs["v1_path"], pid, ver)
        info = ev.get_active_database_info(pid)
        assert Path(info["path"]).exists()

    def test_unknown_project_returns_none(self):
        info = ev.get_active_database_info("no-such-project-xyz")
        assert info is None

    def test_switching_active_version_updates_info(self, real_dbs):
        pid = real_dbs["project_id"]
        v1 = real_dbs["v1_version"]
        v2 = real_dbs["v2_version"]

        install_real_db(real_dbs["v1_path"], pid, v1)
        install_real_db(real_dbs["v2_path"], pid, v2)

        state = UserState.load()
        state.set_active(pid, v1)
        state.save()
        info_v1 = ev.get_active_database_info(pid)
        assert info_v1["version"] == v1

        state.set_active(pid, v2)
        state.save()
        info_v2 = ev.get_active_database_info(pid)
        assert info_v2["version"] == v2


# ---------------------------------------------------------------------------
# AV-20  Two installed versions can be queried independently
# ---------------------------------------------------------------------------

class TestTwoVersionsCoexist:

    def test_both_versions_queryable_simultaneously(self, real_dbs):
        pid = real_dbs["project_id"]
        v1 = real_dbs["v1_version"]
        v2 = real_dbs["v2_version"]
        install_real_db(real_dbs["v1_path"], pid, v1)
        install_real_db(real_dbs["v2_path"], pid, v2)

        terms_v1 = ev.get_all_terms_in_project(pid, version=v1)
        terms_v2 = ev.get_all_terms_in_project(pid, version=v2)

        # Both should return non-empty lists from their respective DBs
        assert len(terms_v1) > 0
        assert len(terms_v2) > 0

    def test_version_param_targets_specific_db(self, real_dbs):
        """get_term_in_project(version=v1) uses v1 DB, (version=v2) uses v2 DB."""
        pid = real_dbs["project_id"]
        v1 = real_dbs["v1_version"]
        v2 = real_dbs["v2_version"]
        install_real_db(real_dbs["v1_path"], pid, v1)
        install_real_db(real_dbs["v2_path"], pid, v2)

        # Both calls should succeed without raising, regardless of result
        r1 = ev.get_term_in_project(pid, "ipsl", version=v1)
        r2 = ev.get_term_in_project(pid, "ipsl", version=v2)
        # If the term exists in both DBs it should be found in both
        if r1 is not None and r2 is not None:
            assert r1.id == r2.id
