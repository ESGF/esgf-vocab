import logging
import re

import typer

KEY_PATTERN = r"^[a-zA-Z0-9\/_-]*:[a-zA-Z0-9\/_-]*:[a-zA-Z0-9\/_.-]*$"

_LOGGER = logging.getLogger(__name__)


def validate_key_format(key: str):
    """Validate if the key matches the XXXX:YYYY:ZZZZ format."""
    if not re.match(KEY_PATTERN, key):
        raise typer.BadParameter(f"Invalid key format: {key}. Must be XXXX:YYYY:ZZZZ.")
    return key.split(":")


def handle_unknown(x: str | None, y: str | None, z: str | None):
    _LOGGER.warning("Unknown key components: X=%s, Y=%s, Z=%s", x, y, z)
