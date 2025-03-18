"""
from esgvoc.core.service.settings import ServiceSettings
from esgvoc.core.service.state import StateService
import shutil
from pathlib import Path
from esgvoc.core.service.config_register import ConfigManager, DEFAULT_CONFIG
import esgvoc.api as ev
from esgvoc.core.service import config_manager, service_settings, state_service 

CONFIG_DIR = Path(ConfigManager().dirs.user_config_path)
DBS_DIR = CONFIG_DIR / "dbs"
REPOS_DIR = CONFIG_DIR / "repos"

# def get_config_setting_state():
#     active_setting = config_manager.get_active_config()
#     active_setting["base_dir"] = str(config_manager.config_dir / config_manager.get_active_config_name())
#     service_settings = ServiceSettings.from_config(active_setting)
#     state_service = StateService(service_settings)
#     return config_manager, service_settings, state_service


# Test 1: Init and update default config
def test_init_and_update_default():
    # Remove everything from the .config dir before each test
    if CONFIG_DIR.exists():
        shutil.rmtree(CONFIG_DIR)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    config_manager.init()
    state_service.synchronize_all()
    
    # Check that databases are created in the default config directory
    for db_path in ["dbs/cmip6.sqlite", "dbs/cmip6plus.sqlite", "dbs/universe.sqlite"]:
        db_full_path = CONFIG_DIR / config_manager.get_active_config_name() / db_path
        assert db_full_path.exists(), f"Database not found: {db_full_path}"

    assert(ev.valid_term_in_project("IPSL","cmip6")) 

# Test 2: Add a config 'config1' with the default setting
def test_add_config1_with_default_setting():

    config_manager.init()
    config_manager.add("config1", DEFAULT_CONFIG)
    assert(config_manager.get_active_config_name()=="config1")

    active_setting = config_manager.get_active_config()
    active_setting["base_dir"] = str(config_manager.config_dir / config_manager.get_active_config_name())
    service_settings = ServiceSettings.from_config(active_setting)
    state_service = StateService(service_settings)

    state_service.synchronize_all()

    # Check that databases are created in the 'config1' config directory
    for db_path in ["dbs/cmip6.sqlite", "dbs/cmip6plus.sqlite", "dbs/universe.sqlite"]:
        db_full_path = CONFIG_DIR / config_manager.get_active_config_name() / db_path
        assert db_full_path.exists(), f"Database not found: {db_full_path}"
    assert(ev.valid_term_in_project("IPSL","cmip6")) 

# Test 3: Remove a project from a setting
def test_remove_project_from_setting():
    config_manager.init()
    # Modify the config to remove 'cmip6' project
    modified_config = {
        "projects": [DEFAULT_CONFIG["projects"][1]],  # Keep only 'cmip6plus'
        "universe": DEFAULT_CONFIG["universe"]
    }
    config_manager.add("config1_wo_cmip6", modified_config)
    active_setting = config_manager.get_active_config()
    active_setting["base_dir"] = str(config_manager.config_dir / config_manager.get_active_config_name())
    service_settings = ServiceSettings.from_config(active_setting)
    state_service = StateService(service_settings)

    state_service.synchronize_all()

    # Remove associated databases and repos
    db_to_remove = CONFIG_DIR / "dbs/cmip6.sqlite"
    repo_to_remove = CONFIG_DIR / "repos/CMIP6_CVs"
    assert not db_to_remove.exists(), f"Database not removed: {db_to_remove}"
    assert not repo_to_remove.exists(), f"Repo not removed: {repo_to_remove}"

# Test 4: Add a config with a new project in the setting
def test_add_config_with_new_project():
    
    

    # Add a new project to the config
    new_project = {
        "project_name": "cmip6",
        "github_repo": "https://github.com/WCRP-CMIP/CMIP6_CVs",
        "branch": "esgvoc",
        "local_path": "repos/CMIP6_CVs",
        "db_path": "dbs/cmip6b.sqlite"
    }
    
    config_manager.add_project(new_project,"config1_wo_cmip6")
    
    active_setting = config_manager.get_config("config1_wo_cmip6")
    active_setting["base_dir"] = str(config_manager.config_dir / config_manager.get_active_config_name())
    service_settings = ServiceSettings.from_config(active_setting)
    state_service = StateService(service_settings)

    state_service.synchronize_all()

    db_path = CONFIG_DIR / "config1_wo_cmip6" / new_project["db_path"]


    assert(db_path.exists())
"""
