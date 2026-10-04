# tao-of-agent

Agent skills following the [Vercel agent skills](https://vercel.com/docs/agent-resources/skills)
format. Each skill is a directory under `skills/` with a `SKILL.md`.

## Skills

| Skill | Description |
| --- | --- |
| [`minimal-code`](skills/minimal-code) | Write the smallest correct, readable, tested change — KISS, YAGNI, DRY, explicit errors, TDD. |
| [`git-hygiene`](skills/git-hygiene) | Keep Git history easy to review during development and meaningful after merge. |
| [`natural-clear-writing`](skills/natural-clear-writing) | Write or edit prose without formulaic AI phrasing, with extra rules for Korean. |

## Install

### As a Claude Code plugin

The repository is a plugin marketplace that ships one plugin, `tao`, containing every
skill above. Inside Claude Code:

```text
/plugin marketplace add recursivecurry/tao-of-agent
/plugin install tao@tao-of-agent
```

Plugin skills are namespaced: `tao:minimal-code`, `tao:git-hygiene`, `tao:natural-clear-writing`.

### With the skills CLI

The [skills CLI](https://vercel.com/docs/agent-resources/skills) installs skills into any
supported agent, Claude Code included. Install every skill in the repository:

```bash
npx skills add recursivecurry/tao-of-agent
```

Or pick one:

```bash
npx skills add recursivecurry/tao-of-agent --skill minimal-code
npx skills add recursivecurry/tao-of-agent --skill git-hygiene
npx skills add recursivecurry/tao-of-agent --skill natural-clear-writing
```

Add `-g` to install globally, or `-a claude-code` to target a specific agent. Skills installed
this way keep their plain names (`minimal-code`, `git-hygiene`, `natural-clear-writing`).

### Manually

For Claude Code, copy any skill directory, with its `references/` subdirectory if it has one:

```bash
cp -r skills/minimal-code ~/.claude/skills/
cp -r skills/natural-clear-writing ~/.claude/skills/
```

## Making `minimal-code` always apply

An agent loads a skill only when it judges the skill relevant, and it loads it at the *start*
of a task — not at the end, where the pre-flight checklist matters most. Coding principles are
meant to hold on every change, so back the skill with a pointer in your project's `CLAUDE.md`
(or `AGENTS.md`):

```markdown
Follow the minimal-code skill when writing or changing code.

Load it before making code changes. Before reporting a change as done, read
references/done-checklist.md from the skill directory and work through it.
```

The skill holds the detail; the pointer is what gets it consulted at the two moments that
decide whether the change stays small. The completion checklist lives in its own file so the
second moment costs a short read, not a reload of the whole skill.

## Making `natural-clear-writing` govern chat replies

The skill loads only for writing and editing tasks, not for ordinary replies. If you want the
same standard on every reply, put the short form in `CLAUDE.md`:

```markdown
Lead replies with the answer. No staged openers, empty contrasts, forced triads,
dramatic closers, or Markdown decoration. Load natural-clear-writing when
writing or editing prose, docs, commit messages, or UI strings.
```

## Evals

`evals/` holds cases for `natural-clear-writing`: an English doc, a Korean doc, a bilingual
note, UI strings with placeholders, and a commit message. Each case has an LLM grader that
checks formulaic phrasing is gone and every fact, placeholder, and register survives.

```bash
tools/eval.sh --judge-model sonnet
```

The default judge (haiku) misreads the Korean criteria, so pass a stronger judge. The run also
scores a no-plugin baseline and reports the delta, which is the number to watch when editing
the skill. Results land in `evals/results/`, which is ignored by git.

`claude plugin eval` reads cases only from inside the plugin directory, and the cases are not
shipped with the plugin. The script rebuilds the outputs, copies `plugins/tao/` and `evals/`
into a temporary directory, and runs the eval there. Extra arguments are passed through. Do
not run `claude plugin eval .` at the repository root: it finds the cases but loads no plugin.

## Repository layout

```text
src/skills/<skill>/SKILL.md.tmpl   skill sources: edit here
src/claude/                        plugin and marketplace manifests
tools/build.py                     generates the three directories below
skills/                            generated, read by the skills CLI
plugins/tao/                       generated, the Claude Code plugin
.claude-plugin/marketplace.json    generated
evals/                             eval cases, not shipped
```

`skills/`, `plugins/tao/`, and `.claude-plugin/` are build output. They are committed because
both installers read the default branch. The build deletes any file in them that it did not
produce, so hand edits and extra files there do not survive.

## Contributing

1. Edit files under `src/`. A `.tmpl` file is rendered once per distribution, and everything
   else is copied as it is. Both distributions get the same text unless a template uses a
   target block:

   ```markdown
   <!-- target:claude -->
   This line appears only in the Claude Code plugin.
   <!-- /target -->
   ```

   The targets are `claude` and `generic`. A marker must be a whole line, and blocks do not
   nest.
2. If the change affects a skill, raise `version` in `src/claude/plugin.json`. Installed
   plugins update only when the version changes, and the version check fails the build PR
   without it.
3. Run the checks:

   ```bash
   python3 -m unittest discover -s tools
   python3 tools/build.py lint
   ```

4. Open a pull request with the `src/` changes. You do not need to commit generated files. If
   you do, run `python3 tools/build.py build` first so that `python3 tools/build.py check`
   passes.

After the pull request merges, a workflow opens a "Release: regenerate distributions" pull
request with the rebuilt outputs. Merging that one is the release.
[docs/release-setup.md](docs/release-setup.md) describes the one-time setup it needs.
