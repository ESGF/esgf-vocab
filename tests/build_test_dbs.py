"""
Build the DBs used by the test suite with `esgvoc admin build`, for ESGVOC_TEST_DBS_DIR.

Tests then run against these DBs instead of the ones published in the registry,
e.g. to test esgvoc against CV branches not published yet (see tests/conftest.py).

    # Projects and universe from their esgvoc_dev branch:
    uv run python tests/build_test_dbs.py /tmp/test_dbs

    # Projects from local checkouts (whatever branch is checked out), universe from esgvoc_dev:
    uv run python tests/build_test_dbs.py /tmp/test_dbs --repos-dir ..

    ESGVOC_TEST_DBS_DIR=/tmp/test_dbs uv run pytest
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from esgvoc.admin.builder import DBBuilder
from esgvoc.cli.test_cv import _PROJECT_REPOS, _UNIVERSE_REPO

# Projects needed by the DB fixtures (tests/python_api and tests/schema conftest.py).
TEST_PROJECTS = ["cmip7", "cmip6plus", "cordex-cmip5", "input4mips"]


def _normalized(name: str) -> str:
    return name.lower().replace("-", "_")


def _local_checkout(repos_dir: Path, repo: str) -> Path:
    """The checkout of *repo* (owner/name) in *repos_dir*, whatever its '-'/'_' and case."""
    wanted = _normalized(repo.split("/")[-1])
    for path in repos_dir.iterdir():
        if path.is_dir() and _normalized(path.name) == wanted:
            return path
    raise SystemExit(f"No checkout of {repo} in {repos_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("output_dir", type=Path, help="Directory receiving one <project_id>.db per project.")
    parser.add_argument("--ref", default="esgvoc_dev", help="Branch or tag of the repos (default: esgvoc_dev).")
    parser.add_argument(
        "--repos-dir", type=Path, help="Build the projects from the local checkouts found in this directory."
    )
    parser.add_argument("--projects", nargs="+", default=TEST_PROJECTS, help="Projects to build.")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    builder = DBBuilder(fail_on_missing_links=False)

    print(f"universe <- {_UNIVERSE_REPO}@{args.ref}")
    builder.build_universe(_UNIVERSE_REPO, args.ref, args.output_dir / "universe.db", universe_version=args.ref)

    for project_id in args.projects:
        repo = _PROJECT_REPOS[project_id]
        output = args.output_dir / f"{project_id}.db"
        overrides = {"project_id": project_id, "cv_version": args.ref}
        if args.repos_dir:
            checkout = _local_checkout(args.repos_dir, repo)
            print(f"{project_id} <- {checkout} (universe {_UNIVERSE_REPO}@{args.ref})")
            builder.build_local(checkout, _UNIVERSE_REPO, args.ref, output, manifest_overrides=overrides)
        else:
            print(f"{project_id} <- {repo}@{args.ref}")
            builder.build_remote(repo, args.ref, _UNIVERSE_REPO, args.ref, output, manifest_overrides=overrides)

    print(f"\nDone. Run the tests with: ESGVOC_TEST_DBS_DIR={args.output_dir} uv run pytest")


if __name__ == "__main__":
    sys.exit(main())
