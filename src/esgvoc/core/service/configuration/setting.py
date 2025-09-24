from typing import ClassVar, Dict, Optional
from pathlib import Path

import toml
from pydantic import BaseModel, Field
from platformdirs import PlatformDirs


def resolve_path_to_absolute(relative_path: Optional[str]) -> Optional[str]:
    """
    Convert a relative path to an absolute path without modifying the original.
    This is used for internal path resolution only.
    """
    if relative_path is None:
        return None

    path_obj = Path(relative_path)

    if path_obj.is_absolute():
        return str(path_obj.resolve())

    # Handle dot-relative paths (./... or ../..) relative to current working directory
    if relative_path.startswith('.'):
        return str((Path.cwd() / relative_path).resolve())

    # Handle plain relative paths using PlatformDirs (default behavior)
    dirs = PlatformDirs("esgvoc", "ipsl")
    base_path = Path(dirs.user_data_path).expanduser().resolve()
    return str(base_path / relative_path)


class ProjectSettings(BaseModel):
    project_name: str
    github_repo: str
    branch: Optional[str] = "main"
    local_path: Optional[str] = None
    db_path: Optional[str] = None

    def get_absolute_local_path(self) -> Optional[str]:
        """Get the absolute local path without modifying the stored value."""
        return resolve_path_to_absolute(self.local_path)

    def get_absolute_db_path(self) -> Optional[str]:
        """Get the absolute db path without modifying the stored value."""
        return resolve_path_to_absolute(self.db_path)


class UniverseSettings(BaseModel):
    github_repo: str
    branch: Optional[str] = None
    local_path: Optional[str] = None
    db_path: Optional[str] = None

    def get_absolute_local_path(self) -> Optional[str]:
        """Get the absolute local path without modifying the stored value."""
        return resolve_path_to_absolute(self.local_path)

    def get_absolute_db_path(self) -> Optional[str]:
        """Get the absolute db path without modifying the stored value."""
        return resolve_path_to_absolute(self.db_path)


class ServiceSettings(BaseModel):
    universe: UniverseSettings
    projects: Dict[str, ProjectSettings] = Field(default_factory=dict)

    @staticmethod
    def _get_default_base_path() -> Path:
        """Get the default base path for data storage using PlatformDirs."""
        dirs = PlatformDirs("esgvoc", "ipsl")
        return Path(dirs.user_data_path).expanduser().resolve()

    @classmethod
    def _get_default_project_configs(cls) -> Dict[str, dict]:
        """Generate default project configurations with absolute paths."""
        base_path = cls._get_default_base_path()
        return {
            "cmip6": {
                "project_name": "cmip6",
                "github_repo": "https://github.com/WCRP-CMIP/CMIP6_CVs",
                "branch": "esgvoc",
                "local_path": str(base_path / "repos" / "CMIP6_CVs"),
                "db_path": str(base_path / "dbs" / "cmip6.sqlite"),
            },
            "cmip6plus": {
                "project_name": "cmip6plus",
                "github_repo": "https://github.com/WCRP-CMIP/CMIP6Plus_CVs",
                "branch": "esgvoc",
                "local_path": str(base_path / "repos" / "CMIP6Plus_CVs"),
                "db_path": str(base_path / "dbs" / "cmip6plus.sqlite"),
            },
            "input4mip": {
                "project_name": "input4mip",
                "github_repo": "https://github.com/PCMDI/input4MIPs_CVs",
                "branch": "esgvoc",
                "local_path": str(base_path / "repos" / "Input4MIP_CVs"),
                "db_path": str(base_path / "dbs" / "input4mips.sqlite"),
            },
            "obs4ref": {
                "project_name": "obs4ref",
                "github_repo": "https://github.com/Climate-REF/Obs4REF_CVs",
                "branch": "main",
                "local_path": str(base_path / "repos" / "obs4REF_CVs"),
                "db_path": str(base_path / "dbs" / "obs4ref.sqlite"),
            },
            "cordex-cmip6": {
                "project_name": "cordex-cmip6",
                "github_repo": "https://github.com/WCRP-CORDEX/cordex-cmip6-cv",
                "branch": "esgvoc",
                "local_path": str(base_path / "repos" / "cordex-cmip6-cv"),
                "db_path": str(base_path / "dbs" / "cordex-cmip6.sqlite"),
            },
            "cmip7": {
                "project_name": "cmip7",
                "github_repo": "https://github.com/WCRP-CMIP/CMIP7-CVs",
                "branch": "esgvoc",
                "local_path": str(base_path / "repos" / "CMIP7-CVs"),
                "db_path": str(base_path / "dbs" / "cmip7.sqlite"),
            },
        }

    @classmethod
    def _get_default_settings(cls) -> dict:
        """Generate default settings with absolute paths."""
        base_path = cls._get_default_base_path()
        project_configs = cls._get_default_project_configs()
        return {
            "universe": {
                "github_repo": "https://github.com/WCRP-CMIP/WCRP-universe",
                "branch": "esgvoc",
                "local_path": str(base_path / "repos" / "WCRP-universe"),
                "db_path": str(base_path / "dbs" / "universe.sqlite"),
            },
            "projects": [
                project_configs["cmip6"],
                project_configs["cmip6plus"],
            ],
        }

    # 🔹 Properties that provide access to the dynamic configurations
    @property
    def DEFAULT_PROJECT_CONFIGS(self) -> Dict[str, dict]:
        return self._get_default_project_configs()

    @property
    def DEFAULT_SETTINGS(self) -> dict:
        return self._get_default_settings()

    @classmethod
    def load_from_file(cls, file_path: str) -> "ServiceSettings":
        """Load configuration from a TOML file, falling back to defaults if necessary."""
        try:
            data = toml.load(file_path)
        except FileNotFoundError:
            data = cls._get_default_settings().copy()  # Use defaults if the file is missing

        projects = {p["project_name"]: ProjectSettings(**p) for p in data.pop("projects", [])}
        return cls(universe=UniverseSettings(**data["universe"]), projects=projects)

    @classmethod
    def load_default(cls) -> "ServiceSettings":
        """Load default settings."""
        return cls.load_from_dict(cls._get_default_settings())

    @classmethod
    def load_from_dict(cls, config_data: dict) -> "ServiceSettings":
        """Load configuration from a dictionary."""
        projects = {p["project_name"]: ProjectSettings(**p) for p in config_data.get("projects", [])}
        return cls(universe=UniverseSettings(**config_data["universe"]), projects=projects)

    def save_to_file(self, file_path: str):
        """Save the configuration to a TOML file."""
        data = {
            "universe": self.universe.model_dump(),
            "projects": [p.model_dump() for p in self.projects.values()],
        }
        with open(file_path, "w") as f:
            toml.dump(data, f)

    def dump(self) -> dict:
        """Return the configuration as a dictionary."""
        return {
            "universe": self.universe.model_dump(),
            "projects": [p.model_dump() for p in self.projects.values()],
        }

    # 🔹 NEW: Project management methods

    def add_project_from_default(self, project_name: str) -> bool:
        """
        Add a project using its default configuration.

        Args:
            project_name: Name of the project to add (must exist in DEFAULT_PROJECT_CONFIGS)

        Returns:
            bool: True if project was added, False if it already exists or is unknown
        """
        if project_name in self.projects:
            return False  # Project already exists

        default_configs = self._get_default_project_configs()
        if project_name not in default_configs:
            raise ValueError(
                f"Unknown project '{project_name}'. Available defaults: {list(default_configs.keys())}"
            )

        config = default_configs[project_name].copy()
        self.projects[project_name] = ProjectSettings(**config)
        return True

    def add_project_custom(self, project_config: dict) -> bool:
        """
        Add a project with custom configuration.

        Args:
            project_config: Dictionary containing project configuration

        Returns:
            bool: True if project was added, False if it already exists
        """
        project_settings = ProjectSettings(**project_config)
        project_name = project_settings.project_name

        if project_name in self.projects:
            return False  # Project already exists

        self.projects[project_name] = project_settings
        return True

    def remove_project(self, project_name: str) -> bool:
        """
        Remove a project from the configuration.

        Args:
            project_name: Name of the project to remove

        Returns:
            bool: True if project was removed, False if it didn't exist
        """
        if project_name in self.projects:
            del self.projects[project_name]
            return True
        return False

    def update_project(self, project_name: str, **kwargs) -> bool:
        """
        Update specific fields of an existing project.

        Args:
            project_name: Name of the project to update
            **kwargs: Fields to update

        Returns:
            bool: True if project was updated, False if it doesn't exist
        """
        if project_name not in self.projects:
            return False

        # Get current config and update with new values
        current_config = self.projects[project_name].model_dump()
        current_config.update(kwargs)

        # Recreate the ProjectSettings with updated config
        self.projects[project_name] = ProjectSettings(**current_config)
        return True

    def get_available_default_projects(self) -> list[str]:
        """Return list of available default project names."""
        return list(self._get_default_project_configs().keys())

    def has_project(self, project_name: str) -> bool:
        """Check if a project exists in the current configuration."""
        return project_name in self.projects

    def get_project(self, project_name: str) -> Optional[ProjectSettings]:
        """Get a specific project configuration."""
        return self.projects.get(project_name)


# 🔹 Usage Examples
def main():
    # Create default settings (only cmip6 and cmip6plus)
    settings = ServiceSettings.load_default()
    # ['cmip6', 'cmip6plus']
    print(f"Default projects: {list(settings.projects.keys())}")

    # See what other projects are available to add
    available = settings.get_available_default_projects()
    # ['cmip6', 'cmip6plus', 'input4mip', 'obs4mip']
    print(f"Available default projects: {available}")

    # Add optional projects when needed
    added_input4mip = settings.add_project_from_default("input4mip")
    print(f"Added input4mip: {added_input4mip}")

    added_obs4mip = settings.add_project_from_default("obs4mip")
    print(f"Added obs4mip: {added_obs4mip}")

    print(f"Projects after adding optional ones: {list(settings.projects.keys())}")

    # Remove a project if no longer needed
    removed = settings.remove_project("obs4mip")
    print(f"Removed obs4mip: {removed}")
    print(f"Projects after removal: {list(settings.projects.keys())}")

    # Try to add a custom project
    custom_project = {
        "project_name": "my_custom_project",
        "github_repo": "https://github.com/me/my-project",
        "branch": "develop",
        "local_path": "repos/my_project",
        "db_path": "dbs/my_project.sqlite",
    }
    added_custom = settings.add_project_custom(custom_project)
    print(f"Added custom project: {added_custom}")
    print(f"Final projects: {list(settings.projects.keys())}")

    # Update a project
    updated = settings.update_project("my_custom_project", branch="main", db_path="dbs/updated.sqlite")
    print(f"Updated custom project: {updated}")


if __name__ == "__main__":
    main()
