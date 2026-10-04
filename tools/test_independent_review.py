import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = (
    Path(__file__).resolve().parent.parent
    / "src/skills/independent-review/scripts/prepare_review.py"
)
SPEC = importlib.util.spec_from_file_location("prepare_review", SCRIPT)
prepare_review = importlib.util.module_from_spec(SPEC)
with patch.object(sys, "dont_write_bytecode", True):
    SPEC.loader.exec_module(prepare_review)


def git(repo: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


class PrepareReviewTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repo = Path(self.temporary.name) / "author"
        self.repo.mkdir()
        git(self.repo, "init", "--quiet")
        git(self.repo, "config", "user.name", "Review test")
        git(self.repo, "config", "user.email", "review@example.com")
        self.base = self.commit("base\n")
        self.middle = self.commit("middle\n")
        self.head = self.commit("pushed\n")

    def commit(self, content: str) -> str:
        (self.repo / "code.txt").write_text(content)
        git(self.repo, "add", "code.txt")
        git(self.repo, "commit", "--quiet", "-m", "Update code")
        return git(self.repo, "rev-parse", "HEAD")

    def snapshot(self, base: str, head: str) -> Path:
        result = prepare_review.prepare_review(self.repo, base, head)
        snapshot = Path(result["directory"])
        self.addCleanup(shutil.rmtree, snapshot)
        self.assertEqual(result["base_sha"], base)
        self.assertEqual(result["head_sha"], head)
        return snapshot

    def test_pins_pushed_commit_and_leaves_dirty_author_workspace_alone(self) -> None:
        later = self.commit("later commit\n")
        (self.repo / "code.txt").write_text("unfinished changes\n")
        (self.repo / "private-notes.txt").write_text("author reasoning\n")
        status = git(self.repo, "status", "--porcelain")

        snapshot = self.snapshot(self.base, self.head)

        self.assertEqual(git(snapshot, "rev-parse", "HEAD"), self.head)
        self.assertEqual((snapshot / "code.txt").read_text(), "pushed\n")
        self.assertFalse((snapshot / "private-notes.txt").exists())
        self.assertEqual(git(snapshot, "status", "--porcelain"), "")
        self.assertEqual(git(snapshot, "remote"), "")
        self.assertFalse((snapshot / ".git/objects/info/alternates").exists())
        (snapshot / "code.txt").write_text("review test artifact\n")
        self.assertEqual((self.repo / "code.txt").read_text(), "unfinished changes\n")
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), later)
        self.assertEqual(git(self.repo, "status", "--porcelain"), status)

    def test_keeps_every_commit_in_a_multi_commit_push(self) -> None:
        snapshot = self.snapshot(self.base, self.head)
        commits = git(snapshot, "log", "--format=%H", f"{self.base}..{self.head}")
        self.assertEqual(commits.splitlines(), [self.head, self.middle])
        self.assertIn("-base", git(snapshot, "diff", self.base, self.head))

    def test_keeps_old_tree_after_a_force_update(self) -> None:
        git(self.repo, "checkout", "--quiet", "--detach", self.base)
        replacement = self.commit("replacement\n")
        snapshot = self.snapshot(self.head, replacement)
        diff = git(snapshot, "diff", self.head, replacement)
        self.assertIn("-pushed", diff)
        self.assertIn("+replacement", diff)
        self.assertEqual(git(snapshot, "show", f"{self.head}:code.txt"), "pushed")

    def test_preserves_sha256_repository_format(self) -> None:
        self.repo = Path(self.temporary.name) / "sha256-author"
        self.repo.mkdir()
        git(self.repo, "init", "--quiet", "--object-format=sha256")
        git(self.repo, "config", "user.name", "Review test")
        git(self.repo, "config", "user.email", "review@example.com")
        base = self.commit("base\n")
        head = self.commit("pushed\n")
        snapshot = self.snapshot(base, head)
        self.assertEqual(len(head), 64)
        self.assertEqual(git(snapshot, "rev-parse", "--show-object-format"), "sha256")
        self.assertEqual(git(snapshot, "rev-parse", "HEAD"), head)

    def test_ignores_inherited_git_workspace_environment(self) -> None:
        with patch.dict(
            os.environ,
            {"GIT_DIR": str(self.repo / ".git"), "GIT_WORK_TREE": str(self.repo)},
        ):
            snapshot = self.snapshot(self.base, self.head)
        self.assertEqual(git(snapshot, "rev-parse", "HEAD"), self.head)
        self.assertEqual(git(self.repo, "rev-parse", "HEAD"), self.head)
        self.assertEqual((snapshot / "code.txt").read_text(), "pushed\n")

    def test_does_not_run_lfs_smudge_filters(self) -> None:
        (self.repo / ".gitattributes").write_text("*.txt filter=lfs\n")
        git(self.repo, "add", ".gitattributes")
        head = self.commit("LFS pointer\n")
        committed_content = git(self.repo, "show", f"{head}:code.txt") + "\n"
        config = Path(self.temporary.name) / "global-config"
        config.write_text(
            '[filter "lfs"]\n'
            '    smudge = "exit 1"\n'
            '    process = "exit 1"\n'
            "    required = true\n"
        )
        with patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(config)}):
            snapshot = self.snapshot(self.base, head)
        self.assertEqual((snapshot / "code.txt").read_text(), committed_content)

    def test_cli_emits_scope_and_snapshot_json(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--repo",
                str(self.repo),
                "--base",
                self.base,
                "--head",
                self.head,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        output = json.loads(result.stdout)
        snapshot = Path(output["directory"])
        self.addCleanup(shutil.rmtree, snapshot)
        self.assertEqual(output["head_sha"], git(snapshot, "rev-parse", "HEAD"))

    def test_cli_rejects_mutable_and_missing_commits(self) -> None:
        for value in ("HEAD", "main", "--help", "f" * 40):
            with self.subTest(value=value):
                result = subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT),
                        "--repo",
                        str(self.repo),
                        "--base",
                        self.base,
                        "--head",
                        value,
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertTrue(result.stderr)

    def test_rejects_non_commit_objects(self) -> None:
        blob = git(self.repo, "rev-parse", f"{self.head}:code.txt")
        with self.assertRaisesRegex(ValueError, "is not a commit"):
            prepare_review.prepare_review(self.repo, self.base, blob)

    def test_cleans_partial_snapshot_on_setup_failure(self) -> None:
        snapshot = Path(self.temporary.name) / "failed-snapshot"
        snapshot.mkdir()
        real_git = prepare_review.git

        def fail_fetch(directory: Path, *arguments: str) -> str:
            if arguments[0] == "fetch":
                raise subprocess.CalledProcessError(1, "git fetch", stderr="failed")
            return real_git(directory, *arguments)

        with (
            patch.object(
                prepare_review.tempfile, "mkdtemp", return_value=str(snapshot)
            ),
            patch.object(prepare_review, "git", side_effect=fail_fetch),
            self.assertRaises(subprocess.CalledProcessError),
        ):
            prepare_review.prepare_review(self.repo, self.base, self.head)
        self.assertFalse(snapshot.exists())


if __name__ == "__main__":
    unittest.main()
