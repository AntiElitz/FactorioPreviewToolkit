class UserFacingError(Exception):
    """
    An error whose message is written for the person using the toolkit.

    When a run fails, the toolkit shows str(exception) in a popup - so for anything a user
    can actually fix (a wrong setting, a server that refuses a login), that text is what
    they read. It should name what went wrong, which setting is involved, and what to
    change. The technical cause is kept as the exception's cause, so the log still has it.
    """
