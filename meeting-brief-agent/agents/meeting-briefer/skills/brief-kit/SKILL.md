---
name: brief-kit
description: >-
  Run book and tools for the meeting-brief agent: read the work list from the n8n door, write a short brief and 5
  questions before each booked networking 1-2-1, write the thank-you after each held meeting, and hand each one in with
  deliver.py. Use it for every run, from the first command to the final report.
---

# Brief kit (cloud run book)

**Who it is for.** YOUR_OWNER_NAME owns YOUR_BUSINESS_NAME, YOUR_BUSINESS_DESCRIPTION. The owner meets fellow members of
their networking group one to one ("1-2-1s"). In the owner's own words the purpose is getting to know them, their role,
how they use the group and what referrals help them. Calendar invites and booking pages sometimes show the owner's full
legal name (YOUR_OWNER_FULL_NAME): a booking under that name is the owner's, so never flag it as a doubt. A 1-2-1 is
never a sales meeting, so nothing you write pitches the owner's business.

Nobody watches a run and nobody can answer a question during it. Decide, and give the reason in the final report.
When unsure, take the safer option: a narrower claim, a labelled guess, a shorter brief.

**Cost.** Every tool call re-reads the run so far, so fewer, fuller calls are cheaper: put related commands in one bash
call, open only pages that can answer something, and keep to about 6 searches and 8 page fetches per lead. Never end
your turn to wait for anything.

## The run, in order
Commands say `python3`; if the container only has `python`, use that.

**0. Work list.** `python3 <this skill's folder>/scripts/get_work.py --sheet <sheet>` with the sheet from your kickoff
(`live` or `demo`). It saves `/workspace/work.json` and prints the jobs. If it fails, hand in the run report with the
error (`python3 <skill>/scripts/report.py --sheet <sheet> --note "Work list failed: <the error>"`) and end the run. If it
prints NOTHING TO DO, hand in the run report (`report.py --sheet <sheet> --note "Nothing to do."`) and end with a
one-line message.

**1. Read in full** before writing anything: `references/brief-standard.md`, `references/thank-you-standard.md` and
`references/safety.md` in this skill's folder.

**2. Thank-yous first** (no research needed). For each job in `thank_yous`: write it from `meeting_notes` (the main
source), `conversation` and `brief`, to the thank-you standard. Save it as `/workspace/out/<lead_id>.json` and run
`python3 <skill>/scripts/deliver.py --sheet <sheet> --file /workspace/out/<lead_id>.json`.

**3. Briefs**, earliest meeting first, at most 4 in this run (the rest wait for the next run). For each job in `briefs`:
- **a. Identity first.** Decide who this person is before you research them. The anchor is the business email domain
  (`email_domain`, unless `freemail` is true) and its website, plus the business name. Confirm the person belongs to that
  business (team page, the group's member page, their own emails in `conversation`). Many businesses and people share
  names: never mix in a namesake. If you cannot tie the person to the business, say so in the brief and keep to what the
  sheet and their own emails say.
- **b. Research the business and the role only.** The business's own site (home, about, services, team), their
  networking group's member page, and public business listings when they help (ABN Lookup for a business name: read it
  with care, a name can belong to someone else). No personal social media, nothing about private life.
  **How to open pages:** `web_fetch` only opens addresses that appeared in a `web_search` result or in a page it already
  fetched, so it refuses the website from the work list. Read that one (and its same-site pages, which it lists) with
  `python3 <skill>/scripts/read_page.py <url>`: plain text, capped, blocked sites refused. When the work list has no
  website, start from the email domain (`read_page.py <email_domain>`) or a `web_search` for the business name and town,
  then `web_fetch` the results. Never use curl or wget for pages.
- **c. Write** the brief and the 5 questions to the brief standard. The owner's `prep_notes` (what they want from this
  meeting) come first: every point goes in the brief's "Your notes:" line and each thing they want to find out becomes
  question 3 or 4. Question 5 is always the introduction ask. Every fact comes from a page you opened or from their own
  words in `conversation`; label any inference "(a guess)"; list what you could not confirm in `not_confirmed`.
- **d. Check and deliver.** Go through the standard's checklist, save `/workspace/out/<lead_id>.json`, run `deliver.py`
  (add `--check` to test without sending). If the door refuses it, fix exactly what it lists and send it again, at most
  twice; if it still fails, skip that lead and say why in the report.

**4. Run report, every run.** Write the final report to `/workspace/out/report.txt`: for each job, the lead id, handed
in or skipped (and why), the sources used and the doubts; then one line on anything the operator should look at (for
example an identity you could not confirm). Hand it in with `python3 <skill>/scripts/report.py --sheet <sheet>
--note-file /workspace/out/report.txt` (one bash call can write the file and run it). This is the run's receipt: the run
monitor logs it and emails the operator, and a run n8n started that sends none sets off an alarm. Then end with the
same report as your last message. If report.py prints COULD NOT REPORT, say so at the top of that message.

## The files deliver.py takes
Brief:
```json
{"kind": "brief", "lead_id": "LEAD-000", "brief": "...", "questions": ["...", "...", "...", "...", "..."],
 "sources": ["northgate.example.com (home, about)", "Port City group member page", "her emails of 3 and 6 Oct"],
 "not_confirmed": ["her title comes from her email signature only"]}
```
Thank-you:
```json
{"kind": "thank_you", "lead_id": "DEMO-002", "subject": "Thank you for the coffee, Sam", "body": "Hi Sam,\n\n...\n\nWarm regards,\nJordan"}
```
The door adds the "Not confirmed:" and "Sources:" lines under the brief itself, numbers the questions, writes only
empty cells of that one lead, and does all the emailing. On the demo sheet the same happens with made-up rows.
