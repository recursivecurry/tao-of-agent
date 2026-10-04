# tao-of-agent

[한국어](README.ko.md)

Agent skills following the [Vercel agent skills](https://vercel.com/docs/agent-resources/skills)
format. Each skill is a directory under `skills/` with a `SKILL.md`.

## Skills

| Skill | Description |
| --- | --- |
| [`minimal-code`](skills/minimal-code) | Write the smallest correct, readable, tested change — KISS, YAGNI, DRY, explicit errors, TDD. |
| [`git-hygiene`](skills/git-hygiene) | Keep Git history easy to review during development and meaningful after merge. |
| [`independent-review`](skills/independent-review) | Review pushed code in a fresh background context and report supported defects. |
| [`natural-clear-writing`](skills/natural-clear-writing) | Write or edit prose without formulaic AI phrasing, with extra rules for Korean. |

## Install

### As a Claude Code plugin

The repository is a plugin marketplace that ships one plugin, `tao`, containing every
skill above. Inside Claude Code:

```text
/plugin marketplace add recursivecurry/tao-of-agent
/plugin install tao@tao-of-agent
```

Plugin skills are namespaced: `tao:minimal-code`, `tao:git-hygiene`,
`tao:independent-review`, `tao:natural-clear-writing`.

### As a Codex plugin

The repository is also a Codex marketplace with its own `tao` plugin, built for Codex:

```bash
codex plugin marketplace add recursivecurry/tao-of-agent
codex plugin add tao@tao-of-agent
```

The plugin includes a hook, and Codex runs a plugin's hooks only after you approve them. It
shows the review screen at the start of the next session. The skills work without the
approval. The hook does not.

To update later:

```bash
codex plugin marketplace upgrade tao-of-agent
codex plugin add tao@tao-of-agent
```

### With the skills CLI

The [skills CLI](https://vercel.com/docs/agent-resources/skills) installs skills into any
supported agent. Use it for agents that have no plugin above. Installing both a plugin and
these skills into the same agent loads every skill twice, once as `tao:minimal-code` and once
as `minimal-code`, so pick one. Install every skill in the repository:

```bash
npx skills add recursivecurry/tao-of-agent
```

Or pick one:

```bash
npx skills add recursivecurry/tao-of-agent --skill minimal-code
npx skills add recursivecurry/tao-of-agent --skill git-hygiene
npx skills add recursivecurry/tao-of-agent --skill independent-review
npx skills add recursivecurry/tao-of-agent --skill natural-clear-writing
```

Add `-g` to install globally, or `-a claude-code` to target a specific agent. Skills installed
this way keep their plain names (`minimal-code`, `git-hygiene`, `independent-review`,
`natural-clear-writing`).

### Manually

For Claude Code, copy the complete skill directory, including any scripts and references:

```bash
cp -r skills/minimal-code ~/.claude/skills/
cp -r skills/independent-review ~/.claude/skills/
cp -r skills/natural-clear-writing ~/.claude/skills/
```

## What the plugins add

Both plugins run a hook at the start of every session that adds instructions: follow
`tao:minimal-code` when changing code and work through its done checklist before reporting
done, keep ordinary replies free of formulaic phrasing, and run an independent background
review after successful pushes. The sections below explain
why, and give the same text to paste by hand if you installed the skills without a plugin.

## Making `minimal-code` always apply

An agent loads a skill only when it judges the skill relevant, and it loads it at the *start*
of a task — not at the end, where the pre-flight checklist matters most. Coding principles are
meant to hold on every change. The plugins handle this with their hook. Without a plugin, back
the skill with a pointer in your project's `CLAUDE.md` (or `AGENTS.md`):

```markdown
Follow the minimal-code skill when writing or changing code.

Load it before making code changes. Before reporting a change as done, read
references/done-checklist.md from the skill directory and work through it.
```

The skill holds the detail; the pointer is what gets it consulted at the two moments that
decide whether the change stays small. The completion checklist lives in its own file so the
second moment costs a short read, not a reload of the whole skill.

## Making `natural-clear-writing` govern chat replies

The skill loads only for writing and editing tasks, not for ordinary replies. The plugins add
the short form to every session. Without a plugin, put it in `CLAUDE.md` (or `AGENTS.md`):

```markdown
Lead replies with the answer. No staged openers, empty contrasts, forced triads,
dramatic closers, or Markdown decoration. Load natural-clear-writing when
writing or editing prose, docs, commit messages, or UI strings.
```

## Independent review after push

`independent-review` records an authorized push's scope before it runs, then reviews
successful updates in the background. It never waits for review before pushing and
does not authorize a push itself. Results appear in the current conversation, with
the reviewed remote/ref and SHA. Findings do not trigger automatic fixes or pushes.

The reviewer gets the original requirements and repository rules, without the
author's conversation, reasoning, or self-review. It must substantiate defects with
supported inputs and execution paths; finding no defects is a valid result.
`completed` describes a finished review, including one with findings. `incomplete`
describes failed execution, missing scope, or a material coverage gap.

The included Python 3.11+ helper creates a standalone Git checkout at the pushed
SHA, retaining the base for the full diff. It leaves dirty author files alone and
does not launch a model or access the remote. It excludes inherited Git settings
and content filters, disables hooks and external attributes, accepts repository
subdirectories, and supports `--root` to review a new standalone history against
an empty tree. Git 2.46+ must be installed to disable lazy object fetching.
Existing system/global `safe.directory` entries are preserved for source discovery;
other settings are excluded. If setup
cleanup fails, the error includes the remaining temporary directory's path.
Dependencies, submodule contents, and LFS objects are not installed or fetched
for the reviewer. All reachable Git objects must already be local; partial clones
with missing objects report `incomplete` without fetching or creating a snapshot.
Use `--snapshot-parent <directory>` to choose an existing permitted directory
outside the author's working tree. For a new branch, pin its unique merge-base
with the intended target branch, so independently added target changes do not
appear as deletions in the review. Existing and force updates retain the old ref
SHA as their baseline.

The Claude Code plugin includes a background reviewer agent and requires Claude
Code 2.1.271+ to exclude the author's instruction files with `omitClaudeMd`. A
skills-only Claude installation needs a reviewer that also excludes those files;
otherwise review is reported as `incomplete`. This release conditionally supports
Claude Code hosts with snapshot access under existing permissions. Codex clients
that automatically inject the author's `AGENTS.md` even with conversation
inheritance disabled are unsupported; the Codex host used during development has
that limitation. Generic installations require a host with both forms of context
exclusion. Skills alone cannot provide these runtime capabilities. Every
installation checks context exclusion, background completion, and permission to
use a snapshot parent before creating a snapshot; failure reports `incomplete`.
The skill checks the available tool schema;
it does not assume every client has the same spawning parameters. See the official
[Claude Code subagent documentation](https://code.claude.com/docs/en/sub-agents)
and [Codex subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents).

This version needs fresh-context background execution and completion delivery in
the current session, with existing permission to access the temporary snapshot.
Claude background tasks deny permission prompts, so a version check or directory
read access alone does not establish permission to run Git checks. The Claude
host tested during development also returned `incomplete` because Bash was not
already permitted. `omitClaudeMd` applies to a subagent, not a top-level `--agent`
session. See the [live host checks](docs/independent-review-host-check.md) for
the tested behavior and its limits.
If those are unavailable, it reports `incomplete` rather than
running a foreground review. It does not guarantee execution or notification after
the session closes. The SessionStart hook supplies a workflow instruction, not a
Git push interceptor; pushes made outside the agent session are not monitored.

For a skills-only installation, add this pointer to `CLAUDE.md` or `AGENTS.md`:

```markdown
Load independent-review before an authorized push to record its scope, then start
its fresh-context background review after success and report the result when it
arrives. Never wait for review before pushing; report incomplete if the required
capabilities or scope are unavailable.
```

## Evals

`evals/` holds cases for `natural-clear-writing`: an English doc, a Korean doc, a bilingual
note, UI strings with placeholders, and a commit message. Each case has an LLM grader that
checks formulaic phrasing is gone and every fact, placeholder, and register survives.

The independent-review cases exercise supported defects, intentional behavior
without defects, and unavailable background capabilities. These are offline
behavioral exercises; they do not establish live delegation or notification
support. `tools/test_independent_review.py` checks the snapshot helper against real
temporary Git repositories, including multiple commits and force updates.

The installer checks build a temporary copy of `src/` using
`python3 tools/build.py stage <directory>`. They leave the caller's generated
files untouched, including local edits and stale distributions.

```bash
tools/eval.sh --judge-model sonnet
```

The default judge (haiku) misreads the Korean criteria, so pass a stronger judge. The run also
scores a no-plugin baseline and reports the delta, which is the number to watch when editing
the skill. Results land in `evals/results/`, which is ignored by git.

`claude plugin eval` reads cases only from inside the plugin directory, and the cases are not
shipped with the plugin. The script rebuilds the outputs, copies `plugins/claude/tao/` and
`evals/` into a temporary directory, and runs the eval there. Extra arguments are passed through. Do
not run `claude plugin eval .` at the repository root: it finds the cases but loads no plugin.

## Repository layout

```text
src/skills/<skill>/SKILL.md.tmpl   skill sources: edit here
src/plugin/                        files that go into both plugins
src/claude/                        Claude Code manifests and Claude-only files
src/codex/                         Codex manifests and Codex-only files
tools/build.py                     generates everything below
skills/                            generated, read by the skills CLI
plugins/claude/tao/                generated, the Claude Code plugin
plugins/codex/tao/                 generated, the Codex plugin
.claude-plugin/marketplace.json    generated, the Claude Code marketplace
.agents/plugins/marketplace.json   generated, the Codex marketplace
evals/                             eval cases, not shipped
```

`skills/`, `plugins/`, `.claude-plugin/`, and `.agents/plugins/` are build output. They are
committed because every installer reads the default branch. The build deletes any file in
them that it did not produce, so hand edits and extra files there do not survive.

## Contributing

[AGENTS.md](AGENTS.md) holds the rules for writing a skill that works in all three
distributions. Claude Code and Codex read it when they work in this repository.

1. Edit files under `src/`. A `.tmpl` file is rendered once per distribution, and everything
   else is copied as it is. Every distribution gets the same text unless a template uses a
   target block:

   ```markdown
   <!-- target:claude -->
   This line appears only in the Claude Code plugin.
   <!-- /target -->
   ```

   The targets are `claude`, `codex`, and `generic`. A marker must be a whole line, and
   blocks do not nest.

   Anything that only one agent supports goes in that agent's directory: a hook definition, a
   subagent, a file that names the agent's own variables. `src/claude/` is copied into the
   Claude Code plugin and `src/codex/` into the Codex plugin. Lint rejects the other agent's
   variables and paths there, such as `${PLUGIN_ROOT}` in `src/claude/` or
   `${CLAUDE_PLUGIN_ROOT}` in `src/codex/`. Files that both plugins need go in `src/plugin/`.
2. If the change affects a plugin, raise `version` in both `src/claude/plugin.json` and
   `src/codex/plugin.json`. The two must stay equal. Installed plugins update only when the
   version changes, and the version check fails the build PR without it.
3. Run the checks:

   ```bash
   python3 -m unittest discover -s tools
   python3 tools/build.py lint
   tools/check_codex_plugin.sh   # needs the codex CLI, no login
   ```

4. Open a pull request with the `src/` changes. You do not need to commit generated files. If
   you do, run `python3 tools/build.py build` first so that `python3 tools/build.py check`
   passes.

After the pull request merges, a workflow opens a "Release: regenerate distributions" pull
request with the rebuilt outputs. Merging that one is the release.
[docs/release-setup.md](docs/release-setup.md) describes the one-time setup it needs.
