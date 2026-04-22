"""
Integration Test Suite for ESGF-Vocab

This package contains comprehensive integration tests for the ESGF-Vocab project,
specifically designed to test the new features while working with the default configuration.

New Features Tested:
- Config Path Resolution (absolute, dot-relative, platform-relative paths)
- Shallow Clone functionality (--depth 1 by default)
- Complete workflow scenarios

Key Principles:
1. Tests work with the "default" configuration only
2. Original user config is stored and restored after tests (like test_config.py)
3. Tests create temporary config variants for testing different path types
4. Proper cleanup ensures test configs are removed
5. Tests cover both individual features and end-to-end scenarios

Test Structure:
- conftest.py: Shared fixtures following test_config.py pattern
- test_config_path_resolution.py: Path resolution feature tests
- test_shallow_clone_integration.py: Shallow clone feature tests
- test_end_to_end_scenarios.py: Complete workflow integration tests

Usage:
    pytest tests/integration/  # Run all integration tests
    pytest tests/integration/test_config_path_resolution.py  # Run specific test file
"""