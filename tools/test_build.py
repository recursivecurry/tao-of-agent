import contextlib
import io
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

import build

SKILL = "---\nname: demo\ndescription: Demo skill.\n---\n\nSee [the note](references/note.md).\n"
NOTE = "A note.\n"
PLUGIN = '{\n  "name": "tao",\n  "version": "0.2.0"\n}\n'
MARKETPLACE = (
    '{\n  "name": "m",\n'
    '  "plugins": [{"name": "tao", "source": "./plugins/claude/tao"}]\n}\n'
)
CODEX_MARKETPLACE = (
    '{\n  "name": "m",\n  "plugins": [{"name": "tao", "source": '
    '{"source": "local", "path": "./plugins/codex/tao"}}]\n}\n'
)
SKILL_SOURCE = "src/skills/demo/SKILL.md.tmpl"


def write(
    root: Path, path: str, content: str | bytes, *, executable: bool = False
) -> None:
    file = root / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(content.encode() if isinstance(content, str) else content)
    file.chmod(0o755 if executable else 0o644)


def snapshot(root: Path) -> dict[str, tuple[bytes, int, int]]:
    return {
        path.relative_to(root).as_posix(): (
            path.read_bytes(),
            path.stat().st_mode,
            path.stat().st_mtime_ns,
        )
        for path in sorted(root.rglob("*"))
        if path.is_file() and ".git" not in path.parts
    }


def run(command, *arguments) -> tuple[int, str, str]:
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = command(*arguments)
    return code, stdout.getvalue(), stderr.getvalue()


def git(root: Path, *arguments: str) -> None:
    identity = ["-c", "user.name=test", "-c", "user.email=test@example.com"]
    subprocess.run(
        ["git", *identity, *arguments], cwd=root, check=True, capture_output=True
    )


def commit_all(root: Path, message: str) -> None:
    git(root, "add", "-A")
    git(root, "commit", "-m", message)


class SourceTreeCase(unittest.TestCase):
    def setUp(self) -> None:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        write(self.root, SKILL_SOURCE, SKILL)
        write(self.root, "src/skills/demo/references/note.md", NOTE)
        write(self.root, build.README, "[`demo`](skills/demo)\n")
        write(self.root, build.CLAUDE.source_manifest, PLUGIN)
        write(self.root, build.CLAUDE.source_marketplace, MARKETPLACE)
        write(self.root, build.CODEX.source_manifest, PLUGIN)
        write(self.root, build.CODEX.source_marketplace, CODEX_MARKETPLACE)

    def build(self) -> str:
        code, stdout, _ = run(build.build, self.root)
        self.assertEqual(code, 0)
        return stdout


class RenderTest(unittest.TestCase):
    def render(self, text: str, target: str) -> str:
        return build.render_template(text, target, "t.tmpl", notice=False).decode()

    def test_block_appears_only_in_its_target(self) -> None:
        text = "a\n<!-- target:claude -->\nc\n<!-- /target -->\n<!-- target:generic -->\ng\n<!-- /target -->\nz\n"
        self.assertEqual(self.render(text, "claude"), "a\nc\nz\n")
        self.assertEqual(self.render(text, "generic"), "a\ng\nz\n")
        self.assertEqual(self.render(text, "codex"), "a\nz\n")

    def test_indented_markers_are_removed_with_their_newline(self) -> None:
        text = "- item\n  <!-- target:claude -->\n  nested\n\t<!-- /target -->\nend"
        self.assertEqual(self.render(text, "claude"), "- item\n  nested\nend")
        self.assertEqual(self.render(text, "generic"), "- item\nend")

    def test_marker_must_be_a_whole_line(self) -> None:
        text = "text <!-- target:claude --> more\n<!-- target: claude -->\n"
        self.assertEqual(self.render(text, "generic"), text)

    def test_other_syntax_passes_through(self) -> None:
        text = "{{ value }} {% tag %} <!-- a comment -->\n"
        self.assertEqual(self.render(text, "claude"), text)

    def test_markers_work_inside_frontmatter(self) -> None:
        text = (
            "---\nname: demo\n<!-- target:claude -->\ndescription: C\n<!-- /target -->\n"
            "<!-- target:generic -->\ndescription: G\n<!-- /target -->\n---\n"
        )
        self.assertEqual(
            self.render(text, "claude"), "---\nname: demo\ndescription: C\n---\n"
        )
        self.assertEqual(
            self.render(text, "generic"), "---\nname: demo\ndescription: G\n---\n"
        )

    def test_notice_becomes_line_two(self) -> None:
        rendered = build.render_template(SKILL, "generic", SKILL_SOURCE, notice=True)
        lines = rendered.decode().splitlines()
        self.assertEqual(lines[0], "---")
        self.assertEqual(
            lines[1],
            f"# Generated from {SKILL_SOURCE}. Edit the source, not this file.",
        )
        self.assertEqual(lines[2:], SKILL.splitlines()[1:])

    def test_notice_requires_frontmatter_on_line_one(self) -> None:
        with self.assertRaisesRegex(build.BuildError, r"^t\.tmpl:1: frontmatter"):
            build.render_template("# Title\n", "generic", "t.tmpl", notice=True)

    def test_marker_errors_report_file_and_line(self) -> None:
        cases = {
            "nested": (
                "<!-- target:claude -->\n<!-- target:generic -->\n",
                r"^t\.tmpl:2: .*nested",
            ),
            "unclosed": (
                "a\n<!-- target:claude -->\nb\n",
                r"^t\.tmpl:2: .*never closed",
            ),
            "stray close": ("a\n<!-- /target -->\n", r"^t\.tmpl:2: closing marker"),
            "unknown target": (
                "<!-- target:cursor -->\n<!-- /target -->\n",
                r"^t\.tmpl:1: unknown target 'cursor'",
            ),
        }
        for name, (text, message) in cases.items():
            with (
                self.subTest(name),
                self.assertRaisesRegex(build.BuildError, message),
            ):
                self.render(text, "claude")


class BuildTest(SourceTreeCase):
    def test_writes_every_distribution(self) -> None:
        self.build()
        generated = {
            path: content
            for path, (content, _, _) in snapshot(self.root).items()
            if not path.startswith("src/") and path != build.README
        }
        skill = build.render_template(SKILL, "generic", SKILL_SOURCE, notice=True)
        self.assertEqual(
            generated,
            {
                "skills/demo/SKILL.md": skill,
                "skills/demo/references/note.md": NOTE.encode(),
                "plugins/claude/tao/skills/demo/SKILL.md": skill,
                "plugins/claude/tao/skills/demo/references/note.md": NOTE.encode(),
                "plugins/claude/tao/.claude-plugin/plugin.json": PLUGIN.encode(),
                ".claude-plugin/marketplace.json": MARKETPLACE.encode(),
                "plugins/codex/tao/skills/demo/SKILL.md": skill,
                "plugins/codex/tao/skills/demo/references/note.md": NOTE.encode(),
                "plugins/codex/tao/.codex-plugin/plugin.json": PLUGIN.encode(),
                ".agents/plugins/marketplace.json": CODEX_MARKETPLACE.encode(),
            },
        )

    def test_renders_each_target_from_its_blocks(self) -> None:
        template = SKILL + "<!-- target:claude -->\nClaude only.\n<!-- /target -->\n"
        write(self.root, SKILL_SOURCE, template)
        self.build()
        claude = (self.root / "plugins/claude/tao/skills/demo/SKILL.md").read_text()
        codex = (self.root / "plugins/codex/tao/skills/demo/SKILL.md").read_text()
        generic = (self.root / "skills/demo/SKILL.md").read_text()
        self.assertIn("Claude only.", claude)
        self.assertNotIn("Claude only.", codex)
        self.assertNotIn("Claude only.", generic)

    def test_shared_plugin_files_go_to_both_plugins(self) -> None:
        template = "all\n<!-- target:codex -->\ncodex\n<!-- /target -->\n"
        write(self.root, "src/plugin/hooks/context.md.tmpl", template)
        write(self.root, "src/plugin/hooks/run.sh", "echo\n", executable=True)
        self.build()
        claude, codex = (
            self.root / "plugins/claude/tao",
            self.root / "plugins/codex/tao",
        )
        self.assertEqual((claude / "hooks/context.md").read_text(), "all\n")
        self.assertEqual((codex / "hooks/context.md").read_text(), "all\ncodex\n")
        self.assertTrue(os.access(claude / "hooks/run.sh", os.X_OK))
        self.assertTrue(os.access(codex / "hooks/run.sh", os.X_OK))
        self.assertFalse((self.root / "skills/hooks").exists())

    def test_agent_files_go_to_their_plugin_only(self) -> None:
        write(self.root, "src/claude/hooks/hooks.json", "{}\n")
        write(self.root, "src/codex/agents/reviewer.toml", "x\n")
        self.build()
        claude, codex = (
            self.root / "plugins/claude/tao",
            self.root / "plugins/codex/tao",
        )
        self.assertTrue((claude / "hooks/hooks.json").exists())
        self.assertFalse((codex / "hooks").exists())
        self.assertTrue((codex / "agents/reviewer.toml").exists())
        self.assertFalse((claude / "agents").exists())
        self.assertFalse((claude / "plugin.json").exists())
        self.assertFalse((codex / "marketplace.json").exists())

    def test_other_templates_lose_the_suffix_and_get_no_notice(self) -> None:
        write(self.root, "src/skills/demo/references/extra.md.tmpl", "Extra.\n")
        self.build()
        extra = self.root / "skills/demo/references/extra.md"
        self.assertEqual(extra.read_text(), "Extra.\n")

    def test_copies_non_templates_byte_for_byte(self) -> None:
        binary = b"\x00\xff\r\n<!-- target:claude -->\n"
        write(self.root, "src/skills/demo/assets/blob.bin", binary)
        self.build()
        blob = self.root / "plugins/codex/tao/skills/demo/assets/blob.bin"
        self.assertEqual(blob.read_bytes(), binary)

    def test_writes_lf_line_endings_for_templates(self) -> None:
        write(self.root, SKILL_SOURCE, SKILL.replace("\n", "\r\n"))
        self.build()
        self.assertNotIn(b"\r", (self.root / "skills/demo/SKILL.md").read_bytes())

    def test_copies_the_executable_bit(self) -> None:
        write(self.root, "src/skills/demo/scripts/run.sh", "echo\n", executable=True)
        self.build()
        self.assertTrue(os.access(self.root / "skills/demo/scripts/run.sh", os.X_OK))
        self.assertFalse(os.access(self.root / "skills/demo/SKILL.md", os.X_OK))

    def test_prunes_files_and_empty_directories_under_owned_roots(self) -> None:
        write(self.root, "skills/old/SKILL.md", "old\n")
        write(self.root, "plugins/tao/evals/case/prompt.md", "p\n")
        write(self.root, ".claude-plugin/plugin.json", PLUGIN)
        write(self.root, ".agents/plugins/old.json", "{}\n")
        write(self.root, "evals/case/prompt.md", "kept\n")
        write(self.root, ".agents/skills/installed/SKILL.md", "kept\n")
        stdout = self.build()
        self.assertFalse((self.root / "skills/old").exists())
        self.assertFalse((self.root / "plugins/tao").exists())
        self.assertFalse((self.root / ".claude-plugin/plugin.json").exists())
        self.assertFalse((self.root / ".agents/plugins/old.json").exists())
        self.assertTrue((self.root / "evals/case/prompt.md").exists())
        self.assertTrue((self.root / ".agents/skills/installed/SKILL.md").exists())
        self.assertIn("removed skills/old/SKILL.md", stdout)

    def test_second_build_changes_nothing(self) -> None:
        self.build()
        first = snapshot(self.root)
        self.assertEqual(self.build(), "")
        self.assertEqual(snapshot(self.root), first)

    def test_rejects_invalid_json_manifest(self) -> None:
        write(self.root, build.CLAUDE.source_manifest, '{\n  "name": \n}\n')
        with self.assertRaisesRegex(build.BuildError, r"^src/claude/plugin\.json:3: "):
            build.build(self.root)

    def test_rejects_two_sources_for_one_output(self) -> None:
        write(self.root, "src/skills/demo/references/note.md.tmpl", NOTE)
        with self.assertRaisesRegex(build.BuildError, "two source files"):
            build.build(self.root)


class CheckTest(SourceTreeCase):
    def setUp(self) -> None:
        super().setUp()
        self.build()

    def test_passes_after_build(self) -> None:
        self.assertEqual(run(build.check, self.root), (0, "", ""))

    def test_fails_with_a_diff_after_a_hand_edit(self) -> None:
        skill = self.root / "skills/demo/SKILL.md"
        skill.write_text(skill.read_text() + "edited by hand\n")
        code, stdout, _ = run(build.check, self.root)
        self.assertEqual(code, 1)
        self.assertIn("--- skills/demo/SKILL.md", stdout)
        self.assertIn("-edited by hand", stdout)

    def test_fails_on_extra_missing_and_mode_changes(self) -> None:
        write(self.root, "plugins/codex/tao/extra.md", "extra\n")
        (self.root / "skills/demo/references/note.md").unlink()
        (self.root / ".claude-plugin/marketplace.json").chmod(0o755)
        code, stdout, _ = run(build.check, self.root)
        self.assertEqual(code, 1)
        self.assertIn("not generated from src: plugins/codex/tao/extra.md", stdout)
        self.assertIn("missing: skills/demo/references/note.md", stdout)
        self.assertIn("wrong executable bit: .claude-plugin/marketplace.json", stdout)

    def test_fails_when_the_source_changed(self) -> None:
        write(self.root, SKILL_SOURCE, SKILL + "New line.\n")
        code, stdout, _ = run(build.check, self.root)
        self.assertEqual(code, 1)
        self.assertIn("+New line.", stdout)


class LintTest(SourceTreeCase):
    def assert_violation(self, expected: str) -> None:
        violations = build.lint_violations(self.root)
        self.assertTrue(
            any(expected in violation for violation in violations), violations
        )

    def test_clean_source_has_no_violations(self) -> None:
        self.assertEqual(build.lint_violations(self.root), [])
        self.assertEqual(run(build.lint, self.root), (0, "", ""))

    def test_lint_prints_violations_and_fails(self) -> None:
        (self.root / SKILL_SOURCE).unlink()
        code, _, stderr = run(build.lint, self.root)
        self.assertEqual(code, 1)
        self.assertIn("src/skills/demo: missing SKILL.md.tmpl", stderr)

    def test_frontmatter_must_open_on_line_one(self) -> None:
        write(self.root, SKILL_SOURCE, "\n" + SKILL)
        self.assert_violation(f"{SKILL_SOURCE}:1: frontmatter must open on line 1")

    def test_frontmatter_must_close(self) -> None:
        write(self.root, SKILL_SOURCE, "---\nname: demo\ndescription: D\n")
        self.assert_violation(f"{SKILL_SOURCE}:1: frontmatter is not closed")

    def test_frontmatter_needs_name_and_description(self) -> None:
        write(self.root, SKILL_SOURCE, "---\nlicense: MIT\ndescription:\n---\n")
        self.assert_violation("frontmatter has no name")
        self.assert_violation("frontmatter has no description")

    def test_frontmatter_is_checked_for_each_target(self) -> None:
        template = (
            "---\nname: demo\n<!-- target:claude -->\ndescription: C\n"
            "<!-- /target -->\n---\n"
        )
        write(self.root, SKILL_SOURCE, template)
        self.assert_violation("frontmatter has no description")

    def test_name_must_equal_the_directory(self) -> None:
        write(self.root, SKILL_SOURCE, SKILL.replace("name: demo", "name: other"))
        self.assert_violation(f"{SKILL_SOURCE}:2: name 'other' must equal")

    def test_name_must_match_the_pattern(self) -> None:
        skill = SKILL.replace("name: demo", "name: Bad_Name").replace(
            "(references/note.md)", "(https://example.com)"
        )
        write(self.root, "src/skills/Bad_Name/SKILL.md.tmpl", skill)
        self.assert_violation("name 'Bad_Name' must equal")

    def test_quoted_name_is_accepted(self) -> None:
        write(self.root, SKILL_SOURCE, SKILL.replace("name: demo", 'name: "demo"'))
        self.assertEqual(build.lint_violations(self.root), [])

    def test_links_must_resolve_inside_the_skill(self) -> None:
        write(self.root, SKILL_SOURCE, SKILL + "[gone](references/gone.md)\n")
        self.assert_violation(f"{SKILL_SOURCE}:7: link 'references/gone.md'")

    def test_links_may_target_rendered_templates_and_anchors(self) -> None:
        write(self.root, "src/skills/demo/references/extra.md.tmpl", "Extra.\n")
        links = "[e](references/extra.md#part) [a](#top) [w](https://example.com/a)\n"
        write(self.root, SKILL_SOURCE, SKILL + links)
        write(self.root, "src/skills/demo/references/note.md", "[up](note.md)\n")
        self.assertEqual(build.lint_violations(self.root), [])

    def test_escapes_and_install_paths_are_rejected(self) -> None:
        for forbidden in build.FORBIDDEN_IN_SKILLS:
            with self.subTest(forbidden):
                write(
                    self.root, "src/skills/demo/references/note.md", f"x {forbidden}y\n"
                )
                self.assert_violation(
                    f"src/skills/demo/references/note.md:1: '{forbidden}' is not allowed"
                )

    def test_agent_specific_terms_need_a_target_block(self) -> None:
        for term in build.AGENT_SPECIFIC_IN_SKILLS:
            with self.subTest(term):
                write(self.root, SKILL_SOURCE, SKILL + f"See {term}x.\n")
                self.assert_violation(
                    f"{SKILL_SOURCE}:7: '{term}' is only allowed inside a target block"
                )

    def test_agent_specific_terms_are_checked_in_copied_files(self) -> None:
        write(self.root, "src/skills/demo/references/note.md", "Load tao:demo.\n")
        self.assert_violation(
            "src/skills/demo/references/note.md:1: 'tao:' is only allowed"
        )

    def test_agent_specific_terms_are_allowed_in_a_target_block(self) -> None:
        block = (
            "<!-- target:claude -->\nLoad tao:demo. See CLAUDE.md.\n<!-- /target -->\n"
        )
        write(self.root, SKILL_SOURCE, SKILL + block)
        self.assertEqual(build.lint_violations(self.root), [])

    def test_readme_must_link_every_skill(self) -> None:
        write(self.root, build.README, "No skills listed.\n")
        self.assert_violation("README.md: does not link to skills/demo")

    def test_readme_must_exist(self) -> None:
        (self.root / build.README).unlink()
        self.assert_violation("README.md: missing")

    def test_malformed_markers_are_reported(self) -> None:
        write(self.root, SKILL_SOURCE, SKILL + "<!-- target:claude -->\n")
        self.assert_violation(
            f"{SKILL_SOURCE}:7: target block 'claude' is never closed"
        )

    def test_marketplace_must_list_one_plugin(self) -> None:
        write(self.root, build.CODEX.source_marketplace, '{"plugins": []}')
        self.assert_violation(
            "src/codex/marketplace.json: must list exactly one plugin"
        )

    def test_marketplace_source_and_name_must_match(self) -> None:
        marketplace = '{"plugins": [{"name": "other", "source": "./"}]}'
        write(self.root, build.CLAUDE.source_marketplace, marketplace)
        write(self.root, build.CODEX.source_marketplace, marketplace)
        self.assert_violation('plugin source must be "./plugins/claude/tao"')
        self.assert_violation("plugin name must match src/claude/plugin.json ('tao')")
        self.assert_violation(
            'plugin source must be {"source": "local", "path": "./plugins/codex/tao"}'
        )
        self.assert_violation("plugin name must match src/codex/plugin.json ('tao')")

    def test_plugin_versions_must_be_equal(self) -> None:
        write(self.root, build.CODEX.source_manifest, PLUGIN.replace("0.2.0", "0.3.0"))
        self.assert_violation(
            "src/codex/plugin.json: version '0.3.0' must equal '0.2.0' "
            "in src/claude/plugin.json"
        )

    def test_plugin_json_files_must_parse(self) -> None:
        write(self.root, "src/plugin/hooks/shared.json", "[]\n")
        write(self.root, "src/codex/hooks/hooks.json", '{\n  "hooks": \n}\n')
        self.assert_violation("src/plugin/hooks/shared.json:1: expected a JSON object")
        self.assert_violation("src/codex/hooks/hooks.json:3: ")

    def test_plugin_templates_need_well_formed_markers(self) -> None:
        write(self.root, "src/plugin/hooks/context.md.tmpl", "<!-- /target -->\n")
        self.assert_violation("src/plugin/hooks/context.md.tmpl:1: closing marker")

    def test_agent_files_must_not_name_the_other_agent(self) -> None:
        write(self.root, "src/claude/hooks/hooks.json", '{"c": "${PLUGIN_ROOT}/x"}\n')
        write(
            self.root, "src/codex/hooks/hooks.json", '{"c": "${CLAUDE_PLUGIN_ROOT}"}\n'
        )
        self.assert_violation(
            "src/claude/hooks/hooks.json:1: '${PLUGIN_ROOT}' is not allowed in src/claude"
        )
        self.assert_violation(
            "src/codex/hooks/hooks.json:1: 'CLAUDE_' is not allowed in src/codex"
        )

    def test_each_agent_may_name_its_own_variables(self) -> None:
        write(
            self.root, "src/claude/hooks/hooks.json", '{"c": "${CLAUDE_PLUGIN_ROOT}"}\n'
        )
        write(self.root, "src/codex/hooks/hooks.json", '{"c": "${PLUGIN_ROOT}"}\n')
        self.assertEqual(build.lint_violations(self.root), [])


class VersionTest(unittest.TestCase):
    def test_versions_compare_numerically(self) -> None:
        self.assertGreater(build.version_key("0.10.0"), build.version_key("0.9.9"))
        self.assertGreater(build.version_key("1.0.0"), build.version_key("0.99.99"))
        self.assertEqual(build.version_key("0.2.0"), (0, 2, 0))

    def test_version_must_be_three_numbers(self) -> None:
        for version in ('"1.2"', '"1.2.3-beta"', '"v1.2.3"', "1", "null"):
            with (
                self.subTest(version),
                self.assertRaisesRegex(build.BuildError, "X.Y.Z"),
            ):
                build.manifest_version(f'{{"version": {version}}}', "plugin.json")


class GitCase(SourceTreeCase):
    def setUp(self) -> None:
        super().setUp()
        git(self.root, "init", "-q", "-b", "main")

    def set_version(self, version: str) -> None:
        for plugin in build.PLUGINS:
            write(self.root, plugin.source_manifest, PLUGIN.replace("0.2.0", version))


class VersionCheckTest(GitCase):
    def setUp(self) -> None:
        super().setUp()
        self.build()
        commit_all(self.root, "base")
        git(self.root, "tag", "base")

    def change_plugin(self) -> None:
        write(self.root, SKILL_SOURCE, SKILL + "More.\n")

    def test_passes_when_the_plugin_is_unchanged(self) -> None:
        write(self.root, "README.md", "docs\n")
        commit_all(self.root, "docs")
        self.assertEqual(build.version_check(self.root, "base"), 0)

    def test_fails_when_the_plugin_changed_without_a_bump(self) -> None:
        self.change_plugin()
        self.build()
        commit_all(self.root, "change")
        message = r"version 0\.2\.0 must be greater than 0\.2\.0"
        with self.assertRaisesRegex(build.BuildError, message):
            build.version_check(self.root, "base")

    def test_fails_when_the_version_goes_down(self) -> None:
        self.set_version("0.1.9")
        self.build()
        commit_all(self.root, "downgrade")
        with self.assertRaisesRegex(build.BuildError, "must be greater than 0.2.0"):
            build.version_check(self.root, "base")

    def test_passes_when_the_plugin_changed_with_a_bump(self) -> None:
        self.change_plugin()
        self.set_version("0.10.0")
        self.build()
        commit_all(self.root, "change")
        self.assertEqual(build.version_check(self.root, "base"), 0)

    def test_each_plugin_is_checked_on_its_own(self) -> None:
        write(self.root, "src/codex/hooks/hooks.json", "{}\n")
        self.build()
        commit_all(self.root, "codex only")
        message = r"^plugins/codex/tao/\.codex-plugin/plugin\.json: version 0\.2\.0"
        with self.assertRaisesRegex(build.BuildError, message):
            build.version_check(self.root, "base")

    def test_reads_the_working_commit_not_the_working_tree(self) -> None:
        self.change_plugin()
        self.build()
        self.assertEqual(build.version_check(self.root, "base"), 0)

    def test_unknown_base_is_an_error(self) -> None:
        with self.assertRaises(subprocess.CalledProcessError):
            build.version_check(self.root, "no-such-ref")


class VersionCheckBaseLookupTest(GitCase):
    def test_falls_back_to_the_root_manifest_of_the_old_layout(self) -> None:
        write(self.root, build.CLAUDE.legacy_manifests[0], PLUGIN)
        commit_all(self.root, "old layout")
        git(self.root, "tag", "base")
        self.build()
        commit_all(self.root, "new layout, same version")
        with self.assertRaisesRegex(build.BuildError, "must be greater than 0.2.0"):
            build.version_check(self.root, "base")

    def test_passes_when_the_base_has_no_plugin_manifest(self) -> None:
        commit_all(self.root, "sources only")
        git(self.root, "tag", "base")
        self.build()
        commit_all(self.root, "first build")
        self.assertEqual(build.version_check(self.root, "base"), 0)


class SummaryTest(GitCase):
    def summary(self) -> str:
        code, stdout, _ = run(build.summary, self.root)
        self.assertEqual(code, 0)
        return stdout

    def test_reports_no_changes_after_a_committed_build(self) -> None:
        self.build()
        commit_all(self.root, "build")
        self.assertEqual(
            self.summary(),
            "## Build summary\n\n"
            "Plugin version: 0.2.0 (unchanged)\n\n"
            "| Skill | Generic | Claude | Codex |\n"
            "|---|---|---|---|\n"
            "| demo | — | — | — |\n\n"
            "Other changes: none\n",
        )

    def test_reports_changed_added_and_removed_skills(self) -> None:
        write(self.root, "src/skills/gone/SKILL.md.tmpl", SKILL.replace("demo", "gone"))
        write(self.root, "src/skills/gone/references/note.md", NOTE)
        self.build()
        commit_all(self.root, "build")

        claude_only = "<!-- target:claude -->\nClaude only.\n<!-- /target -->\n"
        write(self.root, SKILL_SOURCE, SKILL + claude_only)
        write(
            self.root, "src/skills/added/SKILL.md.tmpl", SKILL.replace("demo", "added")
        )
        write(self.root, "src/skills/added/references/note.md", NOTE)
        for source in sorted((self.root / "src/skills/gone").rglob("*"), reverse=True):
            source.rmdir() if source.is_dir() else source.unlink()
        (self.root / "src/skills/gone").rmdir()
        self.set_version("0.3.0")
        self.build()

        self.assertEqual(
            self.summary(),
            "## Build summary\n\n"
            "Plugin version: 0.2.0 → 0.3.0\n\n"
            "| Skill | Generic | Claude | Codex |\n"
            "|---|---|---|---|\n"
            "| added | changed | changed | changed |\n"
            "| demo | — | changed | — |\n"
            "| gone | changed | changed | changed |\n\n"
            "Other changes: plugins/claude/tao/.claude-plugin/plugin.json, "
            "plugins/codex/tao/.codex-plugin/plugin.json\n",
        )

    def test_reports_a_new_plugin_when_head_has_no_manifest(self) -> None:
        commit_all(self.root, "sources only")
        self.build()
        self.assertIn("Plugin version: 0.2.0 (new)\n", self.summary())


if __name__ == "__main__":
    unittest.main()
