import pytest

from tests.python_api.conftest import installed_dbs, universe_db, cmip7_db  # noqa: F401


@pytest.fixture(scope="session")
def project_with_attr_specs(installed_dbs):
    """
    Return ``(project_id, attr_specs)`` for the first installed project
    that has ``attr_specs`` defined.  Skips the test session if none found.
    """
    import esgvoc.api.projects as api

    for pid in api.get_all_projects():
        proj = api.get_project(pid)
        if proj and proj.attr_specs:
            return pid, proj.attr_specs
    pytest.skip(
        "No installed project has attr_specs. "
        "Install a project with attr_specs (e.g. cmip6) to run GA integration tests."
    )
