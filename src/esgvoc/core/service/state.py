import logging
import os
from pathlib import Path
from typing import Optional

from rich.table import Table
from sqlalchemy.exc import NoResultFound
from sqlmodel import select

from esgvoc.core.db.connection import DBConnection
from esgvoc.core.db.models.project import Project
from esgvoc.core.db.models.universe import Universe
from esgvoc.core.repo_fetcher import RepoFetcher
from esgvoc.core.service.configuration.setting import ProjectSettings, ServiceSettings, UniverseSettings

logger = logging.getLogger(__name__)


class BaseState:
    def __init__(
        self, github_repo: str, branch: str = "main", local_path: Optional[str] = None, db_path: Optional[str] = None, offline_mode: bool = False
    ):
        from esgvoc.core.service import config_manager

        self.base_dir = config_manager.data_config_dir  # needed for repofetcher

        self.github_repo: str = github_repo
        self.branch: str = branch
        self.offline_mode: bool = offline_mode
        # False if we dont have internet and some other cases
        # In offline mode, disable github access from the start
        self.github_access: bool = not offline_mode
        self.github_version: str | None = None

        self.local_path: str | None = local_path
        self.local_access: bool = True  # False if we dont have cloned the remote repo yet
        self.local_version: str | None = None

        self.db_path: str | None = db_path
        self.db_access: bool = True  # False if we cant access the db for some reason
        self.db_version: str | None = None

        self.rf = RepoFetcher(local_path=str(self.base_dir), offline_mode=offline_mode)
        self.db_connection: DBConnection | None = None
        self.db_sqlmodel: Universe | Project | None = None


    def fetch_version_local(self):
        if self.local_path:
            try:
                self.local_version = self.rf.get_local_repo_version(self.local_path, self.branch)
                logger.debug(f"Local repo commit: {self.local_version}")
                self.local_access = True
            except Exception as e:
                logger.exception(f"Failed to fetch local repo version: {e}")
                self.local_access = False

    def fetch_version_remote(self):
        if self.offline_mode:
            logger.debug("Skipping remote version fetch due to offline mode")
            self.github_access = False
            return

        if self.github_repo:
            owner = None
            repo = None
            try:
                owner, repo = self.github_repo.removeprefix("https://github.com/").split("/")
                self.github_version = self.rf.get_github_version(owner, repo, self.branch)
                self.github_access = True
                logger.debug(f"Latest GitHub commit: {self.github_version}")
            except IndexError as e:
                self.github_access = False
            except Exception as e:
                logger.exception(
                    f"Failed to fetch GitHub version: {e} ,for {self.github_repo},owner : {owner}, repo : {repo},branch : {self.branch}"
                )
                self.github_access = False

            if self.github_version is None:
                self.github_access = False

    def connect_db(self):
        if self.db_path:
            if not os.path.exists(self.db_path):
                self.db_access = False
            else:
                self.db_connection = DBConnection(db_file_path=Path(self.db_path))

    def fetch_version_db(self):
        if self.db_path:
            if not os.path.exists(self.db_path):
                self.db_version = None
                self.db_access = False
            else:
                try:
                    with self.db_connection.create_session() as session:
                        self.db_version = session.exec(select(self.db_sqlmodel.git_hash)).one()
                        self.db_access = True
                except NoResultFound:
                    logger.debug(f"Unable to find git_hash in {self.db_path}")
                except Exception as e:
                    logger.debug(f"Unable to find git_has in {self.db_path} cause {e}")

        else:
            self.db_version = None
            self.db_access = False

    def fetch_versions(self):
        if self.github_access:
            self.fetch_version_remote()
        self.fetch_version_local()
        self.fetch_version_db()

    def check_sync_status(self):
        self.fetch_versions()
        return {
            "github": self.github_version if self.github_version else None,
            "local": self.local_version if self.local_version else None,
            "db": self.db_version if self.db_version else None,
            "github_local_sync": self.github_version == self.local_version
            if self.github_access and self.github_version and self.local_version
            else False,
            "local_db_sync": self.local_version == self.db_version
            if self.local_access and self.local_version
            else False,
            "github_db_sync": self.github_version == self.db_version
            if self.github_access and self.github_version
            else False,
        }

    def clone_remote(self, force_clean=False):
        if self.offline_mode:
            logger.warning("Cannot clone remote repository in offline mode")
            return

        # If force_clean is True or if local repo exists and we're handling divergence,
        # remove the existing local repository to ensure clean state
        if force_clean and self.local_path and os.path.exists(self.local_path):
            print(f"Removing existing local repository: {self.local_path}")
            import shutil
            shutil.rmtree(self.local_path)

        owner, repo = self.github_repo.removeprefix("https://github.com/").split("/")
        # TODO add destination "local_path" in clone_repo, done in a wierd way Improve that:
        self.rf.clone_repository(owner, repo, self.branch, self.local_path)
        self.fetch_version_local()

    def build_db(self):
        from esgvoc.core.db.models.project import project_create_db
        from esgvoc.core.db.models.universe import universe_create_db
        from esgvoc.core.db.project_ingestion import ingest_project
        from esgvoc.core.db.universe_ingestion import ingest_metadata_universe, ingest_universe

        if self.db_path:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
            else:
                os.makedirs(Path(self.db_path).parent, exist_ok=True)

            if self.db_sqlmodel == Universe:  # Ugly
                print("Building Universe DB from ", self.local_path)
                universe_create_db(Path(self.db_path))
                self.db_connection = DBConnection(db_file_path=Path(self.db_path))

                ingest_metadata_universe(self.db_connection, self.local_version)
                print("Filling Universe DB")
                if self.local_path:
                    ingest_universe(Path(self.local_path), Path(self.db_path))

            elif self.db_sqlmodel == Project:
                print("Building Project DB from ", self.local_path)
                project_create_db(Path(self.db_path))
                print("Filling project DB")
                if self.local_path and self.local_version:
                    ingest_project(Path(self.local_path), Path(self.db_path), self.local_version)
        self.fetch_version_db()

    def sync(self):
        summary = self.check_sync_status()
        updated = False

        if self.offline_mode:
            print("Running in offline mode - only using local repositories and databases")
            if self.local_access:
                if not summary["local_db_sync"] and summary["local_db_sync"] is not None:
                    self.build_db()
                    updated = True
                else:
                    print("Cache db is uptodate from local repository")
            elif not self.db_access:  # it can happen if the db is created but not filled
                if self.local_path and os.path.exists(self.local_path):
                    self.build_db()
                    updated = True
                else:
                    print(f"No local repository found at {self.local_path} - cannot sync in offline mode")
            else:
                print("Nothing to sync in offline mode - local repository and database are up to date")
            return updated

        # Online sync logic with offline-to-online transition detection
        if (
            self.github_access
            and summary["github_db_sync"] is None
            and summary["local_db_sync"] is None
            and summary["github_local_sync"] is None
        ):
            self.clone_remote()
            self.build_db()
            updated = True
        elif self.github_access and not summary["github_db_sync"]:
            if not summary["local_db_sync"] and summary["local_db_sync"] is not None:
                self.clone_remote()
                self.build_db()
                updated = True
            elif not summary["github_local_sync"]:
                # Critical fix: when local and remote diverge in online mode,
                # prioritize remote truth by completely removing local repo and re-cloning
                print(f"Local and remote repositories have diverged (local: {summary['local'][:8] if summary['local'] else 'N/A'}, remote: {summary['github'][:8] if summary['github'] else 'N/A'})")
                print("Prioritizing remote repository truth - removing local repository and re-cloning from GitHub...")
                self.clone_remote(force_clean=True)
                self.build_db()
                updated = True
            else:  # can be simply build in root and clone if neccessary
                self.build_db()
                updated = True
        elif self.local_access:
            if not summary["local_db_sync"] and summary["local_db_sync"] is not None:
                self.build_db()
                updated = True
            else:
                print("Cache db is uptodate from local repository")
        elif not self.db_access:  # it can happen if the db is created but not filled
            self.build_db()
            updated = True
        else:
            print("Nothing to install, everything up to date")
            print("Try 'esgvoc status' for more details")
        return updated


class StateUniverse(BaseState):
    def __init__(self, settings: UniverseSettings):
        params = settings.model_dump()
        params['local_path'] = settings.get_absolute_local_path()
        params['db_path'] = settings.get_absolute_db_path()
        super().__init__(**params)
        self.db_sqlmodel = Universe


class StateProject(BaseState):
    def __init__(self, settings: ProjectSettings):
        mdict = settings.model_dump()
        self.project_name = mdict.pop("project_name")
        mdict['local_path'] = settings.get_absolute_local_path()
        mdict['db_path'] = settings.get_absolute_db_path()
        super().__init__(**mdict)
        self.db_sqlmodel = Project


class StateService:
    def __init__(self, service_settings: ServiceSettings):
        self.universe = StateUniverse(service_settings.universe)
        self.projects = {name: StateProject(proj) for name, proj in service_settings.projects.items()}
        self.connect_db()

    def get_state_summary(self):
        universe_status = self.universe.check_sync_status()
        project_statuses = {name: proj.check_sync_status() for name, proj in self.projects.items()}
        return {"universe": universe_status, "projects": project_statuses}

    def fetch_versions(self):
        self.universe.fetch_versions()
        for _, proj_state in self.projects.items():
            proj_state.fetch_versions()

    def connect_db(self):
        self.universe.connect_db()
        for _, proj_state in self.projects.items():
            proj_state.connect_db()

    def synchronize_all(self):
        print("sync universe")
        if self.universe.offline_mode:
            print("Universe is in offline mode")
        universe_updated = self.universe.sync()
        print("sync projects")
        for project_name, project in self.projects.items():
            if project.offline_mode:
                print(f"Project {project_name} is in offline mode")
            project_updated = project.sync()
            if universe_updated and not project_updated:
                project.build_db()
        self.connect_db()

    def table(self):
        table = Table(show_header=False, show_lines=True)
        table.add_row("", "Remote github repo", "Local repository", "Cache Database")
        table.add_row("Universe path", self.universe.github_repo, self.universe.local_path, self.universe.db_path)
        table.add_row("Version", self.universe.github_version, self.universe.local_version, self.universe.db_version)
        for proj_name, proj in self.projects.items():
            # table.add_row("","Remote github repo","Local repository","Cache Database")
            table.add_row(f"{proj_name} path", proj.github_repo, proj.local_path, proj.db_path)
            table.add_row("Version", proj.github_version, proj.local_version, proj.db_version)
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
    # pprint(state_service.find_version_differences())
