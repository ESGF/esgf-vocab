"""Tests for the nominal-resolution data descriptor model."""

import pytest
from pydantic import ValidationError

from esgvoc.api.data_descriptors.nominal_resolution import NominalResolution


def nominal_resolution_data(**updates):
    """Return a complete nominal-resolution record."""
    record = {
        "id": "50-km",
        "type": "nominal_resolution",
        "drs_name": "50 km",
        "description": "50 km nominal resolution",
        "magnitude": 50.0,
        "range": [36.0, 72.0],
        "units": "km",
    }
    record.update(updates)
    return record


def test_none_accepts_absent_numerical_metadata():
    resolution = NominalResolution(
        id="none",
        type="nominal_resolution",
        drs_name="None",
        description="Nominal resolution is not applicable",
    )

    assert resolution.magnitude is None
    assert resolution.range is None
    assert resolution.units is None


@pytest.mark.parametrize("field", ["magnitude", "range", "units"])
def test_ordinary_resolution_requires_all_numerical_metadata(field):
    record = nominal_resolution_data()
    del record[field]

    with pytest.raises(ValidationError, match="must define magnitude, range, and units"):
        NominalResolution(**record)


def test_none_rejects_numerical_metadata():
    with pytest.raises(ValidationError, match="must not define numerical metadata"):
        NominalResolution(
            **nominal_resolution_data(
                id="none",
                drs_name="None",
            )
        )
