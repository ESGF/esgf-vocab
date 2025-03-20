
from pathlib import Path
from esgvoc.core.db.models import universe
from esgvoc.core.service.configuration.config_manager import ConfigManager
from esgvoc.core.service.configuration.setting import ServiceSettings

import shutil

config_manager = ConfigManager(ServiceSettings, app_name="esgvoc", app_author="ipsl", default_settings=ServiceSettings.DEFAULT_SETTINGS)

CONFIG_DIR = config_manager.dirs.user_config_path
DBS_DIR = CONFIG_DIR / "dbs"
REPOS_DIR = CONFIG_DIR / "repos"




def remove_config_dir():
    # Remove everything from the .config dir before each test
    if CONFIG_DIR.exists():
        shutil.rmtree(CONFIG_DIR)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)



# Test 1: Init and update default config
def test_init_and_update_default():
    """ initialize the registry assert default setting loaded""" 
    remove_config_dir()
    config_manager._init_registry()
    config = config_manager.get_active_config()
    assert(config.dump() == ServiceSettings.DEFAULT_SETTINGS)

# Test2: Change something and make it the active config
def test_change_save_active():
    config = config_manager.get_active_config()
    config.universe.branch = "new-branch"
    config_manager.save_config(config.dump(),"newbranch")
    config_manager.switch_config("newbranch")
    assert(config_manager.get_active_config().universe.branch=="new-branch")
    assert(Path(CONFIG_DIR / "newbranch.toml").exists())

def test_remove_config():
    cl = config_manager.list_configs()
    if "newbranch" not in cl.keys():
        config_manager.switch_config("default")
        config = config_manager.get_active_config()
        config.universe.branch = "new-branch2"
        config_manager.save_config(config.dump(),"newbranch")
    config_manager.remove_config("newbranch")
    cl = config_manager.list_configs()
    assert ("newbranch" not in cl.keys())
    assert(not Path(CONFIG_DIR / "newbranch.toml").exists())
    
