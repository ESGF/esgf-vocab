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

    # 🔹 Define default settings
    DEFAULT_SETTINGS : ClassVar[dict]= {
        "universe": {
            "github_repo": "https://github.com/WCRP-CMIP/WCRP-universe",
            "branch": "esgvoc",
            "local_path": "repos/WCRP-universe",
            "db_path": "dbs/universe.sqlite",
        },
        "projects": [
            {
                "project_name": "cmip6",
                "github_repo": "https://github.com/WCRP-CMIP/CMIP6_CVs",
                "branch": "esgvoc",
                "local_path": "repos/CMIP6_CVs",
                "db_path": "dbs/cmip6.sqlite",
            },
            {
                "project_name": "cmip6plus",
                "github_repo": "https://github.com/WCRP-CMIP/CMIP6Plus_CVs",
                "branch": "esgvoc",
                "local_path": "repos/CMIP6Plus_CVs",
                "db_path": "dbs/cmip6plus.sqlite",
            },
        ],
    }

    @classmethod
    def load_from_file(cls, file_path: str) -> "ServiceSettings":
        """Load configuration from a TOML file, falling back to defaults if necessary."""
        try:
            data = toml.load(file_path)
        except FileNotFoundError:
            data = cls.DEFAULT_SETTINGS  # Use defaults if the file is missing

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
            
    def dump(self)->dict:
        data = {
            "universe": self.universe.model_dump(),
            "projects": [p.model_dump() for p in self.projects.values()],
        }
        return data

