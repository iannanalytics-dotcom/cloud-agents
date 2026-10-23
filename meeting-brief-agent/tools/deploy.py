"""Deploy and run the meeting-brief agent on Anthropic's cloud (Claude Managed Agents) with the `ant` CLI.

Settings: copy settings.example.json to local/settings.json (git ignores local/), or point MEETING_AGENT_SETTINGS at
your own file, and fill it in. It holds the door key and the admin key, so it never goes in git.
Login: `ant auth login` once, in a window where ANTHROPIC_CONFIG_DIR points at the agents' own login folder
(%APPDATA%\\Anthropic-agents on Windows, see "The ant login folder" in SECURITY.md). This script sets that folder for
its own ant calls only. ANT_CLI = the ant executable if it is not on PATH; ANT_PROFILE = the login bound to the agent's
own workspace (or `ant_profile` in the settings).

Then, from this folder (meeting-brief-agent/):
    python tools/deploy.py check                    who is logged in, placeholders left, and the plan (changes nothing)
    python tools/deploy.py apply --yes              create or update the skill, the agent, the environment and the vault
    python tools/deploy.py credential               put the n8n door key into the vault (read from the settings, never shown)
    python tools/deploy.py deployment --yes         create or update BOTH deployments (live, demo), each PAUSED when new
    python tools/deploy.py run [--demo] [--watch]   start one run now (works while paused); --demo resets the demo sheet first
    python tools/deploy.py watch [--demo] [--session ID]   open the live viewer for the latest run (or that one); costs nothing
    python tools/deploy.py status                   both deployments, their last runs and the run monitor
    python tools/deploy.py reset-demo               put the demo sheet back to its two made-up jobs
    python tools/deploy.py unpause --yes            the agent works again: n8n starts it when work is due (and the alarm is on)
    python tools/deploy.py pause                    the agent stops: n8n starts nothing, alarm off (a run already going carries on)
    python tools/deploy.py test-alarm               email the operator a TEST alarm, so they know what a real one looks like
    python tools/deploy.py test-key                 does Anthropic accept n8n's key, and can it see the live deployment?
    python tools/deploy.py dispatch-test [--watch]  the whole n8n path on the DEMO sheet: reset it, n8n finds the work, starts a run
The agent's own Anthropic schedule stays paused for good: n8n (the run monitor, docs/n8n-door.md) looks for work twice
a day and starts a run only when something is due; every run ends with report.py, and a started run with no report 40
minutes later emails the operator an alarm.
`--yes` is the person's approval: run `check` first and read the plan. After any change to the files, run `check` then
`apply --yes` again (the agent gets a new version), then `deployment --yes` so both deployments use it.
In your own private copy, commit claude-lock.json with the files (this public copy ignores it).
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ANT = os.environ.get("ANT_CLI", "ant")
LOCK = os.path.join(REPO, "claude-lock.json")    # written by `ant apply`; claude-lock.example.json shows its shape
SETTINGS = os.environ.get("MEETING_AGENT_SETTINGS") or os.path.join(REPO, "local", "settings.json")
A = "agents/meeting-briefer/"
BASE = [A + "skills/brief-kit", A + "agent.md", A + "environment.yaml", A + "vault.yaml"]
DEPLOYMENTS = {"live": A + "deployment-live.yaml", "demo": A + "deployment-demo.yaml"}
PLACEHOLDER = re.compile(r"YOUR[_-][A-Z0-9_-]+")
# ant keeps its login in its own folder, never in the shared Anthropic folder that other Anthropic tools on the same
# machine (Claude Code among them) also read, so nothing else can sign in with the agents' Console login or spend its
# credit (docs/DECISIONS.md). The folder is set for ant's calls only, never globally.
ANT_HOME = os.path.join(os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config"), "Anthropic-agents")
SHARED_HOME = (os.path.join(os.environ["APPDATA"], "Anthropic") if os.environ.get("APPDATA")
               else os.path.join(os.path.expanduser("~"), ".config", "anthropic"))
ANT_ENV = {**os.environ, "ANTHROPIC_CONFIG_DIR": ANT_HOME}


def shared_login_problems():
    """Ways a Console login could reach other Anthropic tools, which read SHARED_HOME (or ANTHROPIC_CONFIG_DIR when set)."""
    problems = []
    if os.environ.get("ANTHROPIC_CONFIG_DIR"):
        problems.append("ANTHROPIC_CONFIG_DIR is set for the whole session, so other Anthropic tools read that folder too; "
                        "unset it (deploy.py sets it for ant only)")
    configs = os.path.join(SHARED_HOME, "configs")
    if os.path.isdir(configs) and any(n.endswith(".json") for n in os.listdir(configs)):
        problems.append("a login sits in the shared Anthropic folder (%s), where other tools on this machine can pick "
                        "it up; move it out (SECURITY.md, The ant login folder)" % configs)
    return problems


def settings(required=True):
    try:
        return json.load(open(SETTINGS, encoding="utf-8"))
    except (OSError, ValueError):
        if required:
            sys.exit("no settings at %s: copy settings.example.json there and fill it in" % SETTINGS)
        return {}


def profile_args():
    p = os.environ.get("ANT_PROFILE") or settings(required=False).get("ant_profile")
    return ["--profile", p] if p else []


def ant(*args, stdin=None, check=True):
    r = subprocess.run([ANT, *profile_args(), *args], cwd=REPO, input=stdin, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=ANT_ENV)
    if check and r.returncode != 0:
        sys.exit("ant %s failed:\n%s%s" % (" ".join(args[:3]), r.stdout[-2000:], r.stderr[-2000:]))
    return r


def lock_id(path):
    if not os.path.exists(LOCK):
        return None
    res = json.load(open(LOCK, encoding="utf-8")).get("resources", {})
    for key in ("./" + path, path):
        if key in res:
            return res[key].get("id")
    return None


def placeholders(paths):
    left = []
    for p in paths:
        full = os.path.join(REPO, p)
        files = [full] if os.path.isfile(full) else [os.path.join(d, f) for d, _, fs in os.walk(full) for f in fs]
        for f in files:
            if f.endswith((".md", ".yaml", ".yml", ".json")):
                for n, line in enumerate(open(f, encoding="utf-8", errors="replace"), 1):
                    if PLACEHOLDER.search(line):
                        left.append("%s:%d" % (os.path.relpath(f, REPO), n))
    return left


def check():
    print(ant("auth", "status", check=False).stdout.strip() or "(no auth status output)")
    left = placeholders(BASE)
    print("placeholders in the base files: %s" % (left or "none"))
    r = ant("apply", "--dry-run", "-v", *BASE, check=False)
    print(r.stdout[-6000:] + r.stderr[-2000:])
    print("vault id: %s" % (lock_id(A + "vault.yaml") or "not created yet"))


def apply(yes):
    if not yes:
        sys.exit("add --yes to apply (run `check` first and read the plan)")
    left = placeholders(BASE)
    if left:
        sys.exit("fill these first: %s" % left)
    print(ant("apply", "--yes", *BASE).stdout[-6000:])
    print("vault id: %s" % lock_id(A + "vault.yaml"))


def credential():
    vid = lock_id(A + "vault.yaml") or sys.exit("apply the vault first (apply --yes)")
    existing = ant("beta:vaults:credentials", "list", "--vault-id", vid, "--format", "json", check=False).stdout
    if "BRIEF_DOOR_KEY" in existing:
        print("the vault already holds BRIEF_DOOR_KEY; nothing to do (to replace it, archive that credential first)")
        return
    cfg = settings()
    body = {"display_name": "n8n meeting brief door key", "auth": {
        "type": "environment_variable", "secret_name": "BRIEF_DOOR_KEY", "secret_value": cfg["door_secret"],
        "networking": {"type": "limited", "allowed_hosts": [cfg["n8n_host"]]}, "injection_location": {"header": True}}}
    r = ant("beta:vaults:credentials", "create", "--vault-id", vid, "--format", "json", stdin=json.dumps(body))
    out = json.loads(r.stdout) if r.stdout.strip().startswith("{") else {}
    print("credential created: %s (BRIEF_DOOR_KEY, sent only to %s, header only)" % (out.get("id", "?"), cfg["n8n_host"]))


def deployment(yes):
    vid = lock_id(A + "vault.yaml") or sys.exit("apply the vault first (apply --yes), then add the credential")
    for which, rel in DEPLOYMENTS.items():
        path = os.path.join(REPO, rel)
        text = open(path, encoding="utf-8").read()
        if "YOUR_VAULT_ID" in text:
            # LF line endings: CRLF puts \r into the kickoff message
            open(path, "w", encoding="utf-8", newline="\n").write(text.replace("YOUR_VAULT_ID", vid))
            print("vault id written into %s" % rel)
        if not yes:
            print(ant("apply", "--dry-run", "-v", rel, check=False).stdout[-3000:])
            continue
        is_new = lock_id(rel) is None
        print(ant("apply", "--yes", rel).stdout[-2000:])
        did = lock_id(rel)
        if is_new:  # a new deployment is live from the moment it exists: pause it at once
            ant("beta:deployments", "pause", "--deployment-id", did)
            print("%s deployment %s created and PAUSED (manual runs still work: `run%s`)" % (which, did, " --demo" if which == "demo" else ""))
        else:
            print("%s deployment %s updated (its paused or unpaused state is unchanged)" % (which, did))
    if not yes:
        sys.exit("add --yes to create or update the deployments (new ones are paused straight after)")


def latest_session(did):
    r = ant("beta:deployment-runs", "list", "--deployment-id", did, "--max-items", "50", "--format", "jsonl", check=False)
    runs = [json.loads(line) for line in r.stdout.splitlines() if line.strip().startswith("{")]
    runs = [x for x in runs if x.get("session_id")]
    return max(runs, key=lambda x: x.get("created_at", ""))["session_id"] if runs else None


def view(sid, browser=True):
    print("Opening the live viewer for session %s." % sid)
    print("Close this window (or press Ctrl+C) when you are done. The run carries on in the cloud either way.", flush=True)
    subprocess.run([ANT, *profile_args(), "beta:sessions", "connect", sid, "--web"] + ([] if browser else ["--no-browser"]),
                   cwd=REPO, env=ANT_ENV)


def n8n_post(path_key, body, timeout=120):
    """POST to one of the door's admin webhooks with the admin key from the settings."""
    cfg = settings()
    req = urllib.request.Request("https://%s/webhook/%s" % (cfg["n8n_host"], cfg[path_key]), data=json.dumps(body).encode(),
                                 method="POST", headers={"Content-Type": "application/json", cfg["admin_header"]: cfg["admin_secret"]})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode() or "{}")


def reset_demo():
    try:
        res = n8n_post("demo_path", {"action": "reset"})
    except urllib.error.HTTPError as e:
        sys.exit("demo reset failed: %s %s" % (e.code, e.read().decode()[:300]))
    d = res.get("dates", {})
    print("demo sheet reset: DEMO-001 meeting %s (needs a brief), DEMO-002 met %s (needs a thank-you)" % (d.get("demo_001"), d.get("demo_002")))


def run(which, watch=False, browser=True):
    did = lock_id(DEPLOYMENTS[which]) or sys.exit("create the deployments first")
    if which == "demo":
        reset_demo()
    out = ant("beta:deployments", "run", "--deployment-id", did, "--format", "json").stdout
    m = re.search(r'"session_id"\s*:\s*"([^"]+)"', out)
    sid = m.group(1) if m else latest_session(did)
    print("%s run started: session %s" % (which, sid))
    if watch and sid:
        view(sid, browser)
    else:
        print("watch it: python tools/deploy.py watch%s --session %s" % (" --demo" if which == "demo" else "", sid))


def watch(which, sid=None, browser=True):
    did = lock_id(DEPLOYMENTS[which]) or sys.exit("no deployment yet")
    sid = sid or latest_session(did) or sys.exit("no runs yet")
    view(sid, browser)


def monitor(action, **extra):
    """Ask the n8n run monitor to do one thing (admin key from the settings). Never fails the command."""
    if not settings(required=False).get("monitor_path"):
        print("(no monitor_path in %s)" % SETTINGS)
        return None
    try:
        return n8n_post("monitor_path", dict({"action": action}, **extra))
    except Exception as e:  # noqa: BLE001
        print("(run monitor did not answer: %s)" % e)
        return None


def status():
    for which, rel in DEPLOYMENTS.items():
        did = lock_id(rel)
        print("== %s: %s" % (which, did or "not created"))
        if did:
            print(ant("beta:deployments", "retrieve", "--deployment-id", did, "--format", "json", check=False).stdout[:1500])
            print(ant("beta:deployment-runs", "list", "--deployment-id", did, "--max-items", "5", "--format", "jsonl", check=False).stdout[:3000])
    m = monitor("status")
    if m and m.get("ok"):
        print("== n8n: looks for work at %s, starts the agent only when work is due: %s (agent %s)" % (
            ", ".join(m.get("run_times") or []), m.get("dispatch"), m.get("agent")))
        print("== run monitor: alarm %s, checks %s min after a run n8n started" % (m.get("alarm"), m.get("check_after_min")))
        for r in m.get("last") or []:
            print("  %s  %-11s %-5s %s" % (r.get("when"), r.get("event"), r.get("sheet"), r.get("summary")))


def switch(action, yes=True):
    """pause = the agent stops working; unpause = it works again. The agent's Anthropic schedule stays paused for good
    and n8n starts a run only when work is due, so these switch n8n (agent on or off) and the alarm."""
    did = lock_id(DEPLOYMENTS["live"]) or sys.exit("no deployment yet")
    if action == "unpause" and not yes:
        sys.exit("add --yes: the agent will then work on its own again")
    off = action == "pause"
    ant("beta:deployments", "pause", "--deployment-id", did, check=False)  # its cron never fires: n8n starts the runs
    m = monitor("agent_off" if off else "agent_on", reason="%s with deploy.py" % action)
    print("n8n %s" % ("will not start the agent" if (m or {}).get("agent") == "off" else "starts the agent when work is due"))
    m = monitor("alarm_off" if off else "alarm_on", reason="agent %sd with deploy.py" % action)
    print("alarm %s" % ((m or {}).get("alarm") or "unchanged (see above)"))


def test_alarm():
    m = monitor("test_alarm") or {}
    print("TEST alarm emailed: %s" % m.get("subject") if m.get("ok") else "test alarm failed: %s" % m)


def test_key():
    m = monitor("test_key") or {}
    print(("the n8n key works (%s: %s)" % (m.get("checked"), m.get("answer"))) if m.get("ok")
          else "the n8n key does NOT work yet (%s): %s" % (m.get("checked"), m.get("error")))


def dispatch_test(watch=False, browser=True):
    """The whole n8n path on the demo sheet: reset it, ask n8n to look for work, n8n starts the demo deployment."""
    reset_demo()
    print("n8n:", json.dumps(n8n_post("dispatch_path", {"sheet": "demo"}, timeout=60))[:200])
    for _ in range(12):
        time.sleep(5)
        rows = (monitor("status") or {}).get("last") or []
        hit = [x for x in rows if x.get("sheet") == "demo" and x.get("event") in ("Run started", "Start failed", "Check failed")]
        if hit:
            x = hit[-1]
            print("%s  %s: %s | %s" % (x.get("when"), x.get("event"), x.get("summary"), x.get("detail")))
            if watch and x.get("session_id"):
                view(x["session_id"], browser)
            return
    print("no start logged within a minute: check the run log")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for problem in shared_login_problems():
        print("WARNING: " + problem, file=sys.stderr)
    a = sys.argv[1:]
    yes, demo, browser = "--yes" in a, "--demo" in a, "--no-browser" not in a
    which = "demo" if demo else "live"
    sid = a[a.index("--session") + 1] if "--session" in a and a.index("--session") + 1 < len(a) else None
    cmd = a[0] if a else ""
    actions = {"check": check, "apply": lambda: apply(yes), "credential": credential, "deployment": lambda: deployment(yes),
               "run": lambda: run(which, "--watch" in a, browser), "watch": lambda: watch(which, sid, browser),
               "status": status, "reset-demo": reset_demo, "pause": lambda: switch("pause"),
               "unpause": lambda: switch("unpause", yes), "test-alarm": test_alarm, "test-key": test_key,
               "dispatch-test": lambda: dispatch_test("--watch" in a, browser)}
    if cmd not in actions:
        sys.exit(__doc__)
    actions[cmd]()
