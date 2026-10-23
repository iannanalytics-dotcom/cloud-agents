# Security and sensitive data

How the two agents are kept to the least access they need, where every key lives, what personal data they touch, and
what to do when something goes wrong.

## What each agent can reach
| System | Meeting-brief agent | Blog agent | How that is enforced |
|---|---|---|---|
| Anthropic | Its own workspace | The operator's workspace | A hard cap per run (US$2 and US$9), enforced by the platform; the meeting agent's workspace also has a US$5 monthly limit |
| n8n | One key, to the door | One key, to the intake | Kept in Anthropic's vault. The sandbox only ever sees a placeholder; Anthropic swaps in the real key on requests to the n8n host only, in a header only, so code in the sandbox cannot read or leak it |
| Sheets, Drive, Gmail, Outlook, WordPress | None | None | n8n does every read, write and email with its own credentials, after its own checks; a WordPress plugin pulls the posts |
| The open web | Read, for research | Read, for research and fact-checking | Needed for sites that differ every run. Personal social media is blocked for the meeting agent. With open networking a prompt injection could in theory send working data out, so the agents get as little as possible: only the rows due, an email domain instead of an address, no raw keys |
| People | None | None | n8n sends the emails; the owner sends every thank-you; posts wait for a person in review mode |

## Keys: where each one lives
Values never go in a repo, in chat or on screen. A key's value only exists in the places below.

| Key | What it opens | Where it lives | How to change it (rotate) |
|---|---|---|---|
| `BRIEF_DOOR_KEY` (header `x-brief-agent-key`) | The meeting door's work list, hand-in and receipt | The Anthropic vault `meeting-brief-agent`; the n8n door and run monitor; the operator's settings file, outside every repo | New value in n8n and the settings file, archive the vault credential, `python tools/deploy.py credential`, then `dispatch-test` |
| Admin key (header `x-brief-admin-key`) | The demo tools and the run monitor's admin actions | n8n and the settings file. Never given to the agent | New value in both |
| n8n's Anthropic API key | Starting the meeting agent when work is due | Only in an n8n credential (header `x-api-key`, allowed domain api.anthropic.com). Made in the agent's own workspace, so it cannot see or start any other agent | A new key in the Console, pasted into n8n, `python tools/deploy.py test-key`, then delete the old key |
| `BLOG_INTAKE_KEY` (header `x-blog-agent-key`) | The blog intake's context and hand-in | The Anthropic vault `blog-agent`; the n8n intake; the settings file | As for the door key, then a test delivery |
| The `ant` login | Deploying and watching runs | The agents' own login folder (below). It expires by itself after about 8 hours | `ant auth logout` in a window with `ANTHROPIC_CONFIG_DIR` set |

The most powerful keys on the operator's machine (the n8n API key the workflow builders use, the Google service-account
key) are not used by the agents at all. The folder that holds them is never screen-shared, and they are changed if the
machine is ever lost or shared.

## The ant login folder
The `ant` login lives in `%APPDATA%\Anthropic-agents`, never in the shared `%APPDATA%\Anthropic`, which other Anthropic
tools on the same machine also read (Claude Code among them). Keeping the agents' Console login where only these tools
look means nothing else can sign in with it or spend the credit the agents run on ([decision 9](docs/DECISIONS.md)).
- Each `tools/deploy.py` sets `ANTHROPIC_CONFIG_DIR` for its own `ant` calls only. Never make it a system-wide setting:
  every tool would then read the agents' folder too.
- `deploy.py` prints a WARNING when a login is back in the shared folder.
- Running `ant` by hand: `set "ANTHROPIC_CONFIG_DIR=%APPDATA%\Anthropic-agents"` in that window first.

## Personal data
- **Meeting-brief agent sees**, for each lead it works on: the name, business, role, group, website, the email domain
  (never the address), the lead's own replies, calendar lines (time and place) and the owner's notes. **It writes** a
  brief, 5 questions or a thank-you draft, only into that lead's empty cells, through the door.
- **Research rules:** the business and the person's role only, never private life; every fact sourced; guesses labelled
  "(a guess)"; doubts listed ([safety.md](meeting-brief-agent/agents/meeting-briefer/skills/brief-kit/references/safety.md)).
- **Where data is kept:** the client's sheet (shared with named people only); a run-log sheet (lead ids and counts,
  never names); Anthropic's session logs (full detail, so the Console is never shown or shared with outsiders, and demos
  run on the demo sheet).
- **Blog agent:** no personal data. It works from public sources and the site's topic list.
- **In this repo: none.** Examples are made up (LEAD-000, DEMO-001, someone@example.com, Priya Nair, Sam Carter). Every
  n8n address is a placeholder, and no resource id, lock file or settings file is committed.

## A fresh history
This repo is a clean copy of the private repos that deploy the live agents. Those keep their full history; a few of
their early commits held example details borrowed from real leads, which were documented there rather than rewritten,
and those repos are never shared. So this copy was made from the current files, with the client's details replaced by
placeholders, and a new history.

## Safety nets on every commit
GitHub's free plan does not protect branches or scan private repos for secrets, so the checks run locally: the hooks in
`.githooks/` run `tools/repo_check.py` before every commit (the staged files and the message) and before every push
(every commit going up, including any made with `--no-verify`). Turn them on once per copy with
`python tools/repo_check.py install`. The lists of real names, brands, hosts and ids it blocks live in a settings folder
outside every repo; point the check at it with `REPO_CHECK_SETTINGS` or one line in `tools/repo_check.local` (git
ignores that file).

## If a key leaks
1. **Rotate it first** (table above). Deleting the commit does not un-leak it.
2. Look at the n8n executions for calls you did not make, and at the Console's usage for runs you did not start.
3. Then clean up (the repo, the message, the screenshot) and write down what happened the same day.
