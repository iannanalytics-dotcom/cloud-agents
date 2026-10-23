# Blog agent

A blog writer that runs on its own in Anthropic's cloud. On a schedule (or on demand) it plans, researches and writes
one blog post, has a second agent fact-check it, makes the thumbnail and hands the finished post to the publishing
pipeline. Nobody starts it and nobody's laptop needs to be on.

## At a glance
| | |
|---|---|
| The owner's task it takes over | Planning, researching, writing, fact-checking and illustrating a blog post |
| Runs on | Claude Managed Agents; a writer and an editor agent, both Claude Opus 5.5 |
| Started by | Its schedule (no laptop, no person), or by hand |
| Delivers | A finished post, thumbnail and sheet row through n8n; a WordPress plugin imports it |
| A person checks | Yes: review mode, every post lands at Planned until a person approves it |
| Access | One key to one n8n intake; no Google or WordPress access |
| Measured cost | US$7.56 (27 minutes) on test run 1; US$5.22 (about 20 minutes) on its scheduled run after the cost cuts; capped at US$9 a run |
| Status | Deployed; ran on its schedule on Mon 19 Oct 2026, now paused and run on demand to keep costs down |

## How one run works
```
Anthropic cloud (Claude Managed Agents)                      n8n                          WordPress
---------------------------------------                      ---                          ---------
schedule fires (Mon + Wed 6:00 am, when unpaused)
  -> blog-writer agent (Claude Opus 5.5)
       1. prepare_run.py  -- reads the sheet ------------->  intake: context webhook
       2. plans one post (topic bank, keyword clash check, next free slot)
       3. researches and writes it; scorer + link checker until READY
       4. blog-editor agent fact-checks every claim on its source page
       5. draws the thumbnail (the site's design, in code)
       6. deliver.py  ------- post + thumbnail ---------->  intake: saves to Drive,
                                                              adds the sheet row,
                                                              emails the operator
                                                            content feed  <----------  the WordPress plugin pulls
                                                                                       hourly and imports the post
                                                                                       (draft or scheduled)
```

## What keeps it safe
| Check | What it stops |
|---|---|
| The SEO pre-scorer and the link checker (private kit, [KIT.md](agents/blog-writer/skills/blog-kit/KIT.md)) | a weak or broken post: below 80, missing sections, dead links, banned phrases, dashes |
| The blog-editor agent (separate context) | wrong facts: every rule, menu path, quote and sum checked on its source page |
| The intake's own checks in n8n | duplicates (topic, keyword, slug, slot), past slots, missing fields, bad images, dashes |
| The plugin's publish gate on WordPress | an unscheduled publish: needs Mode publish, "Allow publish" on, score 80+ and no live post on the same keyword |
| Modes | `review` (a person approves each row), `draft` (a person presses Schedule), `publish` (scheduled days ahead, a person can still stop it) |
| Hold | anything the agent cannot make right goes to a person with the reason instead of going out |
| Budget | a hard US$9 cap per run, enforced by the platform |
| Secrets | the agent holds one key (to the n8n intake). It sits in Anthropic's vault, is added to requests to the n8n host only, in a header, and never enters the sandbox. No Google or WordPress access at all |

## Files
| Piece | Where |
|---|---|
| Agent definitions | `agents/blog-writer/agent.md` (the writer, coordinator), `agents/blog-editor/agent.md` (the editor) |
| Run book and its own tools (uploaded as a Skill) | `agents/blog-writer/skills/blog-kit/` (SKILL.md, scripts/prepare_run.py, scripts/deliver.py, agent_config.json) |
| The private writing kit | Not in this copy: [KIT.md](agents/blog-writer/skills/blog-kit/KIT.md) lists each piece and what the run book expects from it |
| Cloud container, vault | `agents/blog-writer/environment.yaml`, `agents/blog-writer/vault.yaml` |
| Schedule | `agents/blog-writer/deployment-review.yaml` |
| Deploy and run | `tools/deploy.py`, with its settings in `local/settings.json` (shape: `settings.example.json`) |
| The n8n side | [docs/n8n-door.md](../docs/n8n-door.md): the intake contract |

## Deploy
1. `python ../tools/repo_check.py install` from this repo (turns on the commit checks in your copy).
2. Add your writing kit (KIT.md), fill the `YOUR_...` placeholders and the intake addresses in
   `agents/blog-writer/skills/blog-kit/agent_config.json`.
3. `ant auth login` with `ANTHROPIC_CONFIG_DIR` set to the agents' login folder (SECURITY.md), then
   `python tools/deploy.py check`, read the plan, and `python tools/deploy.py apply --yes`.
4. `python tools/deploy.py credential`, then `python tools/deploy.py deployment --yes` (the schedule is created paused).
5. `python tools/deploy.py run --watch`, read the email and the row it delivers. When a test run is right:
   `python tools/deploy.py unpause --yes`.

## Cost
Model tokens at list price (Claude Opus 5.5), web searches at US$10 per 1,000 and the container at US$0.08 an hour.
**Measured:** test run 1 (15 Oct 2026) US$7.56 in 27 minutes, most of it cache writes and reads plus about US$1.21 lost
while the writer waited for the editor; after the cost cuts (a warm-cache wait, one-call checks) the scheduled run on
19 Oct 2026 cost US$5.22 in about 20 minutes, with the same score. The first estimate (US$2 to 4) was too low, which is
why every cap since has been set from a measured run.
