import toml
import logging
from pathlib import Path
from platformdirs import PlatformDirs
from typing import Type, TypeVar, Generic, Protocol

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define a generic type for configuration
T = TypeVar("T", bound="ConfigSchema")

class ConfigSchema(Protocol):
    """Protocol for application-specific configuration classes."""

    @classmethod
    def load_from_file(cls, file_path: str): ...
    
    def save_to_file(self, file_path: str): ...

class ConfigManager(Generic[T]):
    def __init__(self, config_cls: Type[T], app_name: str, app_author: str, default_settings : dict | None = None ):
        """
        Initialize the configuration manager.
        - config_cls: A class that implements `ConfigSchema` (e.g., ServiceSettings).
        - app_name: Name of the application (used for directory paths).
        - app_author: Name of the author/organization (used for directory paths).
        """
        self.config_cls = config_cls
        self.dirs = PlatformDirs(app_name, app_author)

        # Define standard paths
        self.config_dir = Path(self.dirs.user_config_path).expanduser().resolve()
        self.data_dir = Path(self.dirs.user_data_path).expanduser().resolve()
        self.data_config_dir = None # depends on loaded settings

        self.cache_dir = Path(self.dirs.user_cache_path).expanduser().resolve()


        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.registry_path = self.config_dir / "config_registry.toml"
        self.default_config_path = self.config_dir / "default_setting.toml"
        self.default_settings = default_settings
        self._init_registry()

    def _init_registry(self):
        """Initialize the registry file if it doesn't exist."""
        if not self.registry_path.exists():
            logger.info("Initializing configuration registry...")
            registry = {"configs": {"default": str(self.default_config_path)}, "active": "default"}
            self._save_toml(self.registry_path, registry)
        # Ensure the default settings file exists and save it if necessary
        if not self.default_config_path.exists():
            if self.default_settings:
                logger.info("Saving default settings...")
                self._save_toml(self.default_config_path, self.default_settings)
            else:
                logger.warning("No default settings provided.")

    def _load_toml(self, path: Path) -> dict:
        """Load TOML data from a file."""
        if not path.exists():
            logger.error(f"Configuration file not found: {path}")
            raise FileNotFoundError(f"Configuration file not found: {path}")
        with open(path, "r") as f:
            return toml.load(f)

    def _save_toml(self, path: Path, data: dict) -> None:
        """Save TOML data to a file."""
        with open(path, "w") as f:
            toml.dump(data, f)

    def _get_active_config_path(self) -> Path:
        """Retrieve the path of the active configuration file."""
        registry = self._load_toml(self.registry_path)
        active_config_name = registry["active"]
        return Path(registry["configs"][active_config_name])

    def get_config(self, config_name:str) -> T:
        """Load the configuration as an instance of the given config schema."""
        registry = self._load_toml(self.registry_path)
        if config_name not in registry["configs"]:
            logger.error(f"Config '{config_name}' not found in registry.")
            raise ValueError(f"Config '{config_name}' not found in registry.")
        config_path = self.config_cls.load_from_file(registry["configs"][config_name])
        return self.config_cls.load_from_file(str(config_path))

    def get_active_config(self) -> T:
        """Load the active configuration as an instance of the given config schema."""
        active_config_path = self._get_active_config_path()

        return self.config_cls.load_from_file(str(active_config_path)) 
     
    def get_active_config_name(self) -> str:
        """Retrieve the config name from the registry"""
        registry = self._load_toml(self.registry_path)
        return registry["active"]

    def save_config(self, config_data: dict, name: str | None = None) -> None:
        """Save the modified configuration to the corresponding file and update the registry."""
        
        if name:
            # If a name is provided, save the configuration with that name
            config_path = self.config_dir / f"{name}.toml"
            self._save_toml(config_path, config_data)

            # Update the registry with the new config name
            registry = self._load_toml(self.registry_path)
            registry["configs"][name] = str(config_path)
            registry["active"] = name
            self._save_toml(self.registry_path, registry)

            logger.info(f"Saved configuration to {config_path} and updated registry.")
        else:
            # If no name is provided, give the user a default name, like "user_config"
            default_name = "user_config"
            config_path = self.config_dir / f"{default_name}.toml"
            
            # Check if the user_config already exists, if so, warn them
            if config_path.exists():
                logger.warning(f"{default_name}.toml already exists. Overwriting with the new config.")
            
            # Save the configuration with the default name
            self._save_toml(config_path, config_data)

            # Update the registry with the new config name
            registry = self._load_toml(self.registry_path)
            registry["configs"][default_name] = str(config_path)
            registry["active"] = default_name
            self._save_toml(self.registry_path, registry)

            logger.info(f"Saved new configuration to {config_path} and updated registry.")

    def save_active_config(self, config: T):
        """Save the current configuration to the active file."""
        active_config_path = self._get_active_config_path()
        config.save_to_file(str(active_config_path))

    def switch_config(self, config_name: str):
        """Switch to a different configuration."""
        registry = self._load_toml(self.registry_path)
        if config_name not in registry["configs"]:
            logger.error(f"Config '{config_name}' not found in registry.")
            raise ValueError(f"Config '{config_name}' not found in registry.")
        registry["active"] = config_name
        
        self._save_toml(self.registry_path, registry)
        logger.info(f"Switched to configuration: {config_name}")

    def list_configs(self) -> dict:
        """Return a list of available configurations."""
        return self._load_toml(self.registry_path)["configs"]

    def add_config(self, config_name: str, config_data: dict):
        """Add a new configuration."""
        registry = self._load_toml(self.registry_path)
        if config_name in registry["configs"]:
            raise ValueError(f"Config '{config_name}' already exists.")
        config_path = self.config_dir / f"{config_name}.toml"
        self._save_toml(config_path, config_data)
        registry["configs"][config_name] = str(config_path)
        self._save_toml(self.registry_path, registry)

    def remove_config(self, config_name: str):
        """Remove a configuration."""
        registry = self._load_toml(self.registry_path)
        if config_name == "default":
            raise ValueError("Cannot remove the default configuration.")
        if config_name not in registry["configs"]:
            raise ValueError(f"Config '{config_name}' not found.")
        del registry["configs"][config_name]
        config_path = self.config_dir / f"{config_name}.toml"
        config_path.unlink()

        self._save_toml(self.registry_path, registry)
        logger.info(f"Removed configuration: {config_name}")
        if registry["active"] not in registry["configs"]:
            self.switch_config("default")
            logger.info("active configuration doesnot exist anymore : Switch to default configuration")


    


