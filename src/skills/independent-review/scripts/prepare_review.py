"""Create an isolated checkout for a pushed commit and its review baseline."""

from __future__ import annotations

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
MINIMUM_GIT_VERSION = (2, 46)
MINIMUM_PYTHON_VERSION = (3, 11)


def git_environment(*, isolate_config: bool = True) -> dict[str, str]:
    environment = {
        name: value for name, value in os.environ.items() if not name.startswith("GIT_")
    }
    environment.update(
        GIT_ATTR_NOSYSTEM="1", GIT_LFS_SKIP_SMUDGE="1", GIT_NO_LAZY_FETCH="1"
    )
    if isolate_config:
        environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    return environment


def git(
    directory: Path,
    *arguments: str,
    input_text: str | None = None,
    safe_directories: tuple[str, ...] = (),
) -> str:
    command = [
        "git",
        "-c",
        "protocol.version=2",
        "-c",
        f"core.hooksPath={os.devnull}",
        "-c",
        f"core.attributesFile={os.devnull}",
        "-c",
        "core.fsmonitor=false",
    ]
    for trusted in safe_directories:
        command.extend(("-c", f"safe.directory={trusted}"))
    result = subprocess.run(
        [*command, "-C", str(directory), *arguments],
        env=git_environment(),
        input=input_text,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def trusted_directories(repo: Path) -> tuple[str, ...]:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "config",
            "--includes",
            "--null",
            "--show-scope",
            "--get-all",
            "safe.directory",
        ],
        env=git_environment(isolate_config=False),
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode == 1:
        return ()
    result.check_returncode()
    fields = result.stdout.removesuffix("\0").split("\0")
    return tuple(
        value
        for scope, value in zip(fields[::2], fields[1::2], strict=True)
        if scope in ("system", "global")
    )


def commit_sha(value: str) -> str:
    if COMMIT_SHA.fullmatch(value) is None:
        raise ValueError("expected a full lowercase commit SHA")
    return value


def prepare_review(
    repo: Path, base: str | None, head: str, *, snapshot_parent: Path | None = None
) -> dict[str, str]:
    if sys.version_info[:2] < MINIMUM_PYTHON_VERSION:
        raise ValueError("Python 3.11+ is required")
    commits = [head] if base is None else [base, head]
    for sha in commits:
        commit_sha(sha)
    repo = repo.resolve(strict=True)
    version = git(repo, "--version")
    match = re.match(r"git version (\d+)\.(\d+)", version)
    if match is None or tuple(map(int, match.groups())) < MINIMUM_GIT_VERSION:
        raise ValueError(f"Git 2.46+ is required; found {version}")
    repo = Path(
        git(
            repo,
            "rev-parse",
            "--absolute-git-dir",
            safe_directories=trusted_directories(repo),
        )
    )
    trusted = (str(repo),)
    for sha in commits:
        if git(repo, "cat-file", "-t", sha, safe_directories=trusted) != "commit":
            raise ValueError(f"{sha} is not a commit")

    objects = git(
        repo,
        "rev-list",
        "--objects",
        "--missing=print",
        *commits,
        safe_directories=trusted,
    )
    if any(line.startswith("?") for line in objects.splitlines()):
        raise ValueError(
            "source repository has missing Git objects; materialize partial-clone "
            "objects separately before review (no remote objects were fetched)"
        )
    object_format = git(
        repo, "rev-parse", "--show-object-format", safe_directories=trusted
    )
    if snapshot_parent is not None:
        snapshot_parent = snapshot_parent.resolve(strict=True)
    snapshot = Path(
        tempfile.mkdtemp(prefix="tao-independent-review-", dir=snapshot_parent)
    )
    try:
        git(snapshot, "init", "--quiet", f"--object-format={object_format}")
        git(snapshot, "config", "core.hooksPath", os.devnull)
        git(snapshot, "config", "core.attributesFile", os.devnull)
        git(snapshot, "config", "core.autocrlf", "false")
        git(snapshot, "config", "core.fsmonitor", "false")
        git(
            snapshot,
            "fetch",
            "--quiet",
            "--no-tags",
            str(repo),
            *commits,
            safe_directories=trusted,
        )
        git(snapshot, "checkout", "--quiet", "--detach", head)
        if git(snapshot, "rev-parse", "HEAD") != head:
            raise ValueError("snapshot HEAD does not match the requested commit")
        base_sha = base if base is not None else git(snapshot, "mktree", input_text="")
    except BaseException:
        try:
            shutil.rmtree(snapshot)
        except OSError as error:
            print(
                f"prepare_review: could not remove {snapshot}: {error}", file=sys.stderr
            )
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
    parser.add_argument(
        "--snapshot-parent",
        type=Path,
        help="existing directory already accessible to the background reviewer",
    )
    baseline = parser.add_mutually_exclusive_group(required=True)
    baseline.add_argument("--base", type=commit_sha)
    baseline.add_argument(
        "--root", action="store_true", help="review from an empty tree"
    )
    parser.add_argument("--head", required=True, type=commit_sha)
    arguments = parser.parse_args()
    try:
        snapshot = prepare_review(
            arguments.repo,
            arguments.base,
            arguments.head,
            snapshot_parent=arguments.snapshot_parent,
        )
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
