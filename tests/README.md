# ESGVoc Testing Guide

## Overview

The esgvoc test suite uses a configuration-based system to test against different CV (Controlled Vocabulary) branches and project combinations. This ensures that tests can validate both development and production environments.

## Configuration Types

The test suite supports three main configurations:

### 1. `default_dev` (Development Testing)
- **Projects**: cmip6 + cmip6plus
- **Branches**: `esgvoc_dev`
- **Purpose**: Development and testing of new features
- **When to use**: During active development of esgvoc library and CVs

### 2. `default` (Production Testing)
- **Projects**: cmip6 + cmip6plus
- **Branches**: `esgvoc` (production branches)
- **Purpose**: Pre-release validation and production testing
- **When to use**: Before releasing to production, CI/CD pipelines

### 3. `all_dev` (Multi-Project Testing)
- **Projects**: All 7 projects (cmip6, cmip6plus, cmip7, cordex-cmip6, input4mip, obs4ref, emd)
- **Branches**: `esgvoc_dev`
- **Purpose**: Testing features that require multiple projects
- **When to use**: Testing multi-project functionality like duplicate collections

## Running Tests

### Development Testing (Default)

```bash
# Uses default_dev configuration (esgvoc_dev branches)
uv run pytest tests/
```

### Production Testing

```bash
# Uses default configuration (esgvoc production branches)
ESGVOC_TEST_CONFIG=default uv run pytest tests/
```

### Specific Test Files

```bash
# Run only API tests
uv run pytest tests/test_api_project.py

# Run with production config
ESGVOC_TEST_CONFIG=default uv run pytest tests/test_api_project.py
```

## Environment Variables

### `ESGVOC_TEST_CONFIG`

Controls which configuration is used for the test suite.

- **Values**: `default_dev` (default) | `default` | `all_dev`
- **Default**: `default_dev`
- **Example**:
  ```bash
  export ESGVOC_TEST_CONFIG=default
  uv run pytest tests/
  ```

## Test Configuration System

### How It Works

1. **Session Setup** (`conftest.py`):
   - Saves the user's current active configuration
   - Provides fixtures to switch between configurations
   - Restores the original configuration after all tests complete

2. **Install Test** (`test_install.py`):
   - Creates required test configurations if they don't exist
   - Reads `ESGVOC_TEST_CONFIG` to determine which config to use
   - Synchronizes all projects in the selected configuration
   - Switches to the selected config for subsequent tests

3. **Individual Tests**:
   - Most tests use the configuration set by `test_install.py`
   - Tests requiring specific configs use fixtures:
     - `use_default_dev_config`: Temporarily switch to default_dev
     - `use_default_config`: Temporarily switch to default
     - `use_all_dev_config`: Temporarily switch to all_dev

### Using Fixtures in Tests

```python
def test_multiple_collections_per_data_descriptor(use_all_dev_config):
    """This test needs all_dev config for cordex-cmip6 data."""
    # Test automatically uses all_dev config
    collections = projects.get_collection_from_data_descriptor_in_project(
        "cordex-cmip6", "mip_era"
    )
    assert len(collections) == 2  # mip_era and project_id
```

## CI/CD Integration

### Development Pipeline

```yaml
- name: Run Development Tests
  run: uv run pytest tests/
  env:
    ESGVOC_TEST_CONFIG: default_dev
```

### Production Pipeline

```yaml
- name: Run Production Tests
  run: uv run pytest tests/
  env:
    ESGVOC_TEST_CONFIG: default
```

## Transition from Development to Production

When preparing for a production release:

1. **Verify CVs are released** on `esgvoc` branches
2. **Run tests against production config**:
   ```bash
   ESGVOC_TEST_CONFIG=default uv run pytest tests/
   ```
3. **Check all tests pass** with production CVs
4. **Update CI/CD** to use `default` config for release validation

## Troubleshooting

### "Config not found" error

If you get a configuration not found error:
```bash
# Re-run the install test to create missing configs
uv run pytest tests/test_install.py
```

### Tests using wrong configuration

Check the environment variable:
```bash
echo $ESGVOC_TEST_CONFIG
# Should be either empty (uses default_dev) or "default" or "all_dev"
```

Unset if needed:
```bash
unset ESGVOC_TEST_CONFIG
```

### User config not restored

If your original configuration isn't restored after tests:
```bash
# Manually switch back
esgvoc config switch your-original-config
```

The session fixture should handle this automatically, but if tests are interrupted, you may need to manually restore.

## Adding New Test Configurations

To add a new test configuration:

1. **Create configuration function** in `test_install.py`:
   ```python
   def _ensure_my_config_exists():
       my_config = {
           "projects": [...],
           "universe": {...}
       }
       if "my_config" not in service.config_manager.list_configs():
           service.config_manager.add_config("my_config", my_config)
   ```

2. **Call in test_install()**:
   ```python
   _ensure_my_config_exists()
   ```

3. **Add fixture in conftest.py**:
   ```python
   @pytest.fixture
   def use_my_config():
       """Fixture to switch to 'my_config' for a test."""
       switch_to_config("my_config")
       yield
   ```

4. **Update README** with the new configuration

## Best Practices

1. **Use fixtures for specific configs**: If a test needs a specific configuration, use the appropriate fixture rather than manually switching.

2. **Keep configs in sync**: When CV structure changes, update the config definitions in `test_install.py`.

3. **Test both dev and prod**: Before releases, run the full test suite against both `default_dev` and `default` configurations.

4. **Don't commit config changes**: The test suite creates configs automatically - don't manually modify them in your user config directory.

## Related Files

- `tests/conftest.py`: Configuration fixtures and session management
- `tests/test_install.py`: Config creation and initialization
- `tests/test_api_project.py`: Example of using `use_all_dev_config` fixture
- `tests/api_inputs.py`: Test data based on cmip6/cmip6plus projects
