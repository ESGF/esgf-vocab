"""
esgvoc.api.service — legacy shim

The old `install()` function (which cloned repos and built DBs via the dev-tier
config system) has been removed. Use `esgvoc use <project>@<version>` instead
to download and activate a pre-built database.
"""


def install(*args, **kwargs):
    raise NotImplementedError(
        "'install()' has been removed. "
        "Use 'esgvoc use <project>@<version>' (CLI) or "
        "download a pre-built database via DBFetcher."
    )
