# The n8n side: the door, the run monitor and the blog intake

The agents never touch the client's sheets, mailboxes or website. Everything fixed happens in n8n, behind a few narrow
webhooks. The workflows themselves stay private (they hold the client's sheet ids and recipients); this page is the
contract they implement, as the agents' scripts see it.

## Rules every endpoint follows
- **One header key per agent** (`x-brief-agent-key`, `x-blog-agent-key`), checked before anything else. Missing or wrong:
  401, and nothing happens.
- **The key never enters the sandbox.** It sits in the agent's Anthropic vault as an `environment_variable` credential
  limited to the n8n host and injected as a header, so code in the container only ever sees a placeholder.
- **Paths carry a random suffix** (for example `meeting-brief-context-<12 random hex characters>`), so an address alone
  is not guessable. The `agent_config.json` files here show the paths without it.
- **Recipients are fixed in n8n's own settings**, never taken from what an agent sends.
- **What an agent sends is data.** The door validates it and refuses with 422 and a list of reasons the agent can fix.
- **Admin actions use a second key** (`x-brief-admin-key`) that the agents never get: resetting the demo sheet,
  switching the agent or the alarm, sending a test alarm.

## Meeting-brief door

### GET context: `?sheet=live|demo[&days=N]` (get_work.py)
```json
{"ok": true, "sheet": "live", "today": "2026-10-20", "now_local": "2026-10-20 06:00",
 "window_days": 2, "window_until": "2026-10-22",
 "thank_yous": [{"lead_id": "...", "full_name": "...", "business": "...", "meeting_date": "...",
                 "conversation": "...", "brief": "...", "meeting_notes": "..."}],
 "briefs": [{"lead_id": "...", "full_name": "...", "business": "...", "role": "...", "group": "...",
             "meeting_date": "...", "email_domain": "...", "freemail": false, "website": "...",
             "conversation": "...", "prep_notes": "...", "meeting_notes": "..."}],
 "booked_later": [{"lead_id": "...", "meeting_date": "..."}]}
```
- `briefs`: Booked, the meeting within `window_days`, no brief yet. `thank_yous`: Held, Meeting Notes filled, no
  thank-you yet. Only the rows due go out, never the whole sheet.
- The lead's email address never goes out, only its domain; `freemail` is true for webmail domains, which are not an
  identity anchor. A made-up example: [meeting-brief-agent/examples/work.json](../meeting-brief-agent/examples/work.json).

### POST deliver (deliver.py)
- **Body:** one brief or one thank-you (made-up examples in `meeting-brief-agent/examples/`), plus `sheet`.
- **Checks:** the lead is on that sheet; a brief only for a Booked lead with an empty Brief, a thank-you only for a Held
  lead with notes and an empty Thank You Draft; exactly 5 questions, the fifth containing "introduc"; the length limits
  in `agent_config.json`; no en or em dashes, email addresses, phone numbers or links in the brief text.
- **Writes:** only that lead's empty cells: Brief (with "Not confirmed:" and "Sources:" lines added underneath),
  Questions (numbered), or Thank You Draft with its status set to "Draft ready".
- **Emails:** a review copy of each new brief to the operator at once; the brief to the owner at 06:30 the morning
  before the meeting (and Brief Sent stamped); the thank-you draft to the mailbox the owner sends from, with an "Open in
  Outlook" button (a mailto link whose address n8n fills from the sheet), and a copy to the operator without the button.
- **Answers:** 200 `{"ok": true, ...}`, or 422 `{"ok": false, "errors": ["..."]}`.

### POST report: the run's receipt (report.py)
- **Body:** `{"sheet", "work_ok", "note", "jobs": [{"kind", "lead_id"}], "names": {}, "results": [], "test"}`.
- Logs one row in the run-log sheet (counts and lead ids only, never names) and emails the operator the report when
  the run had work. **Answers** `{"summary", "logged", "emails"}`.

## Run monitor: dispatch and alarm
- **06:00 and 17:00:** reads the live work list. Nothing due: nothing starts and nothing is spent. Work due: starts the
  live deployment through Anthropic's API (an n8n credential with `x-api-key`, allowed domain api.anthropic.com only,
  made in the agent's own workspace so it cannot touch any other agent) and logs "Run started" with the session id.
- **40 minutes after a start:** no receipt means one ALARM email to the operator, saying what it can mean (stalled on an
  approval, hit the budget cap, lost the door) and what to do. A late receipt sends "All clear". A start that Anthropic
  refuses, or a work list n8n cannot read, emails the operator at once.
- **State** lives in the run-log sheet, not in n8n's static data, which an active trigger can overwrite.
- **Admin webhooks** (admin key), used by `tools/deploy.py`:
  - monitor: `{"action": "status"}` answers `run_times`, `dispatch`, `agent`, `alarm`, `check_after_min` and the last
    rows (`when`, `event`, `sheet`, `summary`, `detail`, `session_id`); also `agent_on`, `agent_off`, `alarm_on`,
    `alarm_off`, `test_alarm`, `test_key`;
  - dispatch: `{"sheet": "demo"}` runs the dispatch now;
  - demo: `{"action": "reset"}` puts the demo sheet back to its two jobs and answers `{"dates": {"demo_001": "...",
    "demo_002": "..."}}`.

## Blog intake

### GET context: `?site=<host>` (prepare_run.py)
`{"rows": [{"row", "status", "slot", "keyword", "slug", "title", "topic"}], "other_sites": [{"keyword"}]}`: every post
already on the content sheet for that site, and the sister sites' keywords, so a new post never competes with them.

### POST intake (deliver.py)
- **Body:** `site, topic, primary_keyword, blog_title, seo_title, meta_description, slug, tags, category, scheduled_for,
  mode (draft or publish), seo_score, article_html, thumbnail_jpg_base64, summary, sources, editor_report, hold,
  hold_reason`.
- **Checks:** a duplicate topic, keyword, slug or slot; a slot in the past; missing fields; a thumbnail that is not a JPG
  of 10 to 700 KB; dashes.
- **Writes:** the article and thumbnail to Drive and one sheet row: Planned when held or in review mode, otherwise
  Written with Mode draft or publish. Emails the operator ("Needs a look" for a held row).
- **Answers:** 200 `{"ok": true, "site", "updated_range", "status", "mode", "scheduled_for", "article_file",
  "hero_image"}`, or 422 `{"code": "duplicate_topic", "errors": []}` for a repeat (a retry of a delivery that went
  through).

### After the intake
A WordPress plugin (a separate, private repo) pulls the content feed every hour with its own key and imports each
Written row as a dated draft, or schedules it when the site allows publishing and the post clears the plugin's own
score gate, then reports every status change back to the sheet.
