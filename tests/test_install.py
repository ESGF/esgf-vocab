import os
from esgvoc.core import service
import esgvoc.api as ev


def _ensure_default_dev_config_exists():
    """Ensure the 'default_dev' config exists for development testing."""
    default_dev_config = {
        "projects": [
            {
                "project_name": "cmip6",
                "github_repo": "https://github.com/WCRP-CMIP/CMIP6_CVs",
                "branch": "esgvoc_dev",
                "local_path": "repos/CMIP6_CVs",
                "db_path": "dbs/cmip6.sqlite",
                "offline_mode": False,
            },
            {
                "project_name": "cmip6plus",
                "github_repo": "https://github.com/WCRP-CMIP/CMIP6Plus_CVs",
                "branch": "esgvoc_dev",
                "local_path": "repos/CMIP6Plus_CVs",
                "db_path": "dbs/cmip6plus.sqlite",
                "offline_mode": False,
            },
        ],
        "universe": {
            "github_repo": "https://github.com/WCRP-CMIP/WCRP-universe",
            "branch": "esgvoc_dev",
            "local_path": "repos/WCRP-universe",
            "db_path": "dbs/universe.sqlite",
            "offline_mode": False,
        },
    }

    # Check if default_dev config exists
    existing_configs = service.config_manager.list_configs()
    if "default_dev" not in existing_configs:
        service.config_manager.add_config("default_dev", default_dev_config)


def _ensure_all_dev_config_exists():
    """Ensure the 'all_dev' config exists for testing with multiple projects."""
    all_dev_config = {
        "projects": [
            {
                "project_name": "cmip6",
                "github_repo": "https://github.com/WCRP-CMIP/CMIP6_CVs",
                "branch": "esgvoc_dev",
                "local_path": "repos/CMIP6_CVs",
                "db_path": "dbs/cmip6.sqlite",
                "offline_mode": False,
            },
            {
                "project_name": "cmip6plus",
                "github_repo": "https://github.com/WCRP-CMIP/CMIP6Plus_CVs",
                "branch": "esgvoc_dev",
                "local_path": "repos/CMIP6Plus_CVs",
                "db_path": "dbs/cmip6plus.sqlite",
                "offline_mode": False,
            },
            {
                "project_name": "cmip7",
                "github_repo": "https://github.com/WCRP-CMIP/CMIP7-CVs",
                "branch": "esgvoc_dev",
                "local_path": "repos/CMIP7_CVs",
                "db_path": "dbs/cmip7.sqlite",
                "offline_mode": False,
            },
            {
                "project_name": "cordex-cmip6",
                "github_repo": "https://github.com/WCRP-CORDEX/cordex-cmip6-cv",
                "branch": "esgvoc_dev",
                "local_path": "repos/cordex-cmip6-cv",
                "db_path": "dbs/cordex-cmip6.sqlite",
                "offline_mode": False,
            },
            {
                "project_name": "input4mip",
                "github_repo": "https://github.com/PCMDI/input4MIPs_CVs",
                "branch": "esgvoc_dev",
                "local_path": "repos/Input4MIP_CVs",
                "db_path": "dbs/input4mips.sqlite",
                "offline_mode": False,
            },
            {
                "project_name": "obs4ref",
                "github_repo": "https://github.com/Climate-REF/Obs4REF_CVs",
                "branch": "esgvoc_dev",
                "local_path": "repos/obs4REF_CVs",
                "db_path": "dbs/obs4ref.sqlite",
                "offline_mode": False,
            },
            {
                "project_name": "emd",
                "github_repo": "https://github.com/WCRP-CMIP/Essential-Model-Documentation",
                "branch": "esgvoc",
                "local_path": "repos/Essential-Model-Documentation",
                "db_path": "dbs/emd.sqlite",
                "offline_mode": False,
            },
        ],
        "universe": {
            "github_repo": "https://github.com/WCRP-CMIP/WCRP-universe",
            "branch": "esgvoc_dev",
            "local_path": "repos/WCRP-universe",
            "db_path": "dbs/universe.sqlite",
            "offline_mode": False,
        },
    }

    # Check if all_dev config exists
    existing_configs = service.config_manager.list_configs()
    if "all_dev" not in existing_configs:
        service.config_manager.add_config("all_dev", all_dev_config)


def test_install():
    """Essential install test that initializes the package for other tests."""
    assert service.config_manager is not None
    before_test_active = service.config_manager.get_active_config_name()
    service.config_manager._init_registry()

    # Determine which config to use from environment variable
    # ESGVOC_TEST_CONFIG can be: "default_dev" (development) or "default" (production)
    test_config = os.getenv("ESGVOC_TEST_CONFIG", "default_dev")

    # Ensure test configs exist
    _ensure_default_dev_config_exists()
    _ensure_all_dev_config_exists()

    # Test with the selected default config (cmip6 + cmip6plus or all projects)
    service.config_manager.switch_config(test_config)
    current_state = service.get_state()
    assert current_state is not None
    current_state.synchronize_all()
    # Verify the expected projects are present
    projects = ev.get_all_projects()
    # default_dev and default have 2 projects, "all" has 7
    if test_config in ["default_dev", "default"]:
        assert len(projects) == 2
    assert "cmip6" in projects
    assert "cmip6plus" in projects

    # Only test with all_dev config if we're in development mode (default_dev)
    # Skip this if using production configs (default, all, etc.)
    if test_config == "default_dev":
        # Test with all_dev config to initialize all projects
        service.config_manager.switch_config("all_dev")
        current_state = service.get_state()
        assert current_state is not None
        current_state.synchronize_all()
        # Verify a project that's only in all_dev
        assert "cordex-cmip6" in ev.get_all_projects()

        # Switch back to the selected test config for the rest of the tests
        # (The session fixture will restore the original config at the very end)
        service.config_manager.switch_config(test_config)
        current_state = service.get_state()