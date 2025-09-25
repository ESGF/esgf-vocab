import ast
from pathlib import Path

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