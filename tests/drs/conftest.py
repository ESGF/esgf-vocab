"""
DRS tests need installed databases — reuse the session fixture from python_api.
"""
from tests.python_api.conftest import cmip7_db, installed_dbs, universe_db  # noqa: F401
