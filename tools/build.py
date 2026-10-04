"""Generate the generic skills and the Claude Code plugin from src/."""

import argparse
import difflib
import io
import json
import posixpath
import re
import stat
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path, PurePath

SRC_SKILLS = "src/skills"
SRC_PLUGIN_MANIFEST = "src/claude/plugin.json"
SRC_MARKETPLACE_MANIFEST = "src/claude/marketplace.json"

PLUGIN_ROOT = "plugins/tao"
PLUGIN_MANIFEST = f"{PLUGIN_ROOT}/.claude-plugin/plugin.json"
MARKETPLACE_MANIFEST = ".claude-plugin/marketplace.json"
LEGACY_PLUGIN_MANIFEST = ".claude-plugin/plugin.json"
MARKETPLACE_PLUGIN_SOURCE = f"./{PLUGIN_ROOT}"

SKILL_ROOTS = {"generic": "skills", "claude": f"{PLUGIN_ROOT}/skills"}
OWNED_ROOTS = ("skills", PLUGIN_ROOT, ".claude-plugin")

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


def skill_outputs(root: Path, skill_dir: Path) -> Iterator[tuple[str, Output]]:
    for source in source_files(skill_dir):
        path = source.relative_to(root).as_posix()
        name = output_name(source.relative_to(skill_dir))
        executable = is_executable(source)
        for target, skill_root in SKILL_ROOTS.items():
            if is_template(source):
                notice = source == skill_dir / SKILL_TEMPLATE
                content = render_template(
                    read_text(root, path), target, path, notice=notice
                )
            else:
                content = source.read_bytes()
            yield f"{skill_root}/{skill_dir.name}/{name}", Output(content, executable)


def manifest_outputs(root: Path) -> Iterator[tuple[str, Output]]:
    manifests = (
        (SRC_PLUGIN_MANIFEST, PLUGIN_MANIFEST),
        (SRC_MARKETPLACE_MANIFEST, MARKETPLACE_MANIFEST),
    )
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
    for path, output in [*produced, *manifest_outputs(root)]:
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
        if is_template(source):
            skill = skill_dir.name if source == skill_template else None
            yield from lint_template(path, text, skill)


def lint_manifests(root: Path) -> Iterator[BuildError]:
    try:
        plugin = parse_json_object(
            read_text(root, SRC_PLUGIN_MANIFEST), SRC_PLUGIN_MANIFEST
        )
        marketplace = parse_json_object(
            read_text(root, SRC_MARKETPLACE_MANIFEST), SRC_MARKETPLACE_MANIFEST
        )
    except BuildError as error:
        yield error
        return
    plugins = marketplace.get("plugins")
    if (
        not isinstance(plugins, list)
        or len(plugins) != 1
        or not isinstance(plugins[0], dict)
    ):
        yield BuildError(SRC_MARKETPLACE_MANIFEST, "must list exactly one plugin")
        return
    entry = plugins[0]
    if entry.get("source") != MARKETPLACE_PLUGIN_SOURCE:
        yield BuildError(
            SRC_MARKETPLACE_MANIFEST,
            f'plugin source must be "{MARKETPLACE_PLUGIN_SOURCE}"',
        )
    if entry.get("name") != plugin.get("name"):
        message = (
            f"plugin name must match {SRC_PLUGIN_MANIFEST} ('{plugin.get('name')}')"
        )
        yield BuildError(SRC_MARKETPLACE_MANIFEST, message)


def lint_violations(root: Path) -> list[str]:
    violations = [
        violation
        for skill_dir in skill_dirs(root)
        for violation in lint_skill(root, skill_dir)
    ]
    violations += lint_manifests(root)
    # Both targets report the same violation when a template has no target blocks.
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


def plugin_version_at(root: Path, ref: str) -> str | None:
    for path in (PLUGIN_MANIFEST, LEGACY_PLUGIN_MANIFEST):
        text = file_at(root, ref, path)
        if text is not None:
            return manifest_version(text, f"{ref}:{path}")
    return None


def version_check(root: Path, base: str) -> int:
    if not git(root, "diff", "--name-only", base, "HEAD", "--", PLUGIN_ROOT):
        return 0
    base_version = plugin_version_at(root, base)
    if base_version is None:
        return 0
    head_manifest = file_at(root, "HEAD", PLUGIN_MANIFEST)
    if head_manifest is None:
        raise BuildError(PLUGIN_MANIFEST, "missing at HEAD")
    head_version = manifest_version(head_manifest, PLUGIN_MANIFEST)
    if version_key(head_version) <= version_key(base_version):
        message = (
            f"version {head_version} must be greater than {base_version} "
            f"because {PLUGIN_ROOT}/ changed; bump it in {SRC_PLUGIN_MANIFEST}"
        )
        raise BuildError(PLUGIN_MANIFEST, message)
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
    current = manifest_version(read_text(root, PLUGIN_MANIFEST), PLUGIN_MANIFEST)
    previous = plugin_version_at(root, "HEAD")
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
    commands.add_parser(
        "check", help="fail with a diff if the generated files are stale"
    )
    commands.add_parser("lint", help="check src/ against the source rules")
    commands.add_parser(
        "summary", help="print a Markdown summary of generated changes since HEAD"
    )
    version_parser = commands.add_parser(
        "version-check", help="require a plugin version bump when the plugin changed"
    )
    version_parser.add_argument(
        "--base", required=True, help="git ref to compare HEAD against"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    arguments = parse_arguments(argv)
    root = Path.cwd()
    commands = {"build": build, "check": check, "lint": lint, "summary": summary}
    try:
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
