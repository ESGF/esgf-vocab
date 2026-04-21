"""
test_config.py — Legacy config system tests (REMOVED)

The named dev-environment config system (ConfigManager, ServiceSettings,
TOML config files) has been eliminated. These tests are no longer applicable.

The new state model uses per-project pointer files (see UserState in
esgvoc.core.service.user_state) — no ConfigManager or TOML configs needed.
"""

import pytest


@pytest.mark.skip(reason="Legacy config system has been removed — tests no longer applicable")
def test_init_and_update_default():
    pass


@pytest.mark.skip(reason="Legacy config system has been removed — tests no longer applicable")
def test_change_save_active():
    pass


@pytest.mark.skip(reason="Legacy config system has been removed — tests no longer applicable")
def test_remove_config():
    pass
