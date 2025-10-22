"""
Shared fixtures for integration tests that work with the default configuration.
Based on the same pattern as tests/test_config.py - stores current config and restores it after tests.
"""
import pytest
from unittest.mock import patch
from esgvoc.core import service


@pytest.fixture(scope="function")
def default_config_test():
    """
    Store current config, switch to default for testing, then restore original config.
    This follows the same pattern as existing tests in test_config.py.
    """
    assert service.config_manager is not None

    # Store the original active config name
    before_test_active = service.config_manager.get_active_config_name()

    # Initialize registry and switch to default
    service.config_manager._init_registry()
    service.config_manager.switch_config("default")

    yield service.config_manager

    # Restore the original config
    service.config_manager.switch_config(before_test_active)
    current_state = service.get_state()


@pytest.fixture(scope="function")
def mock_subprocess():
    """Mock subprocess.run for git operations."""
    with patch('subprocess.run') as mock_run:
        from unittest.mock import MagicMock
        mock_run.return_value = MagicMock(returncode=0)
        yield mock_run


@pytest.fixture(scope="function")
def sample_config_modifications():
    """Sample config modifications for testing different path types."""
    return {
        "absolute_paths": {
            "universe_local_path": "/tmp/test_absolute/repos/WCRP-universe",
            "universe_db_path": "/tmp/test_absolute/dbs/universe.sqlite",
            "project_local_path": "/tmp/test_absolute/repos/CMIP6_CVs",
            "project_db_path": "/tmp/test_absolute/dbs/cmip6.sqlite"
        },
        "dot_relative_paths": {
            "universe_local_path": "./test_repos/WCRP-universe",
            "universe_db_path": "./test_dbs/universe.sqlite",
            "project_local_path": "./test_repos/CMIP6_CVs",
            "project_db_path": "./test_dbs/cmip6.sqlite"
        },
        "platform_relative_paths": {
            "universe_local_path": "repos/WCRP-universe",
            "universe_db_path": "dbs/universe.sqlite",
            "project_local_path": "repos/CMIP6_CVs",
            "project_db_path": "dbs/cmip6.sqlite"
        }
    }


def modify_default_config_paths(config_manager, path_type, sample_modifications):
    """
    Helper function to modify the default config with different path types.
    Returns the modified config data.
    """
    # Get current default config
    config = config_manager.get_active_config()
    config_data = config.dump()

    paths = sample_modifications[path_type]

    # Modify universe paths
    config_data["universe"]["local_path"] = paths["universe_local_path"]
    config_data["universe"]["db_path"] = paths["universe_db_path"]

    # Modify first project paths (assumes at least one project exists)
    if config_data["projects"]:
        config_data["projects"][0]["local_path"] = paths["project_local_path"]
        config_data["projects"][0]["db_path"] = paths["project_db_path"]

    return config_data


def create_test_config_variant(config_manager, variant_name, path_type, sample_modifications):
    """
    Create a test config variant with specific path type.
    Save it and switch to it for testing.
    """
    modified_config = modify_default_config_paths(config_manager, path_type, sample_modifications)
    config_manager.save_config(modified_config, variant_name)
    config_manager.switch_config(variant_name)
    return config_manager.get_active_config()


def cleanup_test_config(config_manager, config_name):
    """
    Clean up a test config if it exists.
    """
    try:
        configs = config_manager.list_configs()
        if config_name in configs:
            config_manager.remove_config(config_name)
    except (ValueError, KeyError):
        # Config doesn't exist, nothing to clean up
        pass