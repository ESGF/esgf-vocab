from esgvoc.core.service import current_state


def install() -> None:
    """Synchronize all repositories and databases.

    This function clones/updates the remote repositories and rebuilds
    the local database caches as needed.
    """
    current_state.synchronize_all()
    current_state.fetch_versions()
    current_state.connect_db()
