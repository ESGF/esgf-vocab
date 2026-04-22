"""
DRS tests need installed databases — reuse the session fixture from python_api.
"""
from tests.python_api.conftest import installed_dbs, universe_db, cmip7_db  # noqa: F401
