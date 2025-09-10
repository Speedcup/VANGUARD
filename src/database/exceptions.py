class DatabaseError(Exception):
    """Base database exception."""

    pass


class NotFoundError(DatabaseError):
    """Raised when a record is not found."""

    pass


class IntegrityViolationError(DatabaseError):
    """Raised when there is a database integrity violation."""

    pass
