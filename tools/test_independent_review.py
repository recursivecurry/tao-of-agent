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
    environment = {
        name: value for name, value in os.environ.items() if not name.startswith("GIT_")
    }
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    return subprocess.run(
        [
            "git",
            "-c",
            f"core.hooksPath={os.devnull}",
            "-c",
            f"core.attributesFile={os.devnull}",
            "-c",
            "core.fsmonitor=false",
            "-C",
            str(repo),
            *arguments,
        ],
        env=environment,
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

    def snapshot(self, base: str | None, head: str) -> Path:
        result = prepare_review.prepare_review(self.repo, base, head)
        snapshot = Path(result["directory"])
        self.addCleanup(shutil.rmtree, snapshot)
        if base is None:
            self.assertEqual(result["baseline_kind"], "empty-tree")
            self.assertEqual(
                git(snapshot, "cat-file", "-t", result["base_sha"]), "tree"
            )
        else:
            self.assertEqual(result["base_sha"], base)
            self.assertEqual(result["baseline_kind"], "commit")
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

    def test_fetches_unadvertised_force_update_base_with_old_protocol_config(
        self,
    ) -> None:
        git(self.repo, "reset", "--hard", self.base)
        replacement = self.commit("replacement\n")
        for version in ("0", "1"):
            with self.subTest(version=version):
                git(self.repo, "config", "protocol.version", version)
                config = Path(self.temporary.name) / "protocol-config"
                config.write_text(f"[protocol]\n version = {version}\n")
                with patch.dict(os.environ, {"GIT_CONFIG_GLOBAL": str(config)}):
                    snapshot = self.snapshot(self.head, replacement)
                self.assertEqual(
                    git(snapshot, "show", f"{self.head}:code.txt"), "pushed"
                )

    def test_accepts_a_repository_subdirectory(self) -> None:
        subdirectory = self.repo / "nested"
        subdirectory.mkdir()
        self.repo = subdirectory
        snapshot = self.snapshot(self.base, self.head)
        self.assertEqual((snapshot / "code.txt").read_text(), "pushed\n")

    def test_accepts_a_bare_repository(self) -> None:
        bare = Path(self.temporary.name) / "bare.git"
        git(self.repo, "clone", "--quiet", "--bare", str(self.repo), str(bare))
        self.repo = bare
        snapshot = self.snapshot(self.base, self.head)
        self.assertEqual((snapshot / "code.txt").read_text(), "pushed\n")

    def test_accepts_a_linked_worktree_subdirectory(self) -> None:
        worktree = Path(self.temporary.name) / "linked-worktree"
        git(
            self.repo,
            "worktree",
            "add",
            "--quiet",
            "--detach",
            str(worktree),
            self.head,
        )
        subdirectory = worktree / "nested"
        subdirectory.mkdir()
        self.repo = subdirectory
        snapshot = self.snapshot(self.base, self.head)
        self.assertEqual((snapshot / "code.txt").read_text(), "pushed\n")

    def test_reviews_all_files_and_commits_without_a_baseline_commit(self) -> None:
        result = prepare_review.prepare_review(self.repo, None, self.head)
        snapshot = Path(result["directory"])
        self.addCleanup(shutil.rmtree, snapshot)
        self.assertEqual(result["baseline_kind"], "empty-tree")
        self.assertEqual(git(snapshot, "ls-tree", result["base_sha"]), "")
        self.assertIn("+pushed", git(snapshot, "diff", result["base_sha"], self.head))
        self.assertEqual(
            git(snapshot, "log", "--format=%H", self.head).splitlines(),
            [self.head, self.middle, self.base],
        )

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

    def test_does_not_run_hooks_tracked_in_the_pushed_tree(self) -> None:
        marker = Path(self.temporary.name) / "tracked-hook-ran"
        hook = self.repo / "disabled-hooks/post-checkout"
        hook.parent.mkdir()
        hook.write_text(f'#!/bin/sh\nprintf ran > "{marker}"\n')
        hook.chmod(0o755)
        git(self.repo, "add", "disabled-hooks")
        head = self.commit("with tracked hook\n")

        snapshot = self.snapshot(self.base, head)

        self.assertTrue((snapshot / "disabled-hooks/post-checkout").exists())
        self.assertFalse(marker.exists())

    def test_ignores_default_global_attributes(self) -> None:
        home = Path(self.temporary.name) / "home"
        xdg = Path(self.temporary.name) / "xdg"
        for attributes in (home / ".config/git/attributes", xdg / "git/attributes"):
            attributes.parent.mkdir(parents=True)
            attributes.write_text("* text eol=crlf\n")
        for xdg_home in ("", str(xdg)):
            with (
                self.subTest(xdg_home=xdg_home),
                patch.dict(
                    os.environ, {"HOME": str(home), "XDG_CONFIG_HOME": xdg_home}
                ),
            ):
                snapshot = self.snapshot(self.base, self.head)
                self.assertEqual((snapshot / "code.txt").read_bytes(), b"pushed\n")

    def test_preserves_existing_global_trust_without_other_global_settings(
        self,
    ) -> None:
        home = Path(self.temporary.name) / "home"
        home.mkdir()
        (home / ".gitconfig").write_text(
            f"[safe]\n directory = {self.repo}\n"
            "[core]\n fsmonitor = exit 1\n"
            '[filter "custom"]\n smudge = exit 1\n required = true\n'
        )
        (self.repo / ".gitattributes").write_text("*.txt filter=custom\n")
        git(self.repo, "add", ".gitattributes")
        head = self.commit("unfiltered\n")
        real_run = subprocess.run

        def simulate_foreign_owner(command, **kwargs):
            directory = command[command.index("-C") + 1]
            if Path(directory).is_relative_to(self.repo):
                kwargs["env"] = dict(kwargs["env"], GIT_TEST_ASSUME_DIFFERENT_OWNER="1")
            return real_run(command, **kwargs)

        with (
            patch.dict(os.environ, {"HOME": str(home), "XDG_CONFIG_HOME": ""}),
            patch.object(
                prepare_review.subprocess, "run", side_effect=simulate_foreign_owner
            ),
        ):
            snapshot = self.snapshot(self.base, head)
        self.assertEqual((snapshot / "code.txt").read_bytes(), b"unfiltered\n")

    def test_does_not_trust_a_foreign_repository_without_existing_trust(self) -> None:
        home = Path(self.temporary.name) / "home"
        home.mkdir()
        git(self.repo, "config", "safe.directory", str(self.repo))
        real_run = subprocess.run

        def simulate_foreign_owner(command, **kwargs):
            kwargs["env"] = dict(kwargs["env"], GIT_TEST_ASSUME_DIFFERENT_OWNER="1")
            return real_run(command, **kwargs)

        with (
            patch.dict(os.environ, {"HOME": str(home), "XDG_CONFIG_HOME": ""}),
            patch.object(
                prepare_review.subprocess, "run", side_effect=simulate_foreign_owner
            ),
            self.assertRaises(subprocess.CalledProcessError) as raised,
        ):
            prepare_review.prepare_review(self.repo, self.base, self.head)
        self.assertIn("dubious ownership", raised.exception.stderr)

    def test_rejects_git_versions_without_global_config_isolation(self) -> None:
        real_git = prepare_review.git

        def old_git(directory: Path, *arguments: str, **kwargs) -> str:
            if arguments == ("--version",):
                return "git version 2.31.1"
            return real_git(directory, *arguments, **kwargs)

        with (
            patch.object(prepare_review, "git", side_effect=old_git),
            patch.object(prepare_review.tempfile, "mkdtemp") as make_snapshot,
            self.assertRaisesRegex(ValueError, "Git 2.32\\+ is required"),
        ):
            prepare_review.prepare_review(self.repo, self.base, self.head)
        make_snapshot.assert_not_called()

    def test_fixtures_ignore_user_signing_hooks_and_templates(self) -> None:
        home = Path(self.temporary.name) / "home"
        home.mkdir()
        hooks = home / "hooks"
        hooks.mkdir()
        hook = hooks / "pre-commit"
        hook.write_text("#!/bin/sh\nexit 1\n")
        hook.chmod(0o755)
        template = home / "template"
        template.mkdir()
        (template / "fixture-contamination").write_text("user template\n")
        (home / ".gitconfig").write_text(
            "[commit]\n gpgsign = true\n[gpg]\n program = false\n"
            f"[core]\n hooksPath = {hooks}\n[init]\n templateDir = {template}\n"
        )
        fixture = home / "fixture"
        fixture.mkdir()
        with patch.dict(os.environ, {"HOME": str(home), "XDG_CONFIG_HOME": ""}):
            git(fixture, "init", "--quiet")
            git(fixture, "config", "user.name", "Fixture")
            git(fixture, "config", "user.email", "fixture@example.com")
            git(fixture, "commit", "--quiet", "--allow-empty", "-m", "Fixture")
        self.assertFalse((fixture / ".git/fixture-contamination").exists())
        self.assertEqual(git(fixture, "log", "-1", "--format=%s"), "Fixture")

    def test_ignores_system_and_global_non_lfs_filters(self) -> None:
        (self.repo / ".gitattributes").write_text("*.txt filter=custom\n")
        git(self.repo, "add", ".gitattributes")
        head = self.commit("raw content\n")
        config = Path(self.temporary.name) / "filter-config"
        config.write_text(
            '[filter "custom"]\n'
            '    smudge = "exit 1"\n'
            '    process = "exit 1"\n'
            "    required = true\n"
        )
        with patch.dict(
            os.environ,
            {"GIT_CONFIG_GLOBAL": str(config), "GIT_CONFIG_SYSTEM": str(config)},
        ):
            snapshot = self.snapshot(self.base, head)
        self.assertEqual((snapshot / "code.txt").read_text(), "raw content\n")

    def test_ignores_inherited_command_config_and_repository_discovery_settings(
        self,
    ) -> None:
        hooks = Path(self.temporary.name) / "hooks"
        hooks.mkdir()
        marker = Path(self.temporary.name) / "hook-ran"
        hook = hooks / "post-checkout"
        hook.write_text(f'#!/bin/sh\nprintf ran > "{marker}"\n')
        hook.chmod(0o755)
        injections = (
            {"GIT_CONFIG_PARAMETERS": f"'core.hooksPath={hooks}'"},
            {
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "core.hooksPath",
                "GIT_CONFIG_VALUE_0": str(hooks),
            },
            {"GIT_NAMESPACE": "unrelated", "GIT_CEILING_DIRECTORIES": str(self.repo)},
        )
        for injection in injections:
            with self.subTest(injection=injection):
                with patch.dict(os.environ, injection):
                    snapshot = self.snapshot(self.base, self.head)
                self.assertFalse(marker.exists())
                self.assertEqual((snapshot / "code.txt").read_text(), "pushed\n")

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

    def test_cli_requires_exactly_one_baseline_mode(self) -> None:
        for baseline in ([], ["--base", self.base, "--root"]):
            with self.subTest(baseline=baseline):
                result = subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT),
                        "--repo",
                        str(self.repo),
                        "--head",
                        self.head,
                        *baseline,
                    ],
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")

    def test_cli_root_mode(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--repo",
                str(self.repo),
                "--head",
                self.head,
                "--root",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        output = json.loads(result.stdout)
        snapshot = Path(output["directory"])
        self.addCleanup(shutil.rmtree, snapshot)
        self.assertEqual(output["baseline_kind"], "empty-tree")
        self.assertEqual(git(snapshot, "ls-tree", output["base_sha"]), "")

    def test_rejects_non_commit_objects(self) -> None:
        blob = git(self.repo, "rev-parse", f"{self.head}:code.txt")
        with self.assertRaisesRegex(ValueError, "is not a commit"):
            prepare_review.prepare_review(self.repo, self.base, blob)

    def test_cleans_partial_snapshot_on_setup_failure(self) -> None:
        snapshot = Path(self.temporary.name) / "failed-snapshot"
        snapshot.mkdir()
        real_git = prepare_review.git

        def fail_fetch(directory: Path, *arguments: str, **kwargs) -> str:
            if arguments[0] == "fetch":
                raise subprocess.CalledProcessError(1, "git fetch", stderr="failed")
            return real_git(directory, *arguments, **kwargs)

        with (
            patch.object(
                prepare_review.tempfile, "mkdtemp", return_value=str(snapshot)
            ),
            patch.object(prepare_review, "git", side_effect=fail_fetch),
            self.assertRaises(subprocess.CalledProcessError),
        ):
            prepare_review.prepare_review(self.repo, self.base, self.head)
        self.assertFalse(snapshot.exists())

    def test_cleans_partial_snapshot_on_interrupt(self) -> None:
        snapshot = Path(self.temporary.name) / "interrupted-snapshot"
        snapshot.mkdir()
        real_git = prepare_review.git

        def interrupt_fetch(directory: Path, *arguments: str, **kwargs) -> str:
            if arguments[0] == "fetch":
                raise KeyboardInterrupt
            return real_git(directory, *arguments, **kwargs)

        with (
            patch.object(
                prepare_review.tempfile, "mkdtemp", return_value=str(snapshot)
            ),
            patch.object(prepare_review, "git", side_effect=interrupt_fetch),
            self.assertRaises(KeyboardInterrupt),
        ):
            prepare_review.prepare_review(self.repo, self.base, self.head)
        self.assertFalse(snapshot.exists())

    def test_reports_cleanup_failure_without_masking_setup_failure(self) -> None:
        snapshot = Path(self.temporary.name) / "failed-snapshot"
        snapshot.mkdir()
        real_git = prepare_review.git

        def fail_fetch(directory: Path, *arguments: str, **kwargs) -> str:
            if arguments[0] == "fetch":
                raise subprocess.CalledProcessError(
                    1, "git fetch", stderr="original failure"
                )
            return real_git(directory, *arguments, **kwargs)

        with (
            patch.object(
                prepare_review.tempfile, "mkdtemp", return_value=str(snapshot)
            ),
            patch.object(prepare_review, "git", side_effect=fail_fetch),
            patch.object(
                prepare_review.shutil, "rmtree", side_effect=PermissionError("denied")
            ),
            patch("sys.stderr") as stderr,
            self.assertRaises(subprocess.CalledProcessError) as raised,
        ):
            prepare_review.prepare_review(self.repo, self.base, self.head)
        self.assertEqual(raised.exception.stderr, "original failure")
        message = "".join(call.args[0] for call in stderr.write.call_args_list)
        self.assertIn(str(snapshot), message)
        self.assertIn("denied", message)


if __name__ == "__main__":
    unittest.main()
