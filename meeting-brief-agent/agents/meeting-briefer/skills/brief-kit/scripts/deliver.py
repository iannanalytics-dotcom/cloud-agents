"""Hand in ONE finished brief or thank-you through the n8n door.

Usage: python3 deliver.py --sheet live|demo --file /workspace/out/<LEAD-ID>.json [--check]
The file is JSON, one of:
  {"kind": "brief", "lead_id": "LEAD-000", "brief": "...", "questions": ["...", x5], "sources": ["..."], "not_confirmed": ["..."]}
  {"kind": "thank_you", "lead_id": "DEMO-002", "subject": "...", "body": "..."}
The same rules as the door are checked here first (--check = check only, send nothing). The door writes only empty cells
of that one lead and emails the result itself; this script never sees an email address.
Each hand-in (delivered, refused or door unreachable) is noted in /workspace/out/handed_in.jsonl for report.py.
Exit 0 = delivered, 2 = refused (the reasons are printed: fix the file and run it again), 3 = the door could not be reached.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, "..", "agent_config.json"), encoding="utf-8"))
R = CFG["rules"]
DASH = re.compile("[\u2013\u2014]")  # en and em dash: the house rule is none
EMAIL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
URL = re.compile(r"https?://", re.I)
WS = "/workspace" if os.path.isdir("/workspace") else os.getcwd()
LOG = os.path.join(WS, "out", "handed_in.jsonl")


def note_result(d, result, **extra):
    """Remember what happened to this hand-in, for the run report (report.py). Never stops a delivery."""
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        rec = dict({"kind": d.get("kind"), "lead_id": d.get("lead_id"), "result": result}, **extra)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


def has_phone(s):
    return any(len(re.sub(r"\D", "", m)) >= 9 for m in re.findall(r"[+(]?\d[\d ().-]{6,}\d", s))


def text_checks(errors, label, s, lo, hi, allow_url=False):
    if len(s) < lo:
        errors.append("%s is too short (%d characters, at least %d)" % (label, len(s), lo))
    if len(s) > hi:
        errors.append("%s is too long (%d characters, at most %d)" % (label, len(s), hi))
    if DASH.search(s):
        errors.append("%s has an en or em dash (house rule: none; use a comma, colon or full stop)" % label)
    if EMAIL.search(s):
        errors.append("%s contains an email address" % label)
    if has_phone(s):
        errors.append("%s contains what looks like a phone number" % label)
    if not allow_url and URL.search(s):
        errors.append("%s contains a web address (put it in sources instead)" % label)


def local_check(d):
    errors = []
    kind = d.get("kind")
    if kind not in ("brief", "thank_you"):
        return ["kind must be brief or thank_you"]
    if not str(d.get("lead_id", "")).strip():
        errors.append("lead_id is missing")
    if kind == "brief":
        text_checks(errors, "brief", str(d.get("brief", "")).strip(), R["brief_min"], R["brief_max"])
        qs = [str(q).strip() for q in d.get("questions") or [] if str(q).strip()]
        if len(qs) != R["questions"]:
            errors.append("questions must be a list of exactly %d (got %d)" % (R["questions"], len(qs)))
        for i, q in enumerate(qs):
            text_checks(errors, "question %d" % (i + 1), re.sub(r"^\s*\d+[.)]\s*", "", q), R["question_min"], R["question_max"])
        if len(qs) == R["questions"] and not re.search(R["intro_stem"], qs[-1], re.I):
            errors.append('question %d must ask them to introduce the owner to people in their network who need what the '
                          'owner\'s business does or would enjoy meeting the owner (use the word "introduce")' % R["questions"])
        src = [str(s).strip() for s in d.get("sources") or [] if str(s).strip()]
        if not src:
            errors.append("sources must list at least one source")
        for i, s in enumerate(src[:R["sources_max"]]):
            if DASH.search(s):
                errors.append("source %d has an en or em dash" % (i + 1))
        for i, s in enumerate(d.get("not_confirmed") or []):
            text_checks(errors, "not_confirmed %d" % (i + 1), str(s).strip(), 3, 250)
    else:
        text_checks(errors, "subject", re.sub(r"\s+", " ", str(d.get("subject", "")).strip()), 5, R["subject_max"])
        text_checks(errors, "body", str(d.get("body", "")).strip(), R["thank_you_min"], R["thank_you_max"], allow_url=True)
    return errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", choices=["live", "demo"], required=True)
    ap.add_argument("--file", required=True)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    d = json.load(open(a.file, encoding="utf-8"))
    errors = local_check(d)
    if errors:
        print("NOT SENT, fix these first:")
        for e in errors:
            print("  - " + e)
        sys.exit(2)
    if a.check:
        print("CHECK OK: %s for %s is ready to deliver" % (d["kind"], d["lead_id"]))
        return
    key = os.environ.get(CFG["key_env"], "")
    if not key:
        sys.exit("%s is not set: the vault credential is missing from this session" % CFG["key_env"])
    d["sheet"] = a.sheet
    data = json.dumps(d).encode("utf-8")
    last = None
    for attempt in range(3):
        req = urllib.request.Request(CFG["deliver_url"], data=data, method="POST",
                                     headers={CFG["header"]: key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                res = json.loads(r.read().decode("utf-8") or "{}")
            note_result(d, "handed_in")
            print("DELIVERED: " + json.dumps(res, ensure_ascii=False))
            return
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")
            if e.code == 422:
                try:
                    errs = json.loads(body).get("errors", [])
                except ValueError:
                    errs = [body[:300]]
                note_result(d, "refused", errors=[str(x)[:200] for x in errs][:5])
                print("REFUSED by the door:")
                for x in errs:
                    print("  - " + x)
                sys.exit(2)
            last = "%s %s" % (e.code, body[:300])
            if e.code in (400, 401, 403):
                break
        except Exception as e:  # noqa: BLE001
            last = str(e)
        time.sleep(8)
    note_result(d, "unreachable", error=str(last)[:300])
    print("COULD NOT DELIVER (the door could not be reached): %s" % last)
    sys.exit(3)


if __name__ == "__main__":
    main()
