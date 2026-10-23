# Design decisions

Why the two agents are built the way they are: each decision, what it was weighed against, and what it costs.
All dates are 2026. The private repos keep the day-by-day record; this is the merged, cleaned-up version.

## Both agents

### 1. An agent for the judgment, n8n for the plumbing (15 and 18 Oct)
- **Decision:** a Claude Managed Agent does the work that needs judgment; n8n does everything fixed around it (sheets,
  Drive, email, schedules, the feed the WordPress plugin pulls).
- **Why:** a good brief needs judgment (is this the right person when most rows on the member sheet have no job title,
  which gaps are worth looking up, what is a fact and what is a guess), and a good post needs a loop (research, write,
  score, fix, check every claim, repeat until nothing is broken).
- **Weighed against:** an n8n workflow with one AI step (cents and fast, but no tools and no loop, so only as good as
  the row it is given) and doing the work in supervised Claude Code sessions (no cost per item, but someone has to sit
  down and run them).
- **Trade-off:** a cost per run and a platform to learn. Kept small by decisions 5, 12 and 13.

### 2. One narrow door instead of Google, Gmail, Outlook or WordPress keys (15 and 18 Oct)
- **Decision:** each agent holds one header key to one n8n endpoint set ([n8n-door.md](n8n-door.md)). The meeting door
  hands out only the rows due (an email domain, never the address) and accepts only a brief, 5 questions or a thank-you
  draft, only into that lead's empty cells, after its own checks. The blog intake checks every hand-in (duplicate
  topic, keyword, slug or slot, past slots, missing fields, bad images, dashes) before it saves anything.
- **Why:** least access. The worst a misbehaving run can do is fill an empty cell with text that passed the door's
  checks, or hand in a post that is refused or lands at Planned for a person to read. Pulling posts from the site side
  also avoids the web host's bot check, which blocks scripted calls into WordPress.
- **Weighed against:** Google access with a narrow scope. A token scoped to one sheet still lets the agent overwrite any
  cell in it; the door's rules are code that can be tested (120 offline and 16 live checks for the meeting door on
  18 Oct, 19 for the blog intake).
- **Trade-off:** n8n is one more moving part, with its own builder and tests.

### 3. The agents never send anything to a person (18 Oct)
- n8n emails the brief the morning before the meeting and the thank-you draft with an "Open in Outlook" button; the
  owner reads it and sends it themselves. A wrong word costs a second look, not a relationship.

### 4. Review mode until it has earned trust (15, 18 and 20 Oct)
- **Meeting agent:** every brief and thank-you went to the operator first until the owner gave the OK. Since then the
  operator still gets each new brief as soon as it is written, 2 days before the meeting, so a wrong word can be fixed on
  the sheet before the owner's 6:30 am email the day before.
- **Thank-you drafts go to the mailbox the owner actually sends from.** The button is a mailto link, and a mailto link
  opens whichever mail app the email is read in: read in a personal inbox it would start the reply from the wrong
  account, which the sent-mail watch cannot see. The operator's copy has no button, so nobody can send to a lead from
  the wrong account.
- **Blog agent:** every post lands at Planned with the agent's notes until a person approves it. Draft and publish
  modes exist, but need the owner's OK, and publish also needs the plugin's own gate.

### 5. Measure the cost, then cut it (15 to 19 Oct)
- **Blog agent:** the first estimate (US$2 to 4 a post) was wrong: test run 1 cost US$7.56 in 27 minutes. Its breakdown
  showed US$1.21 lost while the writer sat idle for 10 minutes waiting for the editor: the 5-minute prompt cache
  expired and 238,000 tokens were written again. **Cut:** the writer now waits in short checks under 5 minutes, so the
  cache stays warm, and runs the scorer and link checker in one call. The 19 Oct run cost US$5.22 (the session's own
  usage record) in about 20 minutes: cache writes fell from 688,000 to 359,000 tokens, the editor still ran in its own
  thread, and the post scored 90 like the first.
- **Meeting agent:** the estimate was US$0.40 to 0.80 a brief; measured, about 12 to 13 US cents (7 briefs for US$0.83 in
  the first live runs, US$0.39 for 3 in a later one).
- Every per-run cap followed a measurement, never a guess: the blog agent's went US$8, then US$12, then US$9.

### 6. The `auto` permission policy, and a receipt and alarm for every run (15 and 18 Oct)
- **Why `auto`:** nobody is there to approve a tool call during an unattended run; `auto` lets ordinary calls through
  and refuses risky ones. The blog agent's first run made 64 tool calls, all allowed.
- **Known risk:** a call the platform cannot decide pauses the run, and an unattended run then waits forever, silently.
- **Decision:** every meeting run ends by handing in its report (`report.py`); 40 minutes after a start with no receipt,
  n8n emails the operator an ALARM. The run state lives in a sheet, not in n8n's static data, which an active trigger
  can overwrite. The blog agent gets the same receipt and alarm before it runs on a schedule again.
- **Weighed against:** letting every bash call run without the platform's safety screen (`always_allow`). The screen
  stayed and the alarm was added.

### 7. Open internet, nothing private inside (15 Oct)
- **Decision:** unrestricted networking. Each brief is researched on a different business's own pages, each post cites
  different government, regulator and vendor pages, and the link checker opens every link. Limiting the network would
  also limit the web tools.
- **What limits the risk:** the one key is swapped in at the network edge for the n8n host only (the sandbox sees a
  placeholder), the agents get as little as possible (only the rows due, an email domain instead of an address, no raw
  keys), and every run has a hard budget cap.

### 8. Infrastructure as code, and a fresh history for this copy (15 to 19 Oct)
- The agents, skills, environments, vaults and deployments are files; `ant apply` makes the cloud match them and
  `claude-lock.json` records the versions. Every apply is a new version, so an old one can be restored, and a private
  repo always says what is running.
- A commit check (`tools/repo_check.py`) keeps keys and real details out, because GitHub's free plan does not scan
  private repos. A few early commits in the private repos held example details borrowed from real leads; they were
  documented rather than rewritten, those repos are never shared, and this public copy starts from the current files
  with a new history.

### 9. The ant login lives in its own folder (21 Oct)
- **Decision:** `ant` keeps its login in `%APPDATA%\Anthropic-agents`, set by `deploy.py` for `ant` only. The shared
  `%APPDATA%\Anthropic` stays empty.
- **Why:** least access. The shared folder is read by other Anthropic tools on the same machine (Claude Code among them),
  so a Console login kept there could be picked up by them and spend the credit the agents run on.
- **Weighed against:** logging out after each use (the login is needed while deploys run, so it would sit in the shared
  folder exactly then), and pointing the other tools at another folder instead (then every `ant` call made from them
  changes too). Cost: none. Guard: `deploy.py` prints a WARNING when a login is back in the shared folder.

## Meeting-brief agent

### 10. Claude Sonnet 5.5 (18 Oct)
- **Why:** short research plus careful writing. The two sample briefs approved before the build came from Sonnet 5.5,
  and it is half the price of Opus 5.5. Haiku 5.5 is far cheaper but riskier on the identity check and on tone.
- Model changes are tried side by side on the demo sheet first.

### 11. Wake only when there is work (18 Oct)
- **Decision:** n8n checks at 6:00 and 17:00 and starts the agent through Anthropic's API only when a brief (a meeting
  within 2 days) or a thank-you is due. The agent's own schedule stays paused for good.
- **Why:** the agent should work only when there is a meeting, so days with nothing due cost nothing. Two days ahead
  gives the operator a day to review before the owner's 6:30 am email on the day before the meeting.
- **Weighed against:** a daily schedule on Anthropic's side (simpler, but it runs and costs on empty days) and writing
  the brief on the morning of the meeting (no time to review).

### 12. Its own workspace, a monthly limit and a key that only works there (18 Oct)
- The agent's workspace has a US$5 monthly limit on top of the US$2 cap per run. The key n8n uses to start the agent
  cannot see or start the blog agent, and n8n only sends it to api.anthropic.com. A mistake in n8n is boxed in.

### 13. Research at booking time, not when a lead is added (18 Oct)
- Only a handful of the leads had booked. Researching everyone up front would cost more, go stale (one lead had left
  the group by the time they booked; another's role differed from the sheet) and could not be checked. The agent
  researches only the people the owner is about to meet.

### 14. A page reader instead of curl (18 Oct)
- The platform's `web_fetch` refuses a web address that only appeared in a tool's output, so on the first demo run the
  agent fell back to curl, which ignores the blocked sites and pulls raw HTML. `read_page.py` reads the page as plain
  text, capped, and refuses blocked sites; the run book says "never curl".

### 15. Facts sourced, guesses labelled, doubts listed (16 Oct)
- "A shorter, honest brief beats a fuller one with a guess dressed as a fact." Every brief ends with what could not be
  confirmed and where each fact came from.

### 16. A demo sheet (18 Oct)
- Demos never show a real member of the group: the demo sheet holds sample rows only, and the live session viewer is
  never opened on a shared screen.

### 17. The last question always asks for introductions (20 Oct)
- **Decision:** question 5 of every brief asks who in their network would need what the owner's business does or would
  enjoy meeting the owner, and whether they would make the introduction. The door refuses a brief whose question 5
  does not use the word "introduce", so "always" holds even if the model drifts.
- **Why:** the first seven briefs all asked how the owner could refer others and none asked for an introduction in
  return, the other half of a 1-2-1.
- **Trade-off:** a word check cannot tell which way an introduction goes, so the run book pins the direction and the
  operator's review copy is the second check. Questions 1 to 4 lean less on stock wording for the same reason: four of
  the first seven sets had repeated one example question word for word.

### 18. Prep notes in their own column (20 Oct)
- **Decision:** a Prep Notes column for what the owner wants from the next meeting: things to find out, to show, to
  remember. The door hands them to the agent with the brief job; the brief restates every point in a "Your notes:" line
  and turns each thing to find out into a question.
- **Why not Meeting Notes:** Meeting Notes are what the thank-you is written from once a meeting is Held, so plans typed
  there would come back as a thank-you for things that never happened. The first prep note was typed there, and moved.
- **Trade-off:** notes typed after the brief is written are not picked up by themselves: clear Brief, Questions and
  Brief Sent to have it rewritten.

## Blog agent

### 19. A second agent checks the facts, in its own context (15 Oct)
- **Why:** a writer checking its own facts tends to confirm them. The editor reads each claim cold against its source
  page. On the first run it fixed or softened 11 claims in a post that had already passed the scorer and link checker.

### 20. Claude Opus 5.5 for both agents (15 Oct)
- **Why:** long, careful writing and claim-by-claim checking, where a mistake is public. The editor on Sonnet 5.5 would
  save about US$0.90 a post; not applied, because quality comes first and the model is a person's call.

### 21. Thumbnails drawn in code (15 Oct)
- The site's series design is drawn with Pillow over a photo: exact words, exact brand colours, about 10 US cents. The
  photo is the one part code cannot make.

### 22. Deployed, measured, then on demand (15 and 19 Oct)
- At US$5 to 7.50 a post, the owner preferred not to pay per post, so the business's regular posts are written in
  supervised Claude Code sessions. The agent stays deployed and paused, and runs on demand, with its twice-weekly
  schedule kept in the file for when it is wanted.
