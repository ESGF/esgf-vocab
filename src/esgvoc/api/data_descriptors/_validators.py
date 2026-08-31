"""
Shared validation helpers for data descriptor models.
"""

from collections.abc import Mapping
from typing import Annotated, Any

from pydantic import AfterValidator


def validate_non_empty_string(value: str) -> str:
    """
    Reject empty and whitespace-only required strings.
    """
    if not value.strip():
        raise ValueError("value cannot be empty")
    return value


NonEmptyString = Annotated[str, AfterValidator(validate_non_empty_string)]


def _is_empty(value: Any) -> bool:
    """
    Return whether a raw descriptor value carries no metadata.
    """
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, tuple, set, dict)):
        return not value
    return False


def validate_standard_or_long_name(data: Any) -> Any:
    """
    Require a standard or long name when descriptor metadata is populated.

    Base-only records are exempt. The ``type`` and JSON-LD context fields are
    structural rather than descriptive and therefore do not count as populated
    descriptor metadata.
    """
    if not isinstance(data, Mapping):
        return data

    long_name = data.get("long_name")
    standard_name = data.get("cf_standard_name")
    if not _is_empty(long_name) or not _is_empty(standard_name):
        return data

    ignored_fields = {
        "id",
        "type",
        "drs_name",
        "description",
        "@context",
        "long_name",
        "cf_standard_name",
    }
    has_populated_metadata = any(not _is_empty(value) for key, value in data.items() if key not in ignored_fields)
    if has_populated_metadata:
        raise ValueError("long_name and cf_standard_name cannot both be empty")

    return data


def validate_valid_range(model: Any) -> Any:
    """
    Ensure that a fully specified valid range is ordered.
    """
    if model.valid_min is not None and model.valid_max is not None and model.valid_min > model.valid_max:
        raise ValueError("valid_min cannot be greater than valid_max")
    return model


def validate_coordinate_data_type(model: Any) -> Any:
    """
    Validate coordinate requests against their declared type and valid range.
    """
    data_type = model.data_type
    values = model.coordinate_values
    bounds = model.coordinate_bounds

    if data_type == "character":
        if model.bounds_required or bounds not in (None, []):
            raise ValueError("character coordinates cannot request bounds")
        if model.tolerance is not None or model.valid_min is not None or model.valid_max is not None:
            raise ValueError("character coordinates cannot define tolerance, valid_min, or valid_max")
        if (
            values is not None
            and not isinstance(values, str)
            and (not isinstance(values, list) or any(not isinstance(value, str) for value in values))
        ):
            raise ValueError("character coordinate values must be a string or a list of strings")
    elif data_type == "integer":
        if values is not None and (not isinstance(values, list) or any(type(value) is not int for value in values)):
            raise ValueError("integer coordinate values must be a list of integers")
        if bounds is not None and any(type(bound) is not int for bound in bounds):
            raise ValueError("integer coordinate bounds must be integers")
    else:
        if values is not None and (
            not isinstance(values, list) or any(type(value) not in (float, int) for value in values)
        ):
            raise ValueError("real and double coordinate values must be numeric")
        if bounds is not None and any(type(bound) not in (float, int) for bound in bounds):
            raise ValueError("real and double coordinate bounds must be numeric")
        if values is not None:
            object.__setattr__(model, "coordinate_values", [float(value) for value in values])
        if bounds is not None:
            object.__setattr__(model, "coordinate_bounds", [float(bound) for bound in bounds])

    if data_type == "character":
        return model

    values = model.coordinate_values
    bounds = model.coordinate_bounds
    if bounds and len(bounds) < 2:
        raise ValueError("coordinate_bounds must contain at least one pair of bounds")
    if isinstance(values, list) and values and bounds and len(bounds) != len(values) + 1:
        raise ValueError("coordinate_bounds must contain m + 1 values for m coordinate_values")

    validate_valid_range(model)

    if isinstance(values, list) and values and bounds:
        for index, value in enumerate(values):
            lower = min(bounds[index], bounds[index + 1])
            upper = max(bounds[index], bounds[index + 1])
            if not lower <= value <= upper:
                raise ValueError("each coordinate value must lie between its corresponding bounds")

    requested = []
    if isinstance(values, list):
        requested.extend(values)
    if bounds:
        requested.extend(bounds)
    if model.valid_min is not None and any(value < model.valid_min for value in requested):
        raise ValueError("requested coordinate values and bounds cannot be below valid_min")
    if model.valid_max is not None and any(value > model.valid_max for value in requested):
        raise ValueError("requested coordinate values and bounds cannot exceed valid_max")

    if model.tolerance is not None:
        if model.tolerance < 0:
            raise ValueError("tolerance cannot be negative")
        has_multiple_values = isinstance(values, list) and len(values) > 1
        has_multiple_bounds = bounds is not None and len(bounds) > 2
        if not has_multiple_values and not has_multiple_bounds:
            raise ValueError("tolerance requires multiple coordinate values or multiple pairs of bounds")

    return model
