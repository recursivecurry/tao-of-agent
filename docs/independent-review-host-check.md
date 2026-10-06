# Independent review host checks

On 2026-10-05 (Asia/Seoul), Claude Code 2.1.289 loaded the generated 0.3.0 plugin
and ran `tao:independent-reviewer` as a non-fork background subagent in two live
smoke tests. Both returned `incomplete` under existing permissions. These are
runtime checks, not a claim that a complete review works on the default host.

## Fixture and execution

A disposable local repository pushed a base commit and then a change from `base`
to `pushed` in `code.txt` to a local bare remote. The helper created a standalone
snapshot at the pushed head outside that repository. Its pinned `CLAUDE.md`
contained one rule token; the author's dirty `CLAUDE.md` contained a different
token. Neither token was included in the delegated task message.

The parent ran with `--plugin-dir`, `--permission-mode dontAsk`,
`--permission-prompts none`, `--no-session-persistence`, and verbose stream JSON.
No directories, tools, or permission rules were added to its allow list. It
invoked the plugin subagent with `run_in_background: true`, emitted
`MAIN_CONTINUES`, and later received the task's completion notification. Runtime
statistics recorded one background task, zero foreground tasks, and no additional
delegation in each run.

The delegated task supplied the reviewer reference path, snapshot path, remote
and ref, pinned base/head, existing-branch provenance, and the original change
requirement. It asked the reviewer to report initial rule-token presence before
reading files, read the snapshot's rules and code, and run the pinned diff and
HEAD check. These probes test instruction-file exclusion; they do not prove the
absence of every possible automatically supplied host field.

## Observations

| Session working directory | File access | Git commands | Result |
| --- | --- | --- | --- |
| Author repository; snapshot and reviewer reference outside it | Read and Grep denied | Bash denied | `incomplete` |
| Existing parent workspace containing separate author repository, snapshot, and a copy of the reviewer reference | Reference and snapshot reads succeeded | Both separate Bash calls denied | `incomplete` |

In the second run, the parent reported its author rule token. The reviewer
reported no author rule token in its initial context, then returned the distinct
pinned rule token and `pushed` file content after reading the snapshot. The first
reviewer reported the dirty filename in automatic Git status, but no instruction
contents. This agrees with the documented scope of
[`omitClaudeMd`](https://code.claude.com/docs/en/sub-agents): custom subagents can
omit author instruction files; this does not remove every host context field and
does not apply to top-level `--agent` sessions.

The stream recorded permission denials for both requested Git commands in the
second run. The reviewer did not claim HEAD or diff verification, did not change
permissions, and did not report a clean review. Allowing a directory to be read
was therefore insufficient for a full review.

The Codex host used during development automatically supplied the author's
`AGENTS.md` despite `fork_turns: "none"`. That configuration is unsupported.

## Release boundary

Claude support is conditional on existing permission to read the reviewer
reference and snapshot and run the needed Git commands, as well as instruction
exclusion and background completion delivery. Codex and generic hosts need
equivalent verified capabilities. Check these before preparing a snapshot;
failure must return `incomplete`. A successful full review under an already
permitted configuration remains unverified. Do not grant permissions or start an
unmanaged process to make a smoke test pass.

To repeat the check, create a disposable local push fixture with distinct author
and pinned rule tokens, delegate only its neutral requirements and fixed scope,
and capture actual task statistics, tool denials, and completion output. Keep
permission failure as a separate expected case. `tools/eval.sh` is a paid model
evaluation workflow and was not run for these checks.
