from pydantic import BaseModel, Field
from typing import Dict, Optional
from pathlib import Path
import toml


SETTINGS_FILE = Path(__file__).parent / "settings.toml"

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

    @classmethod
    def load_from_file(cls, file_path: str) -> "ServiceSettings":
        data = toml.load(file_path)
        projects = {p['project_name']: ProjectSettings(**p) for p in data.pop('projects', [])}
        return cls(universe=UniverseSettings(**data['universe']), projects=projects)

    def save_to_file(self, file_path: str):
        data = {
            "universe": self.universe.model_dump(),
            "projects": [p.model_dump() for p in self.projects.values()]
        }
        with open(file_path, "w") as f:
            toml.dump(data, f)

def load_settings() -> ServiceSettings:
    """Load the settings from the TOML file."""
    if SETTINGS_FILE.exists():
        return ServiceSettings.load_from_file(str(SETTINGS_FILE))
    else:
        default_settings = ServiceSettings(
        universe=UniverseSettings(
            github_repo="https://github.com/WCRP-CMIP/WCRP-universe",
            branch="esgvoc",
            local_path=".cache/repos/WCRP-universe",
            db_path=".cache/dbs/universe.sqlite"
        ),
        projects={"cmip6plus":ProjectSettings(
                project_name="CMIP6Plus_CVs",
                github_repo="https://github.com/WCRP-CMIP/CMIP6Plus_CVs",
                branch="esgvoc",
                local_path=".cache/repos/CMIP6Plus_CVs",
                db_path=".cache/dbs/cmip6plus.sqlite"
                ),
            
            "cmip6":ProjectSettings(
                project_name="CMIP6_CVs",
                github_repo="https://github.com/WCRP-CMIP/CMIP6_CVs",
                branch="esgvoc",
                local_path=".cache/repos/CMIP6_CVs",
                db_path=".cache/dbs/cmip6.sqlite"
                )
            }

        )
    

        default_settings.save_to_file(str(SETTINGS_FILE))
        return default_settings
