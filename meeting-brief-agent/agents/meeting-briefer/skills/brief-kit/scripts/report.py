"""The last step of every run: hand in the run report (the run's receipt) to the n8n run monitor.

Usage: python3 report.py --sheet live|demo (--note TEXT | --note-file PATH)
It sends what this run had to do (/workspace/work.json), what deliver.py handed in or had refused
(/workspace/out/handed_in.jsonl) and your note: the final report (per job: handed in or skipped, the sources, the
doubts; then one line on anything the operator should look at). The monitor logs the run (counts and lead ids only) and
emails the operator the report when the run had work. When a run n8n started sends no report, the operator gets an
alarm. Send it on every run, also when there was nothing to do or the work list failed.
Exit 0 = reported, 3 = the monitor could not be reached (say so at the top of your last message).
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
WS = "/workspace" if os.path.isdir("/workspace") else os.getcwd()
WORK = os.path.join(WS, "work.json")
LOG = os.path.join(WS, "out", "handed_in.jsonl")


def read_log():
    out = []
    if os.path.exists(LOG):
        for line in open(LOG, encoding="utf-8"):
            line = line.strip()
            if line.startswith("{"):
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    return out[-80:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", choices=["live", "demo"], required=True)
    ap.add_argument("--note", default="")
    ap.add_argument("--note-file", default="")
    ap.add_argument("--test", action="store_true", help="logged as a Test report, no email (for checking the script)")
    a = ap.parse_args()
    note = a.note
    if a.note_file:
        try:
            note = (note + "\n" + open(a.note_file, encoding="utf-8").read()).strip()
        except OSError as e:
            note = (note + "\n(note file could not be read: %s)" % e).strip()
    work = None
    if os.path.exists(WORK):
        try:
            work = json.load(open(WORK, encoding="utf-8"))
        except ValueError:
            work = None
    body = {"sheet": a.sheet, "work_ok": bool(isinstance(work, dict) and work.get("ok")), "note": note[:4000],
            "jobs": [], "names": {}, "results": read_log(), "test": a.test}
    if body["work_ok"]:
        for kind, key in (("thank_you", "thank_yous"), ("brief", "briefs")):
            for j in work.get(key) or []:
                lid = str(j.get("lead_id", "")).strip()
                body["jobs"].append({"kind": kind, "lead_id": lid})
                body["names"][lid] = "%s (%s)" % (j.get("full_name", ""), j.get("business", ""))
    key = os.environ.get(CFG["key_env"], "")
    if not key:
        print("COULD NOT REPORT: %s is not set (the vault credential is missing from this session)" % CFG["key_env"])
        sys.exit(3)
    data = json.dumps(body).encode("utf-8")
    last = None
    for _ in range(3):
        req = urllib.request.Request(CFG["report_url"], data=data, method="POST",
                                     headers={CFG["header"]: key, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                res = json.loads(r.read().decode("utf-8") or "{}")
            print("REPORTED: %s | logged %s | emails %s" % (res.get("summary"), res.get("logged"), res.get("emails")))
            return
        except urllib.error.HTTPError as e:
            last = "%s %s" % (e.code, e.read().decode("utf-8", "replace")[:300])
            if e.code in (400, 401, 403):
                break
        except Exception as e:  # noqa: BLE001
            last = str(e)
        time.sleep(8)
    print("COULD NOT REPORT (the run monitor could not be reached): %s" % last)
    sys.exit(3)


if __name__ == "__main__":
    main()
