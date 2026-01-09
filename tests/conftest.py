import ast
from pathlib import Path
import pytest
import esgvoc.core.service as service

_INSTALL_TEST_FILE_PATH = Path('tests/test_install.py')
_CONFIG_TEST_FILE_PATH = Path('tests/test_config.py')


# Respect definition order.
def _get_test_functions(module_path: Path) -> list[str]:
    if not module_path.exists():
        return []
    with open(module_path) as file:
        file_content = file.read()
        result = [func.name for func in ast.parse(file_content).body \
                  if isinstance(func, ast.FunctionDef) and 'test_' in func.name ]
    return result


def pytest_collection_modifyitems(session, config, items) -> None:
    # Install tests must be the first tests so as to install dbs for the other tests.
    # Config tests must be the last, as they erase configuration files.
    install_test_items = list()
    install_test_func_names = _get_test_functions(_INSTALL_TEST_FILE_PATH)
    config_test_items = list()
    config_test_func_names = _get_test_functions(_CONFIG_TEST_FILE_PATH)
    for item in items:
        for test_name in install_test_func_names:
            if item.name.startswith(test_name):
                install_test_items.append(item)
        for test_name in config_test_func_names:
            if item.name.startswith(test_name):
                config_test_items.append(item)
    for item in install_test_items + config_test_items:
        items.remove(item)
    # Insert install tests first.
    for index in range(len(install_test_items)-1, -1, -1):
        items.insert(0, install_test_items[index])
    # Append config tests at the end.
    items.extend(config_test_items)


# ========== Configuration Management for Tests ==========

@pytest.fixture(scope="session", autouse=True)
def save_and_restore_user_config():
    """
    Save the user's config at the start of testing and restore it at the end.

    Note: test_install.py switches to 'default_dev' config for most tests.
    Individual tests can use fixtures like use_all_dev_config to temporarily
    switch to other configs.

    Configuration types:
    - default_dev: cmip6 + cmip6plus with esgvoc_dev branches (for development)
    - default: cmip6 + cmip6plus with esgvoc branches (for production)
    - all_dev: all projects with esgvoc_dev branches (for multi-project testing)
    """
    # Save the original active config name
    original_config = service.config_manager.get_active_config_name()

    yield

    # Restore the original config at the end of all tests
    service.config_manager.switch_config(original_config)
    service.current_state = service.get_state()


def switch_to_config(config_name: str):
    """
    Helper function to switch to a specific configuration.
    This reloads the entire service state to use the new config.
    """
    service.config_manager.switch_config(config_name)
    service.current_state = service.get_state()


@pytest.fixture
def use_default_dev_config():
    """Fixture to switch to 'default_dev' config for a test (esgvoc_dev branches)."""
    switch_to_config("default_dev")
    yield
    # Config will be restored by save_and_restore_user_config at session end


@pytest.fixture
def use_default_config():
    """Fixture to switch to 'default' config for a test (esgvoc branches for production)."""
    switch_to_config("default")
    yield
    # Config will be restored by save_and_restore_user_config at session end


@pytest.fixture
def use_all_dev_config():
    """Fixture to switch to 'all_dev' config for a test (all projects with esgvoc_dev)."""
    switch_to_config("all_dev")
    yield
    # Config will be restored by save_and_restore_user_config at session end