"""Generate the generic skills and the Claude Code and Codex plugins from src/."""

import argparse
import difflib
import io
import json
import posixpath
import re
import shutil
import stat
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path, PurePath

SRC_SKILLS = "src/skills"
README = "README.md"
SRC_SHARED_PLUGIN_FILES = "src/plugin"


@dataclass(frozen=True)
class Plugin:
    target: str
    source: str
    root: str
    manifest: str
    marketplace: str
    marketplace_source: str | dict[str, str]
    legacy_manifests: tuple[str, ...]
    forbidden: tuple[str, ...]

    @property
    def source_manifest(self) -> str:
        return f"{self.source}/plugin.json"

    @property
    def source_marketplace(self) -> str:
        return f"{self.source}/marketplace.json"


CLAUDE = Plugin(
    target="claude",
    source="src/claude",
    root="plugins/claude/tao",
    manifest="plugins/claude/tao/.claude-plugin/plugin.json",
    marketplace=".claude-plugin/marketplace.json",
    marketplace_source="./plugins/claude/tao",
    legacy_manifests=(".claude-plugin/plugin.json",),
    forbidden=("${PLUGIN_ROOT}", "CODEX_", ".codex"),
)
CODEX = Plugin(
    target="codex",
    source="src/codex",
    root="plugins/codex/tao",
    manifest="plugins/codex/tao/.codex-plugin/plugin.json",
    marketplace=".agents/plugins/marketplace.json",
    marketplace_source={"source": "local", "path": "./plugins/codex/tao"},
    legacy_manifests=(),
    forbidden=("CLAUDE_", ".claude"),
)
PLUGINS = (CLAUDE, CODEX)

SKILL_ROOTS = {
    "generic": "skills",
    **{plugin.target: f"{plugin.root}/skills" for plugin in PLUGINS},
}
# .agents/skills is where the skills CLI installs project skills, so only
# .agents/plugins is owned.
OWNED_ROOTS = ("skills", "plugins", ".claude-plugin", ".agents/plugins")

TEMPLATE_SUFFIX = ".tmpl"
SKILL_TEMPLATE = "SKILL.md.tmpl"
FRONTMATTER_FENCE = "---"
REQUIRED_FIELDS = ("name", "description")
GENERATED_NOTICE = "# Generated from {source}. Edit the source, not this file.\n"

MARKER = re.compile(r"[ \t]*<!-- (?:/target|target:(?P<target>\S*)) -->[ \t]*\n?")
FIELD = re.compile(r"(?P<key>[A-Za-z_][\w-]*):(?P<value>.*)")
LINK = re.compile(r"\]\(([^)\s]+)\)")
SKILL_NAME = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
VERSION = re.compile(r"\d+\.\d+\.\d+")

FORBIDDEN_IN_SKILLS = ("](../", "](/", ".claude/", ".agents/", ".codex/", "~/.")
# A skill is `tao:<name>` only in a plugin, and each agent reads its own
# instruction file, so these belong in a target block.
AGENT_SPECIFIC_IN_SKILLS = ("tao:", "CLAUDE.md", "AGENTS.md")
ESCAPING_LINK_PREFIXES = ("/", "../")
EXTERNAL_LINK_PREFIXES = ("#", "mailto:")

EXECUTABLE_MODE = 0o755
REGULAR_MODE = 0o644


class BuildError(Exception):
    def __init__(self, path: str, message: str, line: int | None = None) -> None:
        location = path if line is None else f"{path}:{line}"
        super().__init__(f"{location}: {message}")


@dataclass(frozen=True)
class Output:
    content: bytes
    executable: bool


def read_text(root: Path, path: str) -> str:
    try:
        return (root / path).read_bytes().decode().replace("\r\n", "\n")
    except UnicodeDecodeError as error:
        raise BuildError(path, f"not valid UTF-8: {error.reason}") from error


def parse_json_object(text: str, path: str) -> dict:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise BuildError(path, error.msg, error.lineno) from error
    if not isinstance(data, dict):
        raise BuildError(path, "expected a JSON object", 1)
    return data


def render_lines(text: str, target: str, path: str) -> list[tuple[int, str]]:
    """Return the numbered source lines that belong to target, without markers."""
    kept = []
    open_target = None
    open_line = 0
    for number, line in enumerate(io.StringIO(text), start=1):
        marker = MARKER.fullmatch(line)
        if marker is None:
            if open_target in (None, target):
                kept.append((number, line))
            continue
        name = marker["target"]
        if name is None:
            if open_target is None:
                raise BuildError(path, "closing marker without an open block", number)
            open_target = None
            continue
        if name not in SKILL_ROOTS:
            raise BuildError(path, f"unknown target '{name}'", number)
        if open_target is not None:
            raise BuildError(path, "target blocks cannot be nested", number)
        open_target, open_line = name, number
    if open_target is not None:
        raise BuildError(
            path, f"target block '{open_target}' is never closed", open_line
        )
    return kept


def render_template(text: str, target: str, path: str, *, notice: bool) -> bytes:
    lines = [line for _, line in render_lines(text, target, path)]
    if notice:
        if not lines or lines[0].rstrip("\n") != FRONTMATTER_FENCE:
            raise BuildError(path, "frontmatter must open on line 1 with ---", 1)
        lines.insert(1, GENERATED_NOTICE.format(source=path))
    return "".join(lines).encode()


def skill_dirs(root: Path) -> list[Path]:
    return sorted(path for path in (root / SRC_SKILLS).iterdir() if path.is_dir())


def source_files(directory: Path) -> list[Path]:
    return sorted(path for path in directory.rglob("*") if path.is_file())


def is_template(source: PurePath) -> bool:
    return source.suffix == TEMPLATE_SUFFIX


def output_name(relative: PurePath) -> str:
    stripped = relative.with_suffix("") if is_template(relative) else relative
    return stripped.as_posix()


def tree_outputs(
    root: Path,
    directory: Path,
    sources: list[Path],
    destinations: dict[str, str],
    notice_for: Path | None = None,
) -> Iterator[tuple[str, Output]]:
    """Yield each source once per target, placed under that target's destination."""
    for source in sources:
        path = source.relative_to(root).as_posix()
        name = output_name(source.relative_to(directory))
        executable = is_executable(source)
        for target, destination in destinations.items():
            if is_template(source):
                content = render_template(
                    read_text(root, path), target, path, notice=source == notice_for
                )
            else:
                content = source.read_bytes()
            yield f"{destination}/{name}", Output(content, executable)


def skill_outputs(root: Path, skill_dir: Path) -> Iterator[tuple[str, Output]]:
    destinations = {
        target: f"{skill_root}/{skill_dir.name}"
        for target, skill_root in SKILL_ROOTS.items()
    }
    return tree_outputs(
        root,
        skill_dir,
        source_files(skill_dir),
        destinations,
        notice_for=skill_dir / SKILL_TEMPLATE,
    )


def agent_files(root: Path, plugin: Plugin) -> list[Path]:
    """Return the files in the plugin's source directory other than its manifests."""
    manifests = {root / plugin.source_manifest, root / plugin.source_marketplace}
    return [
        source
        for source in source_files(root / plugin.source)
        if source not in manifests
    ]


def plugin_file_outputs(root: Path) -> Iterator[tuple[str, Output]]:
    shared = root / SRC_SHARED_PLUGIN_FILES
    plugin_roots = {plugin.target: plugin.root for plugin in PLUGINS}
    yield from tree_outputs(root, shared, source_files(shared), plugin_roots)
    for plugin in PLUGINS:
        yield from tree_outputs(
            root,
            root / plugin.source,
            agent_files(root, plugin),
            {plugin.target: plugin.root},
        )


def manifest_outputs(root: Path) -> Iterator[tuple[str, Output]]:
    manifests = [
        pair
        for plugin in PLUGINS
        for pair in (
            (plugin.source_manifest, plugin.manifest),
            (plugin.source_marketplace, plugin.marketplace),
        )
    ]
    for source, output in manifests:
        parse_json_object(read_text(root, source), source)
        yield output, Output((root / source).read_bytes(), executable=False)


def expected_outputs(root: Path) -> dict[str, Output]:
    outputs: dict[str, Output] = {}
    produced = [
        output
        for skill_dir in skill_dirs(root)
        for output in skill_outputs(root, skill_dir)
    ]
    produced += [*plugin_file_outputs(root), *manifest_outputs(root)]
    for path, output in produced:
        if path in outputs:
            raise BuildError(path, "two source files produce this output")
        outputs[path] = output
    return dict(sorted(outputs.items()))


def files_on_disk(root: Path) -> set[str]:
    return {
        path.relative_to(root).as_posix()
        for owned in OWNED_ROOTS
        for path in (root / owned).rglob("*")
        if path.is_file() or path.is_symlink()
    }


def is_executable(file: Path) -> bool:
    return bool(file.stat().st_mode & stat.S_IXUSR)


def is_current(file: Path, output: Output) -> bool:
    return (
        file.is_file()
        and not file.is_symlink()
        and file.read_bytes() == output.content
        and is_executable(file) == output.executable
    )


def remove_empty_directories(root: Path) -> None:
    for owned in OWNED_ROOTS:
        for directory in sorted((root / owned).rglob("*"), reverse=True):
            if directory.is_dir() and not any(directory.iterdir()):
                directory.rmdir()


def build(root: Path) -> int:
    outputs = expected_outputs(root)
    for path, output in outputs.items():
        file = root / path
        if is_current(file, output):
            continue
        file.parent.mkdir(parents=True, exist_ok=True)
        file.unlink(missing_ok=True)
        file.write_bytes(output.content)
        file.chmod(EXECUTABLE_MODE if output.executable else REGULAR_MODE)
        print(f"wrote {path}")
    for path in sorted(files_on_disk(root) - outputs.keys()):
        (root / path).unlink()
        print(f"removed {path}")
    remove_empty_directories(root)
    return 0


def describe_stale(file: Path, path: str, output: Output) -> str | None:
    if not file.is_file() or file.is_symlink():
        return f"missing: {path}\n"
    actual = file.read_bytes()
    if actual != output.content:
        try:
            before, after = actual.decode(), output.content.decode()
        except UnicodeDecodeError:
            return f"differs (binary): {path}\n"
        diff = difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=path,
            tofile=f"{path} (from src)",
        )
        return "".join(diff)
    if is_executable(file) != output.executable:
        return f"wrong executable bit: {path}\n"
    return None


def check(root: Path) -> int:
    outputs = expected_outputs(root)
    stale = [
        describe_stale(root / path, path, output) for path, output in outputs.items()
    ]
    extra = [
        f"not generated from src: {path}\n"
        for path in sorted(files_on_disk(root) - outputs.keys())
    ]
    problems = [problem for problem in [*stale, *extra] if problem is not None]
    if not problems:
        return 0
    sys.stdout.write("".join(problems))
    print(
        "Generated files are out of date. Run: python3 tools/build.py build",
        file=sys.stderr,
    )
    return 1


def lint_frontmatter(
    path: str, lines: list[tuple[int, str]], skill: str
) -> Iterator[BuildError]:
    if not lines or lines[0][1].rstrip("\n") != FRONTMATTER_FENCE:
        yield BuildError(path, "frontmatter must open on line 1 with ---", 1)
        return
    fields: dict[str, tuple[int, str]] = {}
    for number, line in lines[1:]:
        if line.rstrip("\n") == FRONTMATTER_FENCE:
            break
        field = FIELD.match(line)
        if field is not None:
            fields[field["key"]] = (number, field["value"].strip().strip("\"'"))
    else:
        yield BuildError(path, "frontmatter is not closed with ---", 1)
        return
    for key in REQUIRED_FIELDS:
        if not fields.get(key, (0, ""))[1]:
            yield BuildError(path, f"frontmatter has no {key}", 1)
    number, name = fields.get("name", (0, ""))
    if name and (name != skill or SKILL_NAME.fullmatch(name) is None):
        message = f"name '{name}' must equal the directory name '{skill}' and match {SKILL_NAME.pattern}"
        yield BuildError(path, message, number)


def lint_template(path: str, text: str, skill: str | None) -> Iterator[BuildError]:
    """Check markers, and the frontmatter of each rendering when skill is given."""
    for target in SKILL_ROOTS:
        try:
            lines = render_lines(text, target, path)
        except BuildError as error:
            yield error
            return
        if skill is not None:
            yield from lint_frontmatter(path, lines, skill)


def lint_text(
    path: str, text: str, directory: str, skill_files: set[str]
) -> Iterator[BuildError]:
    for number, line in enumerate(io.StringIO(text), start=1):
        for forbidden in FORBIDDEN_IN_SKILLS:
            if forbidden in line:
                yield BuildError(
                    path, f"'{forbidden}' is not allowed in skill files", number
                )
        for link in LINK.findall(line):
            # Escaping links are already reported through FORBIDDEN_IN_SKILLS.
            if "://" in link or link.startswith(
                EXTERNAL_LINK_PREFIXES + ESCAPING_LINK_PREFIXES
            ):
                continue
            resolved = posixpath.normpath(posixpath.join(directory, link.split("#")[0]))
            if resolved not in skill_files:
                yield BuildError(
                    path,
                    f"link '{link}' does not resolve to a file in this skill",
                    number,
                )


def lint_shared_lines(path: str, text: str, *, template: bool) -> Iterator[BuildError]:
    """Check the lines that every target receives."""
    lines = list(enumerate(io.StringIO(text), start=1))
    if template:
        try:
            renderings = [
                set(render_lines(text, target, path)) for target in SKILL_ROOTS
            ]
        except BuildError:
            # lint_template reports the malformed marker.
            return
        lines = sorted(set.intersection(*renderings))
    for number, line in lines:
        for term in AGENT_SPECIFIC_IN_SKILLS:
            if term in line:
                yield BuildError(
                    path, f"'{term}' is only allowed inside a target block", number
                )


def lint_skill(root: Path, skill_dir: Path) -> Iterator[BuildError]:
    sources = source_files(skill_dir)
    skill_files = {output_name(source.relative_to(skill_dir)) for source in sources}
    skill_template = skill_dir / SKILL_TEMPLATE
    if skill_template not in sources:
        yield BuildError(
            skill_dir.relative_to(root).as_posix(), f"missing {SKILL_TEMPLATE}"
        )
    for source in sources:
        path = source.relative_to(root).as_posix()
        try:
            text = read_text(root, path)
        except BuildError as error:
            if is_template(source):
                yield error
            continue
        directory = source.parent.relative_to(skill_dir).as_posix()
        yield from lint_text(path, text, directory, skill_files)
        yield from lint_shared_lines(path, text, template=is_template(source))
        if is_template(source):
            skill = skill_dir.name if source == skill_template else None
            yield from lint_template(path, text, skill)


def lint_marketplace(
    plugin: Plugin, manifest: dict, marketplace: dict
) -> Iterator[BuildError]:
    plugins = marketplace.get("plugins")
    if (
        not isinstance(plugins, list)
        or len(plugins) != 1
        or not isinstance(plugins[0], dict)
    ):
        yield BuildError(plugin.source_marketplace, "must list exactly one plugin")
        return
    entry = plugins[0]
    if entry.get("source") != plugin.marketplace_source:
        yield BuildError(
            plugin.source_marketplace,
            f"plugin source must be {json.dumps(plugin.marketplace_source)}",
        )
    if entry.get("name") != manifest.get("name"):
        message = (
            f"plugin name must match {plugin.source_manifest} "
            f"('{manifest.get('name')}')"
        )
        yield BuildError(plugin.source_marketplace, message)


def lint_manifests(root: Path) -> Iterator[BuildError]:
    versions = {}
    for plugin in PLUGINS:
        try:
            manifest = parse_json_object(
                read_text(root, plugin.source_manifest), plugin.source_manifest
            )
            marketplace = parse_json_object(
                read_text(root, plugin.source_marketplace), plugin.source_marketplace
            )
        except BuildError as error:
            yield error
            continue
        versions[plugin.target] = manifest.get("version")
        yield from lint_marketplace(plugin, manifest, marketplace)
    if len(set(versions.values())) > 1:
        message = (
            f"version {versions[CODEX.target]!r} must equal "
            f"{versions[CLAUDE.target]!r} in {CLAUDE.source_manifest}"
        )
        yield BuildError(CODEX.source_manifest, message)


def lint_plugin_file(
    root: Path, source: Path, directory: str, forbidden: tuple[str, ...]
) -> Iterator[BuildError]:
    path = source.relative_to(root).as_posix()
    try:
        text = read_text(root, path)
    except BuildError as error:
        if is_template(source):
            yield error
        return
    for number, line in enumerate(io.StringIO(text), start=1):
        for term in forbidden:
            if term in line:
                yield BuildError(
                    path, f"'{term}' is not allowed in {directory}", number
                )
    if is_template(source):
        yield from lint_template(path, text, None)
    elif source.suffix == ".json":
        try:
            parse_json_object(text, path)
        except BuildError as error:
            yield error


def lint_plugin_files(root: Path) -> Iterator[BuildError]:
    directories: list[tuple[str, tuple[str, ...]]] = [(SRC_SHARED_PLUGIN_FILES, ())]
    directories += [(plugin.source, plugin.forbidden) for plugin in PLUGINS]
    for directory, forbidden in directories:
        for source in source_files(root / directory):
            yield from lint_plugin_file(root, source, directory, forbidden)


def lint_readme(root: Path) -> Iterator[BuildError]:
    try:
        readme = read_text(root, README)
    except OSError:
        yield BuildError(README, "missing")
        return
    for skill_dir in skill_dirs(root):
        link = f"(skills/{skill_dir.name})"
        if link not in readme:
            yield BuildError(README, f"does not link to {link[1:-1]}")


def lint_violations(root: Path) -> list[str]:
    violations = [
        violation
        for skill_dir in skill_dirs(root)
        for violation in lint_skill(root, skill_dir)
    ]
    violations += lint_manifests(root)
    violations += lint_plugin_files(root)
    violations += lint_readme(root)
    # Every target reports the same violation when a template has no target blocks.
    return list(dict.fromkeys(str(violation) for violation in violations))


def lint(root: Path) -> int:
    violations = lint_violations(root)
    for violation in violations:
        print(violation, file=sys.stderr)
    return 1 if violations else 0


def git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=root, check=True, capture_output=True, text=True
    )
    return result.stdout


def file_at(root: Path, ref: str, path: str) -> str | None:
    if not git(root, "ls-tree", "--name-only", ref, "--", path):
        return None
    return git(root, "show", f"{ref}:{path}")


def manifest_version(text: str, path: str) -> str:
    version = parse_json_object(text, path).get("version")
    if not isinstance(version, str) or VERSION.fullmatch(version) is None:
        raise BuildError(path, f"version must be X.Y.Z, found {version!r}")
    return version


def version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def plugin_version_at(root: Path, ref: str, plugin: Plugin) -> str | None:
    for path in (plugin.manifest, *plugin.legacy_manifests):
        text = file_at(root, ref, path)
        if text is not None:
            return manifest_version(text, f"{ref}:{path}")
    return None


def check_plugin_version(root: Path, base: str, plugin: Plugin) -> None:
    if not git(root, "diff", "--name-only", base, "HEAD", "--", plugin.root):
        return
    base_version = plugin_version_at(root, base, plugin)
    if base_version is None:
        return
    head_manifest = file_at(root, "HEAD", plugin.manifest)
    if head_manifest is None:
        raise BuildError(plugin.manifest, "missing at HEAD")
    head_version = manifest_version(head_manifest, plugin.manifest)
    if version_key(head_version) <= version_key(base_version):
        message = (
            f"version {head_version} must be greater than {base_version} "
            f"because {plugin.root}/ changed; bump it in {plugin.source_manifest}"
        )
        raise BuildError(plugin.manifest, message)


def version_check(root: Path, base: str) -> int:
    for plugin in PLUGINS:
        check_plugin_version(root, base, plugin)
    return 0


def changed_paths(root: Path) -> list[str]:
    status = git(
        root,
        "status",
        "--porcelain",
        "-z",
        "--no-renames",
        "--untracked-files=all",
        "--",
        *OWNED_ROOTS,
    )
    status_prefix_length = len("XY ")
    return sorted(entry[status_prefix_length:] for entry in status.split("\0") if entry)


def skill_of(path: str) -> tuple[str, str] | None:
    """Return (target, skill) for a path inside a generated skill directory."""
    for target, skill_root in SKILL_ROOTS.items():
        prefix = f"{skill_root}/"
        if path.startswith(prefix) and "/" in path.removeprefix(prefix):
            return target, path.removeprefix(prefix).split("/")[0]
    return None


def describe_version_change(root: Path) -> str:
    # Lint keeps the Codex version equal to this one.
    current = manifest_version(read_text(root, CLAUDE.manifest), CLAUDE.manifest)
    previous = plugin_version_at(root, "HEAD", CLAUDE)
    if previous is None:
        return f"{current} (new)"
    if previous == current:
        return f"{current} (unchanged)"
    return f"{previous} → {current}"


def summary(root: Path) -> int:
    changed = changed_paths(root)
    changed_skills = {skill_of(path) for path in changed} - {None}
    generated_skills = {
        path.name
        for skill_root in SKILL_ROOTS.values()
        for path in (root / skill_root).glob("*")
        if path.is_dir()
    }
    skills = sorted(generated_skills | {skill for _, skill in changed_skills})
    other = [path for path in changed if skill_of(path) is None]

    print("## Build summary\n")
    print(f"Plugin version: {describe_version_change(root)}\n")
    print(f"| Skill | {' | '.join(target.capitalize() for target in SKILL_ROOTS)} |")
    print(f"|---|{'---|' * len(SKILL_ROOTS)}")
    for skill in skills:
        cells = [
            "changed" if (target, skill) in changed_skills else "—"
            for target in SKILL_ROOTS
        ]
        print(f"| {skill} | {' | '.join(cells)} |")
    print(f"\nOther changes: {', '.join(other) or 'none'}")
    return 0


def parse_arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("build", help="write the generated files and delete extras")
    stage_parser = commands.add_parser(
        "stage", help="build a copy of src/ in a temporary directory"
    )
    stage_parser.add_argument("directory", type=Path)
    commands.add_parser(
        "check", help="fail with a diff if the generated files are stale"
    )
    commands.add_parser("lint", help="check src/ against the source rules")
    commands.add_parser(
        "summary", help="print a Markdown summary of generated changes since HEAD"
    )
    version_parser = commands.add_parser(
        "version-check", help="require a plugin version bump when a plugin changed"
    )
    version_parser.add_argument(
        "--base", required=True, help="git ref to compare HEAD against"
    )
    return parser.parse_args(argv)


def stage(root: Path, directory: Path) -> int:
    shutil.copytree(root / "src", directory / "src")
    return build(directory)


def main(argv: list[str] | None = None) -> int:
    arguments = parse_arguments(argv)
    root = Path.cwd()
    commands = {"build": build, "check": check, "lint": lint, "summary": summary}
    try:
        if arguments.command == "stage":
            return stage(root, arguments.directory)
        if arguments.command == "version-check":
            return version_check(root, arguments.base)
        return commands[arguments.command](root)
    except subprocess.CalledProcessError as error:
        print(error.stderr.strip() or error, file=sys.stderr)
    except (BuildError, OSError) as error:
        print(error, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
