class EsgvocException(Exception):
    """
    Class base of all ESGVOC errors.
    """
    pass


class EsgvocNotFoundError(EsgvocException):
    """
    Represents the not found errors.
    """
    pass


class EsgvocValueError(EsgvocException):
    """
    Represents value errors.
    """
    pass


class EsgvocDbError(EsgvocException):
    """
    Represents errors relative to data base management.
    """
    pass


class EsgvocNotImplementedError(EsgvocException):
    """
    Represents not implemented errors.
    """
    pass


class EsgvocMissingLinksError(EsgvocException):
    """
    Error for unresolved @id references during database population.

    Can be raised via MissingLinksTracker.check_and_raise() when one or more
    @id references could not be resolved to actual terms.
    """

    def __init__(self, missing_links: list):
        self.missing_links = missing_links
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        lines = [
            f"Found {len(self.missing_links)} unresolved @id reference(s) during ingestion:",
            "",
        ]
        for link in self.missing_links:
            lines.append(f"  - Context: {link.ingestion_context}")
            lines.append(f"    Term: {link.current_term}")
            if link.property_name:
                lines.append(f"    Property: {link.property_name}")
            lines.append(f"    Missing ID: {link.string_value}")
            lines.append(f"    Expected URI: {link.expected_uri}")
            lines.append(f"    Local path tried: {link.local_path}")
            lines.append("")
        return "\n".join(lines)
