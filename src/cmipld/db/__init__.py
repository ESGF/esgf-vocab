import json
from pathlib import Path

from sqlalchemy import Engine
from sqlmodel import Session, create_engine

def read_json_file(json_file_path: Path) -> dict:
    return json.loads(json_file_path.read_text())

# Singleton for SQLModel engines.
# Not thread safe.
class DBConnection:
    SQLITE_URL_PREFIX = 'sqlite://'
    _ENGINES: dict[Path, Engine] = dict()

    def __init__(self, db_file_path: Path, name: str|None = None, echo: bool = False) -> None:
        if db_file_path in DBConnection._ENGINES:
            self.engine = DBConnection._ENGINES[db_file_path]
        else:
            self.engine = create_engine(f'{DBConnection.SQLITE_URL_PREFIX}/{str(db_file_path)}', echo=echo)
            DBConnection._ENGINES[db_file_path] = self.engine
        self.name = name
        self.file_path = db_file_path

    def set_echo(self, echo: bool) -> None:
        self.engine.echo = echo

    def get_engine(self) -> Engine:
        return self.engine

    def create_session(self) -> Session:
        return Session(self.engine)

    def get_name(self) -> str|None:
        return self.name
    
    def get_file_path(self) -> Path:
        return self.file_path


############## DEBUG ##############
# TODO: to be deleted.
# The following instructions are only temporary as long as a complete data management will be implemented.

from cmipld.settings import ROOT_DIR_PATH  # noqa

UNIVERSE_DIR_NAME = '.cache/repos/mip-cmor-tables'
CMIP6PLUS_DIR_NAME = '.cache/repos/CMIP6Plus_CVs'

UNIVERSE_DIR_PATH = ROOT_DIR_PATH.parent.joinpath(UNIVERSE_DIR_NAME)
CMIP6PLUS_DIR_PATH = ROOT_DIR_PATH.parent.joinpath(CMIP6PLUS_DIR_NAME)

UNIVERSE_DB_FILE_PATH = Path('.cache/dbs/universe.sqlite')
CMIP6PLUS_DB_FILE_PATH = Path('.cache/dbs/cmip6plus.sqlite')
###################################
