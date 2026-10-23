# Where the private writing kit plugs in

The live blog agent's skill folder holds a full writing kit next to the run book. It was built for a client's websites
(their voice, their topics, their verified facts, their brand), so it stays private. This file lists each piece, what
the run book expects from it, and how it is checked, so the design is readable without the kit.

| Piece | Path in the skill folder | What the run book expects |
|---|---|---|
| SEO pre-scorer | `scripts/score_post.py <post folder> --site <site>` | A Python replica of the site's SEO plugin rubric plus house checks (sections, links, banned phrases, dashes). Prints `RESULT READY (score N)` at 80 or more with nothing to fix, else `RESULT NOT READY` and what to fix. `deliver.py` reads that line |
| Link checker | `scripts/check_links.py <post folder>` | Opens every link with browser headers, renders JavaScript help-centre pages in headless Chromium when one is installed, and prints `RESULT ALL OK` or each failing link |
| Inventory + clash rules | `scripts/build_inventory.py`, `scripts/clash.py` | The site's live posts (WordPress REST API, saved copy when the host's bot check blocks scripted calls) and the keyword clash rules: same keyword, plurals and hyphens = FIX; a phrase inside a live title or on a sister site = WARN |
| Brief builder | `scripts/brief.py <batch folder>` | Turns an approved `plan.json` into the writer's `brief.md` and the editor's brief; refuses a plan with gaps |
| Thumbnail renderer | `scripts/render_thumbnail.py` | The site's series design drawn with Pillow over a photo: exact words, exact brand colours, about 10 US cents |
| Standards | `references/writing-standard.md`, `planning.md`, `fact-checking.md` | How a post is built (structure, SEO, the closing block, meta.json), how one is planned (plan.json format, slots) and how claims are checked (primary sources, vendor help pages, quotes word for word) |
| Site profile | `sites/<site>.json`, `sites/<site>.md` | Host, cadence, categories, `never_link_hosts`, sister sites, reader, offer, voice, topic bank and topics done |
| Model posts | `models/<model post>/` | Two approved posts whose craft (not content) the writer copies |
| Prompts and word lists | `assets/` | The writer and editor briefs, the scorer's power and sentiment word lists, fonts, logo, photos |

The live kit is refreshed from the writing skill used for the same sites in supervised sessions, by a small build
script that also reports drift, so the cloud agent and the people writing by hand work to one standard.
