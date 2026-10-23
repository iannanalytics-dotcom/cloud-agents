# Meeting-brief agent

An agent that prepares a business owner for their networking 1-2-1 meetings and follows them up. It works only when
there is work: n8n checks twice a day and wakes it in Anthropic's cloud when a booked meeting is 2 days away and has no
brief yet, or a meeting was held and has notes but no thank-you. It researches the person and writes a short brief and
5 questions, or writes the thank-you the owner sends.

## At a glance
| | |
|---|---|
| The owner's task it takes over | Researching each person before a 1-2-1, preparing questions, writing the thank-you after |
| Runs on | Claude Managed Agents, in its own Anthropic workspace; model Claude Sonnet 5.5 |
| Started by | n8n, twice a day, only when a brief or a thank-you is due (no laptop, no person) |
| Delivers | Brief + 5 questions on the sheet, emailed the morning before (with the owner's own prep notes worked in; the last question always asks for introductions); after the meeting, a thank-you draft in the owner's inbox with an "Open in Outlook" button, which the owner checks and sends |
| A person checks | Yes: the owner sends every thank-you, and the operator gets a copy of every new brief (a day before the owner's email) and every thank-you draft |
| Access | One key to one n8n door; no Google, Gmail or Outlook access; it never emails anyone |
| Measured cost | About 12 to 13 US cents a brief (US$0.39 for 3 briefs in one live run); nothing on days with nothing due; capped at US$2 a run and US$5 a month |
| Status | Live since 18 Oct 2026 |

## How one run works
```
n8n: run monitor                         Anthropic cloud: its own workspace          n8n: the door                       Sheet + email
----------------                         ----------------------------------          -------------                       -------------
06:00 + 17:00: is anything due?
  (the door's work list: briefs for
   meetings within 2 days, thank-yous
   for Held + notes)
  nothing due -> nothing runs, nothing
  is spent
  work due -> starts the agent           -> meeting-briefer (Claude Sonnet 5.5)
     (Anthropic API, key locked to          0. get_work.py --- work list ---------->  context: only the rows due, an
     api.anthropic.com), logs                                                         email domain instead of the address
     "Run started"                          2. thank-yous from the meeting notes
                                            3. briefs: identity check, research the
                                               business and the group page, brief +
                                               5 questions, self-check
                                            deliver.py ------ one result each ----->  deliver: checks it, writes only that   Brief, Questions,
                                                                                      lead's empty cells, emails it          Thank You Draft
                                                                                      06:30: brief to the owner the  ------> email, Brief Sent
                                                                                      morning before; thank-you draft
                                                                                      with an "Open in Outlook" button ---> the owner sends it
     <- report.py: the run's receipt <---   4. report.py
  logs it, emails the operator the report
06:40 + 17:40: a started run with no receipt -> ALARM email to the operator
```

## What keeps it safe
| Check | What it stops |
|---|---|
| Its own workspace | A US$5 monthly spend limit. The key n8n uses to start the agent only works in that workspace, and n8n only sends it to api.anthropic.com |
| One n8n door, one key | No Google, Gmail or Outlook access. The key sits in Anthropic's vault, is added only to requests to the n8n host, in a header, and never enters the sandbox |
| Row-scoped work list | The agent sees only the leads it works on, and an email domain instead of the address |
| The door's own checks | Writes go only into empty cells of a Booked (brief) or Held (thank-you) lead; exactly 5 questions, the last one an introduction ask; no dashes, email addresses, phone numbers or links in a brief; length limits |
| Nobody gets an email from the agent | n8n sends the brief and the thank-you draft; the owner sends every thank-you |
| Review copies | The operator gets every new brief as soon as it is written, 2 days before the meeting, so it can be fixed on the sheet before the owner's 6:30 am email the day before |
| Run book rules | Identity check before research, business and role only, every fact sourced, guesses labelled "(a guess)", doubts listed |
| Budget | A hard US$2 cap per run, enforced by the platform, inside the workspace's US$5 a month |
| Run receipt + alarm | Every run ends by handing in its report. A started run with no report 40 minutes later (stalled on an approval, hit the cap, lost the door) emails the operator an ALARM. The state lives in a run-log sheet, not inside n8n |
| Demo sheet | Demos run on a separate sheet with made-up rows, never on a real person |

## Files
| Piece | Where |
|---|---|
| Agent definition | `agents/meeting-briefer/agent.md` |
| Run book + scripts (uploaded as a Skill) | `agents/meeting-briefer/skills/brief-kit/` (SKILL.md, references/, scripts/get_work.py, deliver.py, report.py, read_page.py) |
| Cloud container, vault | `agents/meeting-briefer/environment.yaml`, `agents/meeting-briefer/vault.yaml` |
| Deployments | `agents/meeting-briefer/deployment-live.yaml` and `deployment-demo.yaml`, both paused for good: n8n (live) or the operator (demo, by hand) starts the runs |
| Deploy and run | `tools/deploy.py`, with its settings in `local/settings.json` (shape: `settings.example.json`) |
| Made-up examples | `examples/work.json` (a work list), `examples/brief.json`, `examples/thank_you.json` (what deliver.py hands in) |
| The n8n side | [docs/n8n-door.md](../docs/n8n-door.md): the contract the door and the run monitor implement |

## Deploy
1. `python ../tools/repo_check.py install` from this repo (turns on the commit checks in your copy).
2. Fill the `YOUR_...` placeholders (`python tools/deploy.py check` lists any left) and the door addresses in
   `agents/meeting-briefer/skills/brief-kit/agent_config.json`.
3. `ant auth login` with `ANTHROPIC_CONFIG_DIR` set to the agents' login folder (SECURITY.md), then
   `python tools/deploy.py check`, read the plan, and `python tools/deploy.py apply --yes`.
4. `python tools/deploy.py credential` (puts the door key in the vault), then `python tools/deploy.py deployment --yes`
   (both deployments, created paused; they stay paused).
5. Put the live deployment's id into the run monitor's settings in n8n, then `test-key` and `dispatch-test`.

Run by hand: `python tools/deploy.py run --demo --watch` resets the demo sheet, starts one run on it and opens
Anthropic's live session viewer (about 2 minutes, around 10 US cents). `run --watch` does the same on the live sheet,
whose viewer shows real people's details, so never on a shared screen.

## Cost
Claude Sonnet 5.5 at list price, web searches at US$10 per 1,000 and the container at US$0.08 an hour. **Measured:**
about 12 to 13 US cents a brief (7 briefs for US$0.83 in the first live runs on 18 Oct 2026; US$0.39 for 3 in one run);
a demo run (1 brief + 1 thank-you) US$0.09 to 0.12 in about a minute. The estimate before the first run was US$0.40 to
0.80 a brief, which is why every cap is set from a measured run. Days with nothing due cost nothing, because nothing runs.
