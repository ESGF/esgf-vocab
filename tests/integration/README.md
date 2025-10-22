# Integration Test Suite

This directory contains comprehensive integration tests for the ESGF-Vocab project, designed to test the new features using the **default configuration only**.

## 🎯 Key Requirements Addressed

### ✅ **Default Configuration Approach**
**IMPORTANT**: Tests work with the default configuration, following the same pattern as `tests/test_config.py`:
- Store current active config name before tests
- Switch to "default" configuration for testing
- Restore original active config after tests complete
- Create temporary test config variants when needed

### ✅ **New Features Tested**
1. **Config Path Resolution System**:
   - Absolute paths (`/tmp/absolute/path`)
   - Dot-relative paths (`./relative/path`, `../parent/path`)
   - Platform-relative paths (`repos/data` - uses PlatformDirs)

2. **Shallow Clone by Default**:
   - Repository cloning now uses `--depth 1` by default
   - Can be disabled with `shallow=False`
   - Proper handling of branch switching with shallow repos

## 📁 Test Structure

### Core Test Files

| File | Purpose |
|------|---------|
| `conftest.py` | Fixtures following `test_config.py` pattern |
| `test_config_path_resolution.py` | Tests all three path resolution modes |
| `test_shallow_clone_integration.py` | Tests shallow clone functionality |
| `test_end_to_end_scenarios.py` | Complete workflow scenarios |

### Test Approach

```python
# Every test uses the default_config_test fixture
def test_example(default_config_test):
    config_manager = default_config_test
    # config_manager is now using "default" config
    # Original config will be restored automatically
```

## 🧪 Running Tests

### Run All Integration Tests
```bash
pytest tests/integration/
```

### Run Specific Test Categories
```bash
# Path resolution tests
pytest tests/integration/test_config_path_resolution.py

# Shallow clone tests
pytest tests/integration/test_shallow_clone_integration.py

# End-to-end scenarios
pytest tests/integration/test_end_to_end_scenarios.py
```

### Run with Verbose Output
```bash
pytest tests/integration/ -v
```

### Run Specific Test Functions
```bash
pytest tests/integration/test_config_path_resolution.py::TestPathResolutionWithDefaultConfig::test_absolute_path_unchanged -v
```

## 🔧 Key Testing Features

### 1. Default Config Pattern
Following the same approach as existing `test_config.py`:
```python
@pytest.fixture(scope="function")
def default_config_test():
    # Store original config
    before_test_active = service.config_manager.get_active_config_name()

    # Switch to default for testing
    service.config_manager.switch_config("default")

    yield service.config_manager

    # Restore original config
    service.config_manager.switch_config(before_test_active)
```

### 2. Path Resolution Testing
- **Absolute paths**: Remain unchanged
- **Dot-relative paths**: Resolve relative to current working directory
- **Platform-relative paths**: Use PlatformDirs with config name isolation

### 3. Shallow Clone Testing
- Verify `--depth 1` is used by default
- Test explicit `shallow=False` removes depth parameter
- Test branch switching with shallow repositories
- Mock subprocess calls to verify git commands

### 4. Test Config Management
- Create temporary config variants for different path types
- Clean up test configs after each test
- Ensure no test configs remain after test completion

## 🛡️ Safety Guarantees

### What These Tests Do
- ✅ Work with the "default" configuration only
- ✅ Store and restore original active config
- ✅ Create temporary test config variants when needed
- ✅ Clean up all test configs after completion
- ✅ Follow the established pattern from `test_config.py`

### What These Tests Don't Do
- ❌ Modify the default config itself (create variants instead)
- ❌ Leave test configs after completion
- ❌ Interfere with user's actual active configuration

## 🧩 Test Categories Explained

### Path Resolution Tests (`test_config_path_resolution.py`)
Tests the new config interpreter that handles three types of paths:

```python
# Test functions demonstrate:

# Absolute paths - unchanged
resolve_path_to_absolute("/tmp/absolute/repos/data")
# Returns: "/tmp/absolute/repos/data"

# Dot-relative paths - relative to current working directory
resolve_path_to_absolute("./repos/data")
# Returns: "/current/working/dir/repos/data"

# Platform-relative paths - use PlatformDirs + config name
resolve_path_to_absolute("repos/data", "config_name")
# Returns: "~/.local/share/esgvoc/{config_name}/repos/data"
```

### Shallow Clone Tests (`test_shallow_clone_integration.py`)
Tests the new default shallow clone behavior:

```python
# Default behavior - shallow clone
fetcher.clone_repository("user", "repo")  # Uses --depth 1

# Explicit full clone
fetcher.clone_repository("user", "repo", shallow=False)  # No --depth
```

### End-to-End Tests (`test_end_to_end_scenarios.py`)
Complete workflow tests combining all features:

- Fresh installation scenarios with default config
- Config variant creation and switching
- Branch switching with shallow repositories
- Multi-path-type setups
- API integration verification

## 🔍 Debugging Tests

### View Test Coverage
```bash
pytest tests/integration/ --cov=esgvoc.core.service.configuration --cov-report=html
```

### Debug Failing Tests
```bash
pytest tests/integration/test_name.py::test_function -v -s --tb=long
```

### Check Config State
```bash
# Verify config is restored properly
pytest tests/integration/ && python -c "from esgvoc.core import service; print(service.config_manager.get_active_config_name())"
```

## 📊 Expected Test Results

When all tests pass, you can be confident that:

1. ✅ **Config Management Safe**: Original config is properly restored
2. ✅ **Path Resolution Works**: All three path types resolve correctly
3. ✅ **Shallow Clone Active**: Repositories are cloned with `--depth 1` by default
4. ✅ **Full Workflows Functional**: Complete installation and usage scenarios work
5. ✅ **Default Config Compatible**: All features work with default configuration

## 🐛 Troubleshooting

### Common Issues

**Config Not Restored**: Check that tests use the `default_config_test` fixture
```python
def test_example(default_config_test):  # ✅ Correct
    config_manager = default_config_test

def test_example():  # ❌ Wrong - no fixture
```

**Test Config Conflicts**: Ensure test configs are cleaned up
```python
try:
    # Test operations
    pass
finally:
    cleanup_test_config(config_manager, "test_config_name")
```

**Path Resolution Issues**: Verify you're testing the right path type
```python
# For platform-relative paths, config name affects resolution
config_manager.save_config(config_data, "specific_name")
config_manager.switch_config("specific_name")
# Path will include "specific_name" directory
```

### Getting Help

If tests fail:
1. Check that default config exists and is valid
2. Verify test configs are properly cleaned up
3. Run individual test files to isolate the problem
4. Check that mocking is applied correctly
5. Ensure working directory is restored after tests

## 🚀 Integration with Existing Tests

These integration tests are designed to work alongside existing tests:

- **`test_config.py`**: Tests basic config functionality
- **`tests/integration/`**: Tests new features with default config
- Both follow the same pattern: store → test with default → restore

The integration tests complement rather than replace existing tests, focusing specifically on the new path resolution and shallow clone features.