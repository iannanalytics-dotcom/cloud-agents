# How changes are made

The live agents are deployed from private copies of these files, so a change to an agent's files is a change to an agent
that works on real people's meetings and a real website. The routine below keeps the files and the deployed agents the
same, and keeps keys and real details out. This public copy follows the same commit rules.

## Once per copy of the repo
`python tools/repo_check.py install` turns on the checks (git hooks in `.githooks/`). Point them at your settings folder
(`REPO_CHECK_SETTINGS`, or its path as one line in `tools/repo_check.local`) so the private lists are checked too.
Without the hooks nothing stops a key or a real person's details from being committed.

## Every change to an agent (run from that agent's folder)
1. **Edit** the files. Examples always use made-up data: LEAD-000, DEMO-001, someone@example.com.
2. **Check the plan:** `python tools/deploy.py check` shows what would change on Anthropic's side, and changes nothing.
3. **Apply** (only when an agent, skill, environment or vault file changed): `python tools/deploy.py apply --yes`, then
   `python tools/deploy.py deployment --yes`, because a deployment pins an agent version.
4. **Prove it:** a demo run (`run --demo --watch` for the meeting agent, `run --watch` for the blog agent), then read
   what it delivered.
5. **Commit** the files (in a private copy, together with `claude-lock.json`, so every commit on `main` is a state that
   actually ran). Look at `git status` and `git diff --staged` first, and stage files by name. The hooks check the files
   and the message.
6. **Tag** a deployed state: `git tag -a live-YYYY-MM-DD -m "what changed"`. Rolling back = check out that tag's files,
   then `check`, `apply --yes`, `deployment --yes`.
7. **Push:** `git push --follow-tags`. The pre-push hook scans every commit going up.

Documentation-only changes skip steps 2 to 4 and 6.

## Commit messages
[Conventional Commits](https://www.conventionalcommits.org/): `type(scope): what changed`, in the imperative ("add", not
"added"), 72 characters at most, no full stop. Then a blank line and, when it helps, why.

| Type | For | Example |
|---|---|---|
| `feat` | something an agent can now do | `feat(brief-kit): run receipt and alarm for every run` |
| `fix` | a bug | `fix(brief-kit): read the work list's website with read_page.py` |
| `docs` | documentation only | `docs(readme): measured costs from the first runs` |
| `chore` | upkeep, deploy records | `chore(deploy): lower the per-run cap to US$9` |
| `refactor`, `test`, `perf`, `build`, `ci`, `revert` | as named | |

Scopes used here: `meeting-agent`, `brief-kit`, `blog-agent`, `blog-kit`, `deploy`, `docs`, `readme`, `security`, `repo`.

## Never
- Never commit a key, a settings file, a lock file with real ids or a real person's details. Keys live in Anthropic's
  vault, in n8n and in a settings folder outside every repo ([SECURITY.md](SECURITY.md)).
- Never skip the checks (`--no-verify`). If a check is wrong, fix the check, or mark that one line with
  `repo-check: allow` and say why in the commit message.
- Never force-push `main` or rewrite history without a backup (`git bundle create backup.bundle --all`) and a written
  reason.
- Never commit test output (`work.json`, `out/`, `tests/ws*/`); `.gitignore` keeps it out.
