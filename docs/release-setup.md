# Release setup

Generated files are committed, and a workflow keeps them current. When changes to `src/` or
`tools/` land on `main`, `.github/workflows/build-pr.yml` rebuilds the outputs and opens one
pull request from the `bot/build` branch. Merging that pull request is the release.

The workflow needs a GitHub App. A pull request opened with the default `GITHUB_TOKEN` does
not trigger `check.yml`, so its required checks would never report. Until the setup below is
done, the workflow fails with a message that points to this file.

## One-time setup

1. Create a GitHub App owned by the repository owner, with no webhook and these repository
   permissions:

   | Permission | Access |
   | --- | --- |
   | Contents | Read and write |
   | Pull requests | Read and write |

2. Install the App on this repository only.
3. Generate a private key for the App.
4. In the repository's Actions settings, add:

   | Kind | Name | Value |
   | --- | --- | --- |
   | Variable | `BUILD_APP_ID` | The App ID |
   | Secret | `BUILD_APP_KEY` | The contents of the private key file |

5. In the repository's Actions settings, allow GitHub Actions to create pull requests.
6. Protect `main` and require these status checks from `check.yml`:

   - `test`
   - `lint`
   - `generated`
   - `version`

   Leave `skills-cli` optional. It reads the text output of the skills CLI, which may change
   between CLI versions.

## First release

1. Merge the pull request that introduces `src/` and `plugins/tao/`. Its generated files are
   already current, so the build workflow opens no pull request.
2. On a machine that has `tao@tao-of-agent` installed from before the move, run:

   ```bash
   claude plugin marketplace update tao-of-agent
   claude plugin update tao@tao-of-agent
   ```

   The plugin should update from 0.1.0 to 0.2.0 and, after a restart, still provide
   `tao:minimal-code`, `tao:git-hygiene`, and `tao:natural-clear-writing`. This path was
   tested against a local marketplace only, so check it once against GitHub.

## Each release after that

1. Merge a pull request that changes `src/` and raises `version` in `src/claude/plugin.json`.
2. Review the "Release: regenerate distributions" pull request. Its body lists the version
   change and which skills changed in each distribution.
3. Merge it.

If the build pull request fails the `version` check, the source change did not raise the
version. Raise it in `src/claude/plugin.json` in a new pull request. The build pull request
updates itself once that merges.
