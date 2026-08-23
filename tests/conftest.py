import pytest

import chic_finder.db


@pytest.fixture(autouse=True)
def _reset_db_pool():
    chic_finder.db._pool = None
    yield
    chic_finder.db._pool = None
