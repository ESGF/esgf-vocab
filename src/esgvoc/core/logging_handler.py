import logging.config
from pathlib import Path

logging.config.fileConfig(f"{Path(__file__).parent}/logging.conf", disable_existing_loggers=False)
