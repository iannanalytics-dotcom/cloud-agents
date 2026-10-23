"""Deploy and run the blog agent on Anthropic's cloud (Claude Managed Agents) with the `ant` CLI.

Settings: copy settings.example.json to local/settings.json (git ignores local/), or point BLOG_AGENT_SETTINGS at your
own file, and fill it in. It holds the intake key, so it never goes in git.
Login: `ant auth login` once, in a window where ANTHROPIC_CONFIG_DIR points at the agents' own login folder
(%APPDATA%\\Anthropic-agents on Windows, see "The ant login folder" in SECURITY.md). This script sets that folder for
its own ant calls only. ANT_CLI = the ant executable if it is not on PATH; ANT_PROFILE = the login bound to the
workspace this agent runs in (or `ant_profile` in the settings), so another agent's login can never point these
commands at the wrong workspace.

Then, from this folder (blog-agent/):
    python tools/deploy.py check                 who is logged in, placeholders left, and the plan (changes nothing)
    python tools/deploy.py apply --yes           create or update the skill, both agents, the environment and the vault
    python tools/deploy.py credential            put the n8n intake key into the vault (read from the settings, never shown)
    python tools/deploy.py deployment --yes      create or update the schedule, then PAUSE it straight away
    python tools/deploy.py run [--watch]         start one run now (works while paused); --watch opens the live viewer
    python tools/deploy.py watch [--session ID]  open the live viewer for the latest run (or that one); costs nothing
    python tools/deploy.py status                the schedule, the last runs and their sessions
    python tools/deploy.py unpause --yes         let the schedule fire on its own (a person's call, after a good test run)
    python tools/deploy.py pause                 stop the schedule (runs already going carry on)
`--yes` is the person's approval: run `check` first and read the plan.
After any change to the files, run `check` then `apply --yes` again: the agents get a new version and the next run uses
it. In your own private copy, commit claude-lock.json with the files (this public copy ignores it).
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
ANT = os.environ.get("ANT_CLI", "ant")
LOCK = os.path.join(REPO, "claude-lock.json")    # written by `ant apply`; claude-lock.example.json shows its shape
SETTINGS = os.environ.get("BLOG_AGENT_SETTINGS") or os.path.join(REPO, "local", "settings.json")
BASE = ["agents/blog-writer/skills/blog-kit", "agents/blog-editor/agent.md", "agents/blog-writer/agent.md",
        "agents/blog-writer/environment.yaml", "agents/blog-writer/vault.yaml"]
DEPLOYMENT = "agents/blog-writer/deployment-review.yaml"
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
    print("vault id: %s" % (lock_id("agents/blog-writer/vault.yaml") or "not created yet"))
    print("deployment placeholders: %s" % (placeholders([DEPLOYMENT]) or "none"))


def apply(yes):
    if not yes:
        sys.exit("add --yes to apply (run `check` first and read the plan)")
    left = placeholders(BASE)
    if left:
        sys.exit("fill these first: %s" % left)
    print(ant("apply", "--yes", *BASE).stdout[-6000:])
    print("vault id: %s" % lock_id("agents/blog-writer/vault.yaml"))


def credential():
    vid = lock_id("agents/blog-writer/vault.yaml") or sys.exit("apply the vault first (apply --yes)")
    existing = ant("beta:vaults:credentials", "list", "--vault-id", vid, "--format", "json", check=False).stdout
    if "BLOG_INTAKE_KEY" in existing:
        print("the vault already holds BLOG_INTAKE_KEY; nothing to do (to replace it, archive that credential first)")
        return
    cfg = settings()
    body = {"display_name": "n8n blog intake key", "auth": {
        "type": "environment_variable", "secret_name": "BLOG_INTAKE_KEY", "secret_value": cfg["intake_secret"],
        "networking": {"type": "limited", "allowed_hosts": [cfg["n8n_host"]]}, "injection_location": {"header": True}}}
    r = ant("beta:vaults:credentials", "create", "--vault-id", vid, "--format", "json", stdin=json.dumps(body))
    out = json.loads(r.stdout) if r.stdout.strip().startswith("{") else {}
    print("credential created: %s (BLOG_INTAKE_KEY, sent only to %s, header only)" % (out.get("id", "?"), cfg["n8n_host"]))


def deployment(yes):
    vid = lock_id("agents/blog-writer/vault.yaml") or sys.exit("apply the vault first (apply --yes), then add the credential")
    path = os.path.join(REPO, DEPLOYMENT)
    text = open(path, encoding="utf-8").read()
    if "YOUR_VAULT_ID" in text:
        text = text.replace("YOUR_VAULT_ID", vid)
        open(path, "w", encoding="utf-8", newline="\n").write(text)  # LF: CRLF puts \r into the kickoff text
        print("vault id written into %s" % DEPLOYMENT)
    left = placeholders([DEPLOYMENT])
    if left:
        sys.exit("fill these first: %s" % left)
    if not yes:
        print(ant("apply", "--dry-run", "-v", DEPLOYMENT, check=False).stdout[-4000:])
        sys.exit("add --yes to create or update the schedule (it is paused straight after)")
    is_new = lock_id(DEPLOYMENT) is None
    print(ant("apply", "--yes", DEPLOYMENT).stdout[-3000:])
    did = lock_id(DEPLOYMENT)
    if is_new:  # a new deployment is live from the moment it exists: pause it at once
        ant("beta:deployments", "pause", "--deployment-id", did)
        print("deployment %s created and PAUSED (manual runs still work: `run`)" % did)
    else:
        print("deployment %s updated (its paused or unpaused state is unchanged)" % did)


def latest_session(did):
    r = ant("beta:deployment-runs", "list", "--deployment-id", did, "--max-items", "50", "--format", "jsonl", check=False)
    runs = [json.loads(line) for line in r.stdout.splitlines() if line.strip().startswith("{")]
    runs = [x for x in runs if x.get("session_id")]
    return max(runs, key=lambda x: x.get("created_at", ""))["session_id"] if runs else None


def view(sid, browser=True):
    """Open Anthropic's session viewer (served by ant on this machine) for one run; it follows every thread live."""
    print("Opening the live viewer for session %s." % sid)
    print("Close this window (or press Ctrl+C) when you are done. The run carries on in the cloud either way.", flush=True)
    subprocess.run([ANT, *profile_args(), "beta:sessions", "connect", sid, "--web"] + ([] if browser else ["--no-browser"]),
                   cwd=REPO, env=ANT_ENV)


def run(watch=False, browser=True):
    did = lock_id(DEPLOYMENT) or sys.exit("create the deployment first")
    out = ant("beta:deployments", "run", "--deployment-id", did, "--format", "json").stdout
    m = re.search(r'"session_id"\s*:\s*"([^"]+)"', out)
    sid = m.group(1) if m else latest_session(did)
    print("run started: session %s" % sid)
    if watch and sid:
        view(sid, browser)
    else:
        print("watch it: python tools/deploy.py watch --session %s" % sid)


def watch(sid=None, browser=True):
    did = lock_id(DEPLOYMENT) or sys.exit("no deployment yet")
    sid = sid or latest_session(did) or sys.exit("no runs yet")
    view(sid, browser)


def status():
    did = lock_id(DEPLOYMENT) or sys.exit("no deployment yet")
    print(ant("beta:deployments", "retrieve", "--deployment-id", did, "--format", "json", check=False).stdout[:2000])
    print(ant("beta:deployment-runs", "list", "--deployment-id", did, "--max-items", "5", "--format", "jsonl", check=False).stdout[:4000])


def switch(action, yes=True):
    did = lock_id(DEPLOYMENT) or sys.exit("no deployment yet")
    if action == "unpause" and not yes:
        sys.exit("add --yes: the schedule will then fire on its own")
    ant("beta:deployments", action, "--deployment-id", did)
    print("deployment %s %sd" % (did, action))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # ant prints symbols a Windows console code page lacks
    for problem in shared_login_problems():
        print("WARNING: " + problem, file=sys.stderr)
    a = sys.argv[1:]
    yes = "--yes" in a
    browser = "--no-browser" not in a
    sid = a[a.index("--session") + 1] if "--session" in a and a.index("--session") + 1 < len(a) else None
    cmd = a[0] if a else ""
    actions = {"check": check, "apply": lambda: apply(yes), "credential": credential, "deployment": lambda: deployment(yes),
               "run": lambda: run("--watch" in a, browser), "watch": lambda: watch(sid, browser), "status": status,
               "pause": lambda: switch("pause"), "unpause": lambda: switch("unpause", yes)}
    if cmd not in actions:
        sys.exit(__doc__)
    actions[cmd]()
