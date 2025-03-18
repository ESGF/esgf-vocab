# from esgvoc.core.service.config_register import ConfigManager
# from esgvoc.core.service.settings import ServiceSettings
# from esgvoc.core.service.state import StateService
#
# config_manager = ConfigManager()
# active_setting = config_manager.get_active_config()
# active_setting["base_dir"] = str(config_manager.config_dir / config_manager.get_active_config_name())
# service_settings = ServiceSettings.from_config(active_setting)
# state_service = StateService(service_settings)


from esgvoc.core.service.configuration.config_manager import ConfigManager
from esgvoc.core.service.configuration.setting import ServiceSettings
from esgvoc.core.service.state import StateService

config_manager : ConfigManager | None = None
current_state : StateService | None = None

def get_config_manager():
    global config_manager
    if config_manager is None:

        config_manager = ConfigManager(ServiceSettings, app_name="esgvoc", app_author="ipsl", default_settings=ServiceSettings.DEFAULT_SETTINGS)
        active_config_name= config_manager.get_active_config_name()
        config_manager.data_config_dir = config_manager.data_dir / active_config_name
        config_manager.data_config_dir.mkdir(parents=True, exist_ok=True)

    return config_manager   


def get_state():
    global current_state 
    if config_manager is not None:
        current_state = StateService(config_manager.get_active_config())
    return current_state

# Singleton Access Function
config_manager = get_config_manager()
current_state = get_state()

