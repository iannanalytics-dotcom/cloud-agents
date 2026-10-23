"""Step 0 of every run: read the work list from the n8n door and save it to /workspace/work.json.

Usage: python3 get_work.py --sheet live|demo [--days N]
The work list holds only what the jobs need: Booked meetings coming up with no brief yet (briefs) and Held meetings with
Meeting Notes and no thank-you yet (thank_yous). Lead email addresses are never sent here, only the email domain.
Exit 0 = saved (even when there is nothing to do), 1 = the door could not be read (end the run and report it).
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, "..", "agent_config.json"), encoding="utf-8"))
OUT = "/workspace/work.json" if os.path.isdir("/workspace") else os.path.join(os.getcwd(), "work.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", choices=["live", "demo"], required=True)
    ap.add_argument("--days", type=int, default=None)
    a = ap.parse_args()
    if "YOUR-N8N-HOST" in CFG["context_url"]:
        print("could not read the work list: agent_config.json still has the YOUR-N8N-HOST placeholder")
        sys.exit(1)
    key = os.environ.get(CFG["key_env"], "")
    if not key:
        sys.exit("%s is not set: the vault credential is missing from this session" % CFG["key_env"])
    url = CFG["context_url"] + "?sheet=" + a.sheet + ("&days=%d" % a.days if a.days is not None else "")
    work, last = None, None
    for _ in range(3):
        req = urllib.request.Request(url, headers={CFG["header"]: key, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                work = json.loads(r.read().decode("utf-8"))
            break
        except urllib.error.HTTPError as e:
            last = "%s %s" % (e.code, e.read().decode("utf-8", "replace")[:300])
            if e.code in (400, 401, 403):
                break
        except Exception as e:  # noqa: BLE001
            last = str(e)
        time.sleep(5)
    if not isinstance(work, dict) or not work.get("ok"):
        print("could not read the work list: %s" % (last or json.dumps(work)[:300]))
        sys.exit(1)
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    json.dump(work, open(OUT, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print("Work list saved to %s" % OUT)
    print("Sheet %s | today %s (local time %s) | window %s days, to %s" % (
        work["sheet"], work["today"], work["now_local"], work["window_days"], work["window_until"]))
    print("Thank-yous to write: %d" % len(work["thank_yous"]))
    for t in work["thank_yous"]:
        print("  %s  %s (%s), met %s" % (t["lead_id"], t["full_name"], t["business"], t["meeting_date"] or "date not on the sheet"))
    print("Briefs to write: %d (at most %d this run, earliest meeting first)" % (len(work["briefs"]), CFG["max_briefs_per_run"]))
    for b in work["briefs"]:
        print("  %s  %s (%s), meeting %s | domain %s%s | website %s%s%s" % (
            b["lead_id"], b["full_name"], b["business"], b["meeting_date"] or "date not set", b["email_domain"] or "none",
            " (personal email, not an anchor)" if b.get("freemail") else "", b["website"] or "none",
            " | OWNER'S PREP NOTES: yes, see work.json" if b.get("prep_notes") else "",
            " | notes from an earlier meeting: yes" if b.get("meeting_notes") else ""))
    if work.get("booked_later"):
        print("Booked further out (not this run): %s" % ", ".join("%s %s" % (x["lead_id"], x["meeting_date"]) for x in work["booked_later"]))
    if not work["thank_yous"] and not work["briefs"]:
        print("NOTHING TO DO: finish with a one-line report.")


if __name__ == "__main__":
    main()
