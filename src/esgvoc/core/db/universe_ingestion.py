import logging
from pathlib import Path

import esgvoc.core.constants
from esgvoc.core.data_handler import JsonLdResource
from esgvoc.core.service.data_merger import DataMerger
from sqlmodel import Session, select

import esgvoc.core.db.connection as db
from esgvoc.core.db.connection import read_json_file
from esgvoc.core.db.models.mixins import TermKind
from esgvoc.core.db.models.universe import UDataDescriptor, UTerm, Universe
from esgvoc.core.db.models.universe import universe_create_db
import esgvoc.core.service as service

_LOGGER = logging.getLogger(__name__)

def infer_term_kind(json_specs: dict) -> TermKind:
    if esgvoc.core.constants.PATTERN_JSON_KEY in json_specs:
        return TermKind.PATTERN
    elif esgvoc.core.constants.COMPOSITE_PARTS_JSON_KEY in json_specs:
        return TermKind.COMPOSITE
    else:
        return TermKind.PLAIN


def ingest_universe(universe_repo_dir_path: Path, universe_db_file_path: Path) -> None:
    try:
        connection = db.DBConnection(universe_db_file_path)
    except Exception as e:
        msg = f'Unable to read universe SQLite file at {universe_db_file_path}. Abort.'
        _LOGGER.fatal(msg)
        raise IOError(msg) from e

    for data_descriptor_dir_path in universe_repo_dir_path.iterdir(): 
        if data_descriptor_dir_path.is_dir() and (data_descriptor_dir_path / "000_context.jsonld").exists(): # TODO maybe put that in setting
            try:
                ingest_data_descriptor(data_descriptor_dir_path, connection)
            except Exception as e:
                msg = f'Unexpected error while processing data descriptor {data_descriptor_dir_path}. Abort.'
                _LOGGER.fatal(msg)
                raise RuntimeError(msg) from e
        
def ingest_metadata_universe(connection,git_hash):
    with connection.create_session() as session:
        universe = Universe(git_hash=git_hash)
        session.add(universe)    
        session.commit()

def ingest_data_descriptor(data_descriptor_path: Path,
                           connection: db.DBConnection) -> None:


    data_descriptor_id = data_descriptor_path.name

    context_file_path = data_descriptor_path.joinpath(esgvoc.core.constants.CONTEXT_FILENAME)
    try:
        context = read_json_file(context_file_path)
    except Exception as e:
        msg = f'Unable to read the context file {context_file_path} of data descriptor \
               {data_descriptor_id}. Skip.\n{str(e)}'
        _LOGGER.warning(msg)
        return        

    with connection.create_session() as session:
        data_descriptor = UDataDescriptor(id=data_descriptor_id,
                                         context=context,
                                         term_kind="") # we ll know it only when we ll add a term (hypothesis all term have the same kind in a data_descriptor)
        term_kind_dd = None

        _LOGGER.debug(f"add data_descriptor : {data_descriptor_id}")
        for term_file_path in data_descriptor_path.iterdir():
            _LOGGER.debug(f"found term path : {term_file_path}, {term_file_path.suffix}")
            if term_file_path.is_file() and term_file_path.suffix == ".json":
                
                try:
                    json_specs=DataMerger(data=JsonLdResource(uri=str(term_file_path)),
                                          locally_available={"https://espri-mod.github.io/mip-cmor-tables":service.current_state.universe.local_path}).merge_linked_json()[-1]
                    term_kind = infer_term_kind(json_specs)
                    term_id = json_specs["id"]

                    if term_kind_dd is None:
                        term_kind_dd = term_kind

                except Exception as e:
                    _LOGGER.warning(f'Unable to read term {term_file_path} for data descriptor {data_descriptor_path}. Skip.\n{str(e)}')
                    continue
                if term_id and json_specs and data_descriptor and term_kind:
                    _LOGGER.debug("adding {term_id}")
                    term = UTerm(
                        id=term_id,
                        specs=json_specs,
                        data_descriptor=data_descriptor,
                        kind=term_kind,
                    )
                    session.add(term)
        if term_kind_dd is not None:
            data_descriptor.term_kind = term_kind_dd
        session.add(data_descriptor)
        session.commit()

def get_universe_term(data_descriptor_id: str,
                     term_id: str,
                     universe_db_session: Session) -> tuple[TermKind, dict]:
    statement = (
        select(UTerm)
        .join(UDataDescriptor)
        .where(UDataDescriptor.id == data_descriptor_id, UTerm.id == term_id)
    )
    results = universe_db_session.exec(statement)
    term = results.one()
    return term.kind, term.specs


if __name__ == "__main__":
    #ingest_universe(db.UNIVERSE_DIR_PATH, db.UNIVERSE_DB_FILE_PATH)
    import os
    root_dir = Path(str(os.getcwd())).parent.parent
    print(root_dir)
    universe_create_db(root_dir /  Path(".cache/dbs/universe.sqlite"))
    ingest_universe(root_dir / Path(".cache/repos/mip-cmor-tables"),root_dir /  Path(".cache/dbs/universe.sqlite"))
