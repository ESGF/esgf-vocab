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
