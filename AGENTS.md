# Working in this repository

One source tree under `src/` generates three outputs: a Claude Code plugin, a Codex plugin, and
generic skills installed with `npx skills`. The README describes the layout.

## Where to edit

- Edit only `src/`, `tools/`, `evals/`, and the docs. `skills/`, `plugins/`, `.claude-plugin/`,
  and `.agents/plugins/` are build output. Change them only by running
  `python3 tools/build.py build`.
- A skill lives in `src/skills/<name>/`. Files that both plugins need go in `src/plugin/`.
  Files for one agent go in `src/claude/` or `src/codex/`.
- `README.ko.md` is the Korean translation of `README.md`. Change both together.

## Running the skills CLI here

- Do not run `npx skills remove` or `npx skills add` in this repository without `-g`. The CLI
  treats the top-level `skills/` as skills installed into this project, so `remove` deletes
  the generated skills there, and `add` installs into the working tree.
- To manage your own installed skills, pass `-g` or run the command outside the repository.
- `npx skills add . --list` only reads, and `tools/check_skills_cli.sh` uses it.
- If `skills/` was deleted this way, run `git restore skills`.

## Writing a skill

A skill's text reaches all three outputs, so write it for any agent.

- Do not assume an agent's tools, commands, or files. Put anything agent-specific inside a
  target block (`claude`, `codex`, or `generic`).
- Refer to another skill in this repository by its plain name, such as "the minimal-code
  skill". It is `tao:minimal-code` only inside a plugin.
- The generic output has no hook. A skill must do its job from its own text.
- Write the `description` for triggering: what the skill does, when to use it, and when not
  to. Agents read only the description until they load the skill.
- Keep `SKILL.md` short. Move detail that is needed only at one moment into `references/`
  and link to it with a path relative to the skill.
- A non-template file in a skill is copied to all three outputs. The build cannot send a
  whole file to one target.
- Do not add a skill to one plugin only. The skills CLI follows the Claude Code marketplace
  into the plugin, so a plugin-only skill would also install for generic users. Use a hook
  or a target block for agent-only behavior.

## When a skill is added or renamed

- Update the skills table and the install commands in the README.
- Update `src/plugin/hooks/session-context.md` if the hook names the skill. Add to that file
  only what must hold in every session, in a sentence or two. It is loaded into every session
  of every plugin user.
- If the skill needs that always-on text, also give generic users the same text in the README
  to paste into their own instruction file.

## Before finishing

- If a plugin's files change, raise `version` in both `src/claude/plugin.json` and
  `src/codex/plugin.json` to the same value.
- Run the checks:

  ```bash
  python3 -m unittest discover -s tools
  python3 tools/build.py lint
  tools/check_codex_plugin.sh   # needs the codex CLI, no login
  tools/check_skills_cli.sh     # needs npx
  ```

- You do not need to commit generated files. A workflow regenerates them after the pull
  request merges. If you do commit them, `python3 tools/build.py check` must pass.
- `tools/eval.sh` starts a paid run. Do not run it unless asked.
