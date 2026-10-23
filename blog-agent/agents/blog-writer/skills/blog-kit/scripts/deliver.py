"""Deliver one finished post to the content sheet through the n8n intake, or hold it back for a person.

Usage:
  python deliver.py --post "<post folder>" --site example --mode review --slot "2026-11-26 09:00" --thumb "<jpg>"
        [--hold "why it needs a person"] [--summary "two plain sentences"] [--editor-report-file "<txt>"] [--dry-run]

Modes (the run's kickoff says which):
  review   the row lands at Planned (held). Nothing reaches WordPress until a person changes Status to Written; it
           then arrives as a draft they schedule. The operator gets a "Needs a look" email.
  draft    the row lands at Written with Mode draft: the plugin imports it as a dated draft within the hour and a
           person presses Schedule.
  publish  the row lands at Written with Mode publish: the plugin imports it and schedules it for the slot by itself
           (only if its own score gate passes too). The operator gets an email and can still stop it before the slot.
  --hold "reason" turns any mode into a held row (Planned, Mode draft) with the reason in the email and the sheet.

Before sending it checks, again, what the intake will refuse anyway: score_post.py must print RESULT READY (unless held),
meta.json must have every field, the thumbnail must be a JPG of 10 to 700 KB, and nothing may hold an en or em dash.
Exit codes: 0 delivered (or held), 2 already on the sheet (a retry of a delivery that went through), 1 refused or failed,
3 not READY (fix it, or deliver with --hold).
The response is saved to <post folder>/delivery.json.
"""
import base64
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
DASH = re.compile("[\u2013\u2014]")  # en and em dash: the house rule is none
MARKER = "<!-- blog-agent:clean v1 -->"  # the line the writing standard puts first in every post.html


def arg(name, default=None):
    a = sys.argv[1:]
    return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default


def fail(msg, code=1):
    print("NOT DELIVERED: " + msg)
    sys.exit(code)


def score(folder, site):
    """(ready, score) from the private kit's scorer; (False, None) when it is not in this copy (KIT.md)."""
    script = os.path.join(HERE, "score_post.py")
    if not os.path.exists(script):
        return False, None
    out = subprocess.run([sys.executable, script, folder, "--site", site],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stdout
    m = re.search(r"RESULT (READY|NOT READY) \(score (\d+)", out)
    return (m.group(1) == "READY", int(m.group(2))) if m else (False, None)


def post(cfg, body):
    if "YOUR-N8N-HOST" in cfg["intake_url"]:
        fail("agent_config.json still has the YOUR-N8N-HOST placeholder")
    key = os.environ.get(cfg["key_env"], "")
    if not key:
        fail("%s is not set: the vault credential is missing from this session" % cfg["key_env"])
    data = json.dumps(body).encode("utf-8")
    last = None
    for attempt in range(4):
        req = urllib.request.Request(cfg["intake_url"], data=data, method="POST",
                                     headers={cfg["header"]: key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.status, json.loads(r.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", "replace")
            try:
                payload = json.loads(text)
            except ValueError:
                payload = {"raw": text[:300]}
            if e.code in (401, 403, 422):
                return e.code, payload  # a retry would get the same answer
            last = (e.code, payload)
        except Exception as e:  # noqa: BLE001  (timeout, connection reset)
            last = (0, {"error": str(e)[:300]})
        time.sleep(20 * (attempt + 1))  # 502: the sheet or Drive was busy; a retry after a timeout is safe (Topic is unique)
    return last


def main():
    folder, site, mode = arg("--post"), arg("--site"), (arg("--mode") or "").lower()
    slot, thumb, hold_reason = arg("--slot"), arg("--thumb"), arg("--hold")
    if not all([folder, site, mode, slot, thumb]) or mode not in ("review", "draft", "publish"):
        sys.exit(__doc__)
    cfg = json.load(open(os.path.join(KIT, "agent_config.json"), encoding="utf-8"))
    profile = os.path.join(KIT, "sites", site + ".json")
    if not os.path.exists(profile):
        fail("no site profile at sites/%s.json: it comes from the private writing kit (KIT.md)" % site)
    site_cfg = json.load(open(profile, encoding="utf-8"))
    meta = json.load(open(os.path.join(folder, "meta.json"), encoding="utf-8"))
    html = open(os.path.join(folder, "post.html"), encoding="utf-8").read()

    if mode == "review" and not hold_reason:
        hold_reason = "review mode: read it, then change Status to Written and it goes to WordPress as a draft"
    hold = bool(hold_reason)
    ready, est = score(folder, site)
    if not ready and not hold:
        fail("score_post.py does not say RESULT READY (score %s). Fix the post, or deliver it with --hold \"<reason>\"." % est, 3)

    need = ["blog_title", "seo_title", "meta_description", "slug", "focus_keyword", "tags", "category"]
    missing = [k for k in need if not meta.get(k)]
    if missing:
        fail("meta.json is missing: " + ", ".join(missing))
    if meta["category"] not in site_cfg.get("categories", []):
        fail("category %r is not one of the site's categories %s" % (meta["category"], site_cfg.get("categories")))
    tags = meta["tags"] if isinstance(meta["tags"], str) else ", ".join(meta["tags"])
    topic = meta.get("topic") or meta["blog_title"]
    for name, value in (("topic", topic), ("blog_title", meta["blog_title"]), ("seo_title", meta["seo_title"]),
                        ("meta_description", meta["meta_description"]), ("tags", tags)):
        if DASH.search(value):
            fail("%s has an en or em dash" % name)
    if not html.startswith(MARKER):
        fail("post.html must start with the %s marker line" % MARKER)
    if DASH.search(html):
        fail("post.html has an en or em dash")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:(00|30)", slot or ""):
        fail("--slot must look like 2026-11-26 09:00 (site time, on the hour or half hour)")
    raw = open(thumb, "rb").read()
    if raw[:3] != b"\xff\xd8\xff" or not (10_000 <= len(raw) <= 700_000):
        fail("the thumbnail must be a JPG of 10 to 700 KB (%d bytes)" % len(raw))

    summary = arg("--summary") or meta.get("excerpt") or meta["meta_description"]
    report_file = arg("--editor-report-file")
    sources = []
    for s in meta.get("sources") or []:
        if isinstance(s, dict):
            sources.append(("%s (%s)" % (s.get("url", ""), s.get("used_for", "")))[:300])
        else:
            sources.append(str(s)[:300])
    body = {
        "site": site_cfg.get("intake_site") or site_cfg["host"], "topic": topic, "primary_keyword": meta["focus_keyword"],
        "blog_title": meta["blog_title"], "seo_title": meta["seo_title"], "meta_description": meta["meta_description"],
        "slug": meta["slug"], "tags": tags, "category": meta["category"], "scheduled_for": slot,
        "mode": "publish" if (mode == "publish" and not hold) else "draft", "seo_score": est,
        "article_html": html, "thumbnail_jpg_base64": base64.b64encode(raw).decode("ascii"),
        "summary": summary, "sources": sources[:20],
        "editor_report": open(report_file, encoding="utf-8").read()[:6000] if report_file else "",
        "hold": hold, "hold_reason": hold_reason or "",
    }
    if "--dry-run" in sys.argv:
        show = dict(body, article_html="<%d characters>" % len(html), thumbnail_jpg_base64="<%d bytes>" % len(raw))
        print(json.dumps(show, indent=1, ensure_ascii=False))
        print("DRY RUN: nothing sent")
        return 0
    status, resp = post(cfg, body)
    json.dump({"status": status, "response": resp, "sent": {k: v for k, v in body.items() if k not in ("article_html", "thumbnail_jpg_base64")}},
              open(os.path.join(folder, "delivery.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    if status == 200 and resp.get("ok"):
        print("DELIVERED %s: row %s, status %s, mode %s, slot %s" % (resp.get("site"), resp.get("updated_range"), resp.get("status"),
                                                                 resp.get("mode"), resp.get("scheduled_for")))
        print("  article %s\n  thumbnail %s" % (resp.get("article_file"), resp.get("hero_image")))
        return 0
    if status == 422 and resp.get("code") == "duplicate_topic":
        print("ALREADY ON THE SHEET: %s (an earlier attempt went through, or the Topic was used before). Check the context before retrying." % resp.get("errors"))
        return 2
    fail("intake answered %s: %s" % (status, json.dumps(resp)[:800]))


if __name__ == "__main__":
    sys.exit(main())
