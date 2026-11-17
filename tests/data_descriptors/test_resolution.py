"""Tests for the resolution data descriptor model."""

import pytest
from pydantic import ValidationError

from esgvoc.api.data_descriptors.resolution import Resolution


def resolution_data(**updates):
    """Return a complete resolution record."""
    record = {
        "id": "50km",
        "type": "resolution",
        "drs_name": "50 km",
        "description": "Resolution of 50 km",
        "name": "50km",
        "value": "50",
        "unit": "km",
    }
    record.update(updates)
    return record


def test_none_accepts_absent_value_and_unit():
    resolution = Resolution(
        id="none",
        type="resolution",
        drs_name="None",
        description="Nominal resolution is not applicable",
        name="none",
    )

    assert resolution.value is None
    assert resolution.unit is None


@pytest.mark.parametrize("field", ["value", "unit"])
def test_ordinary_resolution_requires_value_and_unit(field):
    record = resolution_data()
    del record[field]

    with pytest.raises(ValidationError, match="must define value and unit"):
        Resolution(**record)


@pytest.mark.parametrize(
    ("field", "value"),
    [("value", "none"), ("unit", "none")],
)
def test_none_rejects_value_and_unit(field, value):
    record = resolution_data(
        id="none",
        drs_name="None",
        name="none",
        value=None,
        unit=None,
    )
    record[field] = value

    with pytest.raises(ValidationError, match="must not define value or unit"):
        Resolution(**record)
