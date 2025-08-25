from typing import ClassVar, Dict, Optional

import toml
from pydantic import BaseModel, Field


class ProjectSettings(BaseModel):
    project_name: str
    github_repo: str
    branch: Optional[str] = "main"
    local_path: Optional[str] = None
    db_path: Optional[str] = None


class UniverseSettings(BaseModel):
    github_repo: str
    branch: Optional[str] = None
    local_path: Optional[str] = None
    db_path: Optional[str] = None


class ServiceSettings(BaseModel):
    universe: UniverseSettings
    projects: Dict[str, ProjectSettings] = Field(default_factory=dict)

    # 🔹 Centralized default project configurations
    DEFAULT_PROJECT_CONFIGS: ClassVar[Dict[str, dict]] = {
        "cmip6": {
            "project_name": "cmip6",
            "github_repo": "https://github.com/WCRP-CMIP/CMIP6_CVs",
            "branch": "esgvoc",
            "local_path": "repos/CMIP6_CVs",
            "db_path": "dbs/cmip6.sqlite",
        },
        "cmip6plus": {
            "project_name": "cmip6plus",
            "github_repo": "https://github.com/WCRP-CMIP/CMIP6Plus_CVs",
            "branch": "esgvoc",
            "local_path": "repos/CMIP6Plus_CVs",
            "db_path": "dbs/cmip6plus.sqlite",
        },
        "input4mip": {
            "project_name": "input4mip",
            "github_repo": "https://github.com/PCMDI/input4MIPs_CVs",
            "branch": "esgvoc",
            "local_path": "repos/Input4MIP_CVs",
            "db_path": "dbs/input4mips.sqlite",
        },
        "obs4mip": {
            "project_name": "obs4mip",
            "github_repo": "https://github.com/ltroussellier/obs4MIPs_CVs",
            "branch": "main",
            "local_path": "repos/obs4MIPs_CVs",
            "db_path": "dbs/obs4mips.sqlite",
        },
        "cordex-cmip6": {
            "project_name": "cordex-cmip6",
            "github_repo": "https://github.com/WCRP-CORDEX/cordex-cmip6-cv",
            "branch": "esgvoc",
            "local_path": "repos/cordex-cmip6-cv",
            "db_path": "dbs/cordex-cmip6.sqlite",
        },
    }

    # 🔹 Default settings - only includes cmip6 and cmip6plus by default
    DEFAULT_SETTINGS: ClassVar[dict] = {
        "universe": {
            "github_repo": "https://github.com/WCRP-CMIP/WCRP-universe",
            "branch": "esgvoc",
            "local_path": "repos/WCRP-universe",
            "db_path": "dbs/universe.sqlite",
        },
        "projects": [
            DEFAULT_PROJECT_CONFIGS["cmip6"],
            DEFAULT_PROJECT_CONFIGS["cmip6plus"],
        ],
    }

    @classmethod
    def load_from_file(cls, file_path: str) -> "ServiceSettings":
        """Load configuration from a TOML file, falling back to defaults if necessary."""
        try:
            data = toml.load(file_path)
        except FileNotFoundError:
            data = cls.DEFAULT_SETTINGS.copy()  # Use defaults if the file is missing

        projects = {p["project_name"]: ProjectSettings(**p) for p in data.pop("projects", [])}
        return cls(universe=UniverseSettings(**data["universe"]), projects=projects)

    @classmethod
    def load_default(cls) -> "ServiceSettings":
        """Load default settings."""
        return cls.load_from_dict(cls.DEFAULT_SETTINGS)

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

        if project_name not in self.DEFAULT_PROJECT_CONFIGS:
            raise ValueError(
                f"Unknown project '{project_name}'. Available defaults: {list(self.DEFAULT_PROJECT_CONFIGS.keys())}"
            )

        config = self.DEFAULT_PROJECT_CONFIGS[project_name].copy()
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
        return list(self.DEFAULT_PROJECT_CONFIGS.keys())

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
    print(f"Default projects: {list(settings.projects.keys())}")  # ['cmip6', 'cmip6plus']

    # See what other projects are available to add
    available = settings.get_available_default_projects()
    print(f"Available default projects: {available}")  # ['cmip6', 'cmip6plus', 'input4mip', 'obs4mip']

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
