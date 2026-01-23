# from esgvoc.core.service.config_register import ConfigManager
# from esgvoc.core.service.settings import ServiceSettings
# from esgvoc.core.service.state import StateService
#
# config_manager = ConfigManager()
# active_setting = config_manager.get_active_config()
# active_setting["base_dir"] = str(config_manager.config_dir / config_manager.get_active_config_name())
# service_settings = ServiceSettings.from_config(active_setting)
# state_service = StateService(service_settings)


import logging

from esgvoc.core.service.configuration.config_manager import ConfigManager
from esgvoc.core.service.configuration.setting import ServiceSettings
from esgvoc.core.service.state import StateService

config_manager: ConfigManager | None = None
current_state: StateService | None = None

_logger = logging.getLogger(__name__)


def _initialize_version_check(cfg_manager: ConfigManager) -> None:
    """Initialize the version check system."""
    try:
        from esgvoc.core.version_checker import initialize_version_checker

        active_config = cfg_manager.get_active_config()
        version_settings = getattr(active_config, "version_check", None)

        if version_settings is None:
            enabled = True
            check_interval = 12
            reminder_interval = 72
        else:
            enabled = version_settings.enabled
            check_interval = version_settings.check_interval_hours
            reminder_interval = version_settings.reminder_interval_hours

        checker = initialize_version_checker(
            cache_dir=cfg_manager.cache_dir,
            check_interval_hours=check_interval,
            reminder_interval_hours=reminder_interval,
            enabled=enabled,
        )

        # Synchronous check: blocks import for max ~3s (PyPI timeout)
        # but guarantees the warning is visible immediately.
        # Only fetches from PyPI if cache is expired (every 12h by default).
        checker.check_sync()

    except Exception as e:
        # Never crash on version check failure
        _logger.debug(f"Version check initialization failed: {e}")


def get_config_manager():
    global config_manager
    if config_manager is None:
        config_manager = ConfigManager(
            ServiceSettings,
            app_name="esgvoc",
            app_author="ipsl",
            default_settings=ServiceSettings._get_default_settings(),
        )
        active_config_name = config_manager.get_active_config_name()
        config_manager.data_config_dir = config_manager.data_dir / active_config_name
        config_manager.data_config_dir.mkdir(parents=True, exist_ok=True)

        # Initialize version checker after config is ready
        _initialize_version_check(config_manager)

    return config_manager   


def get_state():
    global current_state
    if config_manager is not None:
        service_settings = config_manager.get_active_config()
        current_state = StateService(service_settings)
    return current_state

# Singleton Access Function
config_manager = get_config_manager()
current_state = get_state()

