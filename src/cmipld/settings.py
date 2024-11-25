import sys
import os
import logging
from pathlib import Path


LOG_HANDLERS = [logging.StreamHandler(sys.stdout)]
LOG_FORMAT = "[%(name)s][%(levelname)s] %(message)s"
LOG_LEVEL = logging.DEBUG

DIRNAME_AND_FILENAME_SEPARATOR = "_"

ROOT_DIR_PATH = Path(os.path.abspath(__file__)).parents[2]
SKIPED_DIRNAMES = {"_src", "_tests", ".git", ".venv", ".pytest_cache"} # DEBUG

PROJECT_SPECS_FILENAME = "project_specs.json"
PROJECT_ID_JSON_KEY = "project_id"
CONTEXT_FILENAME = "000_context.jsonld"
CONTEXT_JSON_KEY = "@context"
DATA_DESCRIPTOR_JSON_KEY = "@id"
TERM_ID_JSON_KEY = 'id'
PATTERN_JSON_KEY = 'pattern'
COMPOSITE_JSON_KEY = 'parts'

logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT, handlers=LOG_HANDLERS)
