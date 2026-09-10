from pathlib import Path

from esgvoc.api.data_descriptors.model_level_coordinate import ModelLevelCoordinate
from esgvoc.core.db.connection import DBConnection
from esgvoc.core.db.models.universe import universe_create_db
from esgvoc.core.db.universe_ingestion import get_universe_term, ingest_data_descriptor

_MINI_UNIVERSE = Path(__file__).parent.parent / "fixtures" / "mini_universe"


def test_model_level_formula_and_bounds_factors_remain_distinct(tmp_path):
    database_path = tmp_path / "universe.db"
    universe_create_db(database_path)
    connection = DBConnection(database_path)

    errors = ingest_data_descriptor(
        _MINI_UNIVERSE / "model_level_coordinate",
        connection,
        str(_MINI_UNIVERSE),
    )

    assert errors == 0
    with connection.create_session() as session:
        _, specs = get_universe_term(
            "model_level_coordinate", "alternate_hybrid_sigma", session
        )

    coordinate = ModelLevelCoordinate.model_validate(specs)
    assert [factor.id for factor in coordinate.z_factors] == ["ap", "b", "ps"]
    assert [factor.id for factor in coordinate.z_bounds_factors] == [
        "ap_bnds",
        "b_bnds",
        "ps",
    ]
