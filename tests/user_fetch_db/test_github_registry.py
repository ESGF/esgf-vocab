"""Tests for github_registry — project registry and URL resolution."""


from esgvoc.core.github_registry import (
    _DEFAULT_REGISTRY_BASE,
    ProjectInfo,
    get_all_projects,
    get_project,
    get_registry_base_url,
    known_project_ids,
    register_project,
)


class TestRegistryBaseUrl:
    def test_default_url(self, monkeypatch):
        monkeypatch.delenv("ESGVOC_REGISTRY_BASE_URL", raising=False)
        assert get_registry_base_url() == _DEFAULT_REGISTRY_BASE

    def test_env_var_override(self, monkeypatch):
        monkeypatch.setenv("ESGVOC_REGISTRY_BASE_URL", "https://example.com/registry")
        assert get_registry_base_url() == "https://example.com/registry"


class TestProjectInfo:
    def test_raw_index_url_default(self, monkeypatch):
        monkeypatch.delenv("ESGVOC_REGISTRY_BASE_URL", raising=False)
        info = ProjectInfo("cmip7")
        assert info.raw_index_url == f"{_DEFAULT_REGISTRY_BASE}/cmip7.json"

    def test_raw_index_url_with_override(self, monkeypatch):
        monkeypatch.setenv("ESGVOC_REGISTRY_BASE_URL", "https://example.com/reg")
        info = ProjectInfo("cmip7")
        assert info.raw_index_url == "https://example.com/reg/cmip7.json"

    def test_raw_index_url_strips_trailing_slash(self, monkeypatch):
        monkeypatch.setenv("ESGVOC_REGISTRY_BASE_URL", "https://example.com/reg/")
        info = ProjectInfo("cmip7")
        assert info.raw_index_url == "https://example.com/reg/cmip7.json"

    def test_release_tag(self):
        info = ProjectInfo("cmip7")
        assert info.release_tag("v1.0.0") == "cmip7.v1.0.0"


class TestKnownProjects:
    def test_known_projects_include_universe(self):
        assert "universe" in known_project_ids()

    def test_known_projects_include_cmip7(self):
        assert "cmip7" in known_project_ids()

    def test_get_project_returns_info(self):
        info = get_project("universe")
        assert info is not None
        assert info.project_id == "universe"

    def test_get_project_unknown_returns_none(self):
        assert get_project("nonexistent_project_xyz") is None

    def test_get_all_projects_nonempty(self):
        assert len(get_all_projects()) > 0


class TestRegisterProject:
    def test_register_custom_project(self):
        register_project("myorg-cvs", name="MyOrg CVs")
        assert "myorg-cvs" in known_project_ids()
        info = get_project("myorg-cvs")
        assert info.name == "MyOrg CVs"
