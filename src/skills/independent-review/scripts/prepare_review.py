"""Create an isolated checkout for a pushed commit and its review baseline."""

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


def git(directory: Path, *arguments: str, input_text: str | None = None) -> str:
    environment = {
        name: value for name, value in os.environ.items() if not name.startswith("GIT_")
    }
    environment.update(
        GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_ATTR_NOSYSTEM="1",
        GIT_LFS_SKIP_SMUDGE="1",
    )
    result = subprocess.run(
        ["git", "-c", "protocol.version=2", "-C", str(directory), *arguments],
        env=environment,
        input=input_text,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def commit_sha(value: str) -> str:
    if COMMIT_SHA.fullmatch(value) is None:
        raise argparse.ArgumentTypeError("expected a full lowercase commit SHA")
    return value


def prepare_review(repo: Path, base: str | None, head: str) -> dict[str, str]:
    repo = repo.resolve(strict=True)
    repo = Path(git(repo, "rev-parse", "--absolute-git-dir"))
    commits = [head] if base is None else [base, head]
    for sha in commits:
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
        git(snapshot, "fetch", "--quiet", "--no-tags", str(repo), *commits)
        git(snapshot, "checkout", "--quiet", "--detach", head)
        if git(snapshot, "rev-parse", "HEAD") != head:
            raise ValueError("snapshot HEAD does not match the requested commit")
        base_sha = base if base is not None else git(snapshot, "mktree", input_text="")
    except (OSError, subprocess.CalledProcessError, ValueError):
        shutil.rmtree(snapshot)
        raise

    return {
        "directory": str(snapshot),
        "base_sha": base_sha,
        "head_sha": head,
        "baseline_kind": "commit" if base is not None else "empty-tree",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    baseline = parser.add_mutually_exclusive_group(required=True)
    baseline.add_argument("--base", type=commit_sha)
    baseline.add_argument(
        "--root", action="store_true", help="review from an empty tree"
    )
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
