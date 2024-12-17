import logging
import os
from pathlib import Path
from typing import Optional
from esgvoc.core.repo_fetcher import RepoFetcher
from esgvoc.core.service.settings import UniverseSettings, ProjectSettings, ServiceSettings
from esgvoc.core.db._utils import DBConnection
from esgvoc.core.db.models.project import Project
from esgvoc.core.db.models.universe import Universe 
from rich.table import Table
from sqlalchemy.exc import NoResultFound
from sqlmodel import select

logger = logging.getLogger(__name__)

class BaseState:
    def __init__(self, github_repo: str, branch: str = "main", local_path: Optional[str] = None, db_path: Optional[str] = None):
    
        self.github_repo = github_repo
        self.branch = branch
        self.local_path = local_path
        self.rf = RepoFetcher()
        
        self.db_path = db_path
        self.db_connection:DBConnection|None = None

        self.github_version = None
        self.local_version = None
        self.db_version = None

    
    def fetch_version_local(self):
         if self.local_path:
            try:
                self.local_version = self.rf.get_local_repo_version(self.local_path, self.branch)
                logger.debug(f"Local repo commit: {self.local_version}")
            except Exception as e:
                logger.exception(f"Failed to fetch local repo version: {e}")
    def fetch_version_remote(self):
        if self.github_repo:
            owner = None
            repo = None
            try:
                owner, repo = self.github_repo.lstrip("https://github.com/").split("/")
                self.github_version = self.rf.get_github_version(owner, repo, self.branch) # This one use the github api, TODO maybe change that ? 
                logger.debug(f"Latest GitHub commit: {self.github_version}")
            except Exception as e:
                logger.exception(f"Failed to fetch GitHub version: {e} ,for {self.github_repo},owner : {owner}, repo : {repo},branch : {self.branch}")

    def fetch_versions(self):
        self.fetch_version_remote()
        self.fetch_version_local()
              
    def check_sync_status(self):
        self.fetch_versions()
        return {
            "github_sync": self.github_version == self.local_version if self.github_version and self.local_version else None,
            "local_db_sync": self.local_version == self.db_version if self.local_version and self.db_version else None,
            "github_db_sync": self.github_version == self.db_version if self.github_version and self.db_version else None
        }

    def sync(self):
        if self.github_version and self.github_version != self.local_version:
            owner, repo = self.github_repo.lstrip("https://github.com/").split("/")
            self.rf.clone_repository(owner, repo, self.branch)
            #self.fetch_versions()

        if self.local_version != self.db_version:
            # delete and redo the DB? 
            pass

class StateUniverse(BaseState):
    def __init__(self, settings: UniverseSettings):
        super().__init__(**settings.model_dump())

    def fetch_versions(self):
        super().fetch_versions()
        if self.db_path:
            if not os.path.exists(self.db_path):
                self.db_version = None
            else:
                self.db_connection =DBConnection(db_file_path= Path(self.db_path)) 
                with self.db_connection.create_session() as session:
                    self.db_version = session.exec(select(Universe.git_hash)).one()
        else:
            self.db_version = None


class StateProject(BaseState):
    def __init__(self, settings: ProjectSettings):
        mdict = settings.model_dump()
        self.project_name = mdict.pop("project_name")
        super().__init__(**mdict)

    def fetch_versions(self):
        super().fetch_versions()
        self.db_version = None
        if self.db_path:
            if not os.path.exists(self.db_path):
                self.db_version = None
            else:
                try :
                    self.db_connection =DBConnection(db_file_path= Path(self.db_path)) 
                    with self.db_connection.create_session() as session:
                        self.db_version = session.exec(select(Project.git_hash)).one()
                except NoResultFound :
                    logger.debug(f"Unable to find git_hash in project {self.project_name}")
                except Exception as e:
                    logger.debug(f"Unable to find git_has in project {self.project_name} cause {e}" )

class StateService:
    def __init__(self, service_settings: ServiceSettings):
        self.universe = StateUniverse(service_settings.universe)
        self.projects = {name: StateProject(proj) for name, proj in service_settings.projects.items()}
        self.connect_db()

    def get_state_summary(self):
        universe_status = self.universe.check_sync_status()
        project_statuses = {name: proj.check_sync_status() for name, proj in self.projects.items()}
        return {"universe": universe_status, "projects": project_statuses}

    def connect_db(self):
        self.universe.fetch_versions()
        for _,proj_state in self.projects.items():
            proj_state.fetch_versions()

    def synchronize_all(self):
        self.universe.sync()
        for project in self.projects.values():
            project.sync()
    def table(self):
        table = Table(show_header=False, show_lines=True)
        table.add_row("","Remote github repo","Local repository","Cache Database")
        table.add_row("Universe path",self.universe.github_repo,self.universe.local_path,self.universe.db_path)
        table.add_row("Version",self.universe.github_version,self.universe.local_version,self.universe.db_version)
        for proj_name,proj in self.projects.items():

            table.add_row("","Remote github repo","Local repository","Cache Database")
            table.add_row(f"{proj_name} path",proj.github_repo,proj.local_path,proj.db_path)
            table.add_row("Version",proj.github_version,proj.local_version,proj.db_version)
        return table

if __name__ == "__main__":
    # Load settings from file
    service_settings = ServiceSettings.load_from_file("src/esgvoc/core/service/settings.toml")
    
    # Initialize StateService
    state_service = StateService(service_settings)
    state_service.get_state_summary()

    # Synchronize all
    state_service.synchronize_all()

    # pprint(state_service.universe.github_version)
    # pprint(state_service.universe.local_version)
    # pprint(state_service.universe.db_version)

    
    # Check for differences
    #pprint(state_service.find_version_differences())
