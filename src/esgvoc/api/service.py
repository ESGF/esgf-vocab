from esgvoc.core.service import current_state


def install(fail_on_missing_links: bool = False) -> int:
    """Synchronize all repositories and databases.

    This function clones/updates the remote repositories and rebuilds
    the local database caches as needed.

    Args:
        fail_on_missing_links: If True, track missing @id references and
            return -1 if any were found. Defaults to False.

    Returns:
        0 if successful, -1 if missing links were found (when fail_on_missing_links=True).
    """
    result = current_state.synchronize_all(fail_on_missing_links=fail_on_missing_links)
    current_state.fetch_versions()
    current_state.connect_db()
    return result
