"""Create an isolated review checkout from two full commit SHAs."""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

COMMIT_SHA = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
GIT_LOCATION_VARIABLES = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_COMMON_DIR",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
)


def git(directory: Path, *arguments: str) -> str:
    environment = os.environ.copy()
    for name in GIT_LOCATION_VARIABLES:
        environment.pop(name, None)
    environment["GIT_LFS_SKIP_SMUDGE"] = "1"
    result = subprocess.run(
        ["git", "-C", str(directory), *arguments],
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def commit_sha(value: str) -> str:
    if COMMIT_SHA.fullmatch(value) is None:
        raise argparse.ArgumentTypeError("expected a full lowercase commit SHA")
    return value


def prepare_review(repo: Path, base: str, head: str) -> dict[str, str]:
    repo = repo.resolve(strict=True)
    for sha in (base, head):
        commit_sha(sha)
        if git(repo, "cat-file", "-t", sha) != "commit":
            raise ValueError(f"{sha} is not a commit")

    object_format = git(repo, "rev-parse", "--show-object-format")
    snapshot = Path(tempfile.mkdtemp(prefix="tao-independent-review-"))
    try:
        git(snapshot, "init", "--quiet", f"--object-format={object_format}")
        git(snapshot, "config", "core.hooksPath", str(snapshot / "disabled-hooks"))
        git(snapshot, "config", "core.autocrlf", "false")
        git(snapshot, "config", "core.fsmonitor", "false")
        git(snapshot, "config", "filter.lfs.smudge", "")
        git(snapshot, "config", "filter.lfs.process", "")
        git(snapshot, "config", "filter.lfs.required", "false")
        git(snapshot, "fetch", "--quiet", "--no-tags", str(repo), base, head)
        git(snapshot, "checkout", "--quiet", "--detach", head)
        if git(snapshot, "rev-parse", "HEAD") != head:
            raise ValueError("snapshot HEAD does not match the requested commit")
    except (OSError, subprocess.CalledProcessError, ValueError):
        shutil.rmtree(snapshot)
        raise

    return {"directory": str(snapshot), "base_sha": base, "head_sha": head}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--base", required=True, type=commit_sha)
    parser.add_argument("--head", required=True, type=commit_sha)
    arguments = parser.parse_args()
    try:
        snapshot = prepare_review(arguments.repo, arguments.base, arguments.head)
    except subprocess.CalledProcessError as error:
        print(f"prepare_review: {error.stderr.strip()}", file=sys.stderr)
        return 1
    except (OSError, ValueError) as error:
        print(f"prepare_review: {error}", file=sys.stderr)
        return 1
    print(json.dumps(snapshot))
    return 0


if __name__ == "__main__":
    sys.exit(main())
