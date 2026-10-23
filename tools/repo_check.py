"""Safety checks for this repository. The git hooks in .githooks/ run it on every commit and every push.

    python tools/repo_check.py install          once per copy of the repo: turn the hooks on
    python tools/repo_check.py staged           what the pre-commit hook runs: the files about to be committed
    python tools/repo_check.py message <file>   what the commit-msg hook runs: the commit message
    python tools/repo_check.py push             what the pre-push hook runs: every commit not yet on GitHub
    python tools/repo_check.py tree             every tracked file as it is now (run it before sharing a copy)
    python tools/repo_check.py history          every file and message ever committed, on every branch (an audit)

What it stops:
- keys: anything shaped like an Anthropic, GitHub, Google, AWS, Slack or Telegram key, a private key, a Google
  service-account file, a JWT or an Anthropic resource id, plus the exact values of the real keys, read from the
  machine's settings folder (below). A key's value is never printed;
- files that never belong in a repo: .env, *.key, *.pem, credential and service-account files, anything over 5 MB;
- personal data: email addresses and phone numbers not listed in tools/repo_check_allow.txt, lead ids (LEAD-000 and
  DEMO-nnn are the made-up ones), and the real names, businesses, domains and ids in the private lists:
  private_terms.txt and this repo's own private_terms.<repo>.txt (<repo> = its name on GitHub or its folder name);
- commit messages that do not follow the convention in CONTRIBUTING.md.
The settings folder holds the private lists and the settings files with the real keys. It lives outside every repo and
is found through REPO_CHECK_SETTINGS, else the one-line pointer file tools/repo_check.local (git ignores it), else
../../../.claude next to the repo. Without it the pattern checks still run and a note says what was skipped.
A line that is a false alarm can end with "repo-check: allow"; say why in the commit message.
It never needs the internet and has no dependencies beyond Python. If it crashes, the commit is blocked (fails safe).
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)


def settings_dir():
    env = os.environ.get("REPO_CHECK_SETTINGS", "").strip()
    if env:
        return env
    try:
        pointer = open(os.path.join(HERE, "repo_check.local"), encoding="utf-8").read().strip()
        if pointer:
            return pointer
    except OSError:
        pass
    return os.path.normpath(os.path.join(REPO, "..", "..", "..", ".claude"))


SETTINGS_DIR = settings_dir()
PROJECT = os.path.dirname(os.path.normpath(SETTINGS_DIR))
PRIVATE_TERMS = os.path.join(SETTINGS_DIR, "private_terms.txt")
ALLOW_FILE = os.path.join(HERE, "repo_check_allow.txt")
MAX_BYTES = 5 * 1024 * 1024
ALLOW_MARK = "repo-check: allow"

KEY_PATTERNS = {
    "an Anthropic key or login token": r"sk-ant-[a-z0-9]{2,8}-[A-Za-z0-9_\-]{20,}",
    "an Anthropic resource id": r"\b(?:agent|env|vlt|vcrd|depl|drun|sesn|skill|skver|wrkspc)_[0-9A-Za-z]{16,}\b",
    "a GitHub token": r"\bgh[pousr]_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{40,}",
    "a Google API key": r"\bAIza[0-9A-Za-z_\-]{35}\b",
    "a private key": r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    "a Google service-account file": r"\"private_key_id\"\s*:|\"type\"\s*:\s*\"service_account\"",
    "an AWS key": r"\bAKIA[0-9A-Z]{16}\b",
    "a JWT (the shape of an n8n API key)": r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}",
    "a Telegram bot token": r"\b\d{8,10}:AA[A-Za-z0-9_\-]{30,}\b",
    "a Slack token": r"\bxox[abprs]-[A-Za-z0-9\-]{10,}",
    "a secret written into a setting": r"(?i)\b(api[_\-]?key|secret|token|password|passwd)[\"']?\s*[:=]\s*[\"'][A-Za-z0-9_\-+/=]{20,}[\"']",
    "a key written into a header": r"(?i)\bx-[a-z\-]*key[\"']?\s*[:=]\s*[\"'][A-Za-z0-9_\-]{20,}[\"']",
}
EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
PHONE = re.compile(r"(?<![\w.+])(?:\+61\s?4\d{2}|04\d{2}|\+61\s?[2378]|\(0[2378]\)|0[2378])[\s\-]?\d{3,4}[\s\-]?\d{3,4}(?![\w.])")
LEAD_ID = re.compile(r"\b(?!DEMO-\d{3}\b|LEAD-000\b)[A-Z]{2,5}-\d{3}\b")
ALWAYS_ALLOWED_EMAILS = {"noreply@anthropic.com", "noreply@github.com"}
ALLOWED_EMAIL_DOMAINS = ("example.com", "example.org", "example.net", "users.noreply.github.com")
BLOCKED_NAMES = [
    (re.compile(r"(^|/)\.env(\..*)?$"), "an .env file"),
    (re.compile(r"\.(key|pem|p12|pfx|kdbx)$", re.I), "a key file"),
    (re.compile(r"(^|/)id_(rsa|ed25519|ecdsa)[^/]*$"), "an SSH key"),
    (re.compile(r"(credential|service[-_]?account|gsheets_key)[^/]*\.json$", re.I), "a credentials file"),
    (re.compile(r"(^|/)claude-lock(\.[^/]*)?\.json$"), "a lock file with real resource ids (only claude-lock.example.json belongs here)"),
    (re.compile(r"(^|/)private_terms[^/]*\.txt$"), "a private list (it stays in the settings folder)"),
]
CONVENTION = re.compile(r"^(feat|fix|docs|chore|refactor|test|perf|build|ci|revert)(\([a-z0-9][a-z0-9\-]*\))?!?: \S")


def git(*args, data=None):
    return subprocess.run(["git", "-C", REPO, *args], input=data, capture_output=True, check=True).stdout


def secret_values():
    """Exact values of the real keys, from the machine's settings files. Missing files are fine (another machine)."""
    values = {}
    files = []
    if os.path.isdir(SETTINGS_DIR):
        for d, _, fs in os.walk(SETTINGS_DIR):
            if os.path.relpath(d, SETTINGS_DIR).split(os.sep)[0] in ("skills", "agents", "blog-writer-workspace"):
                continue
            files += [os.path.join(d, f) for f in fs if f.endswith(".json")]
    files.append(os.path.join(PROJECT, ".mcp.json"))
    for f in files:
        try:
            data = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        stack = [("", data)]
        while stack:
            path, obj = stack.pop()
            if isinstance(obj, dict):
                stack += [(f"{path}.{k}", v) for k, v in obj.items()]
            elif isinstance(obj, list):
                stack += [(f"{path}[{i}]", v) for i, v in enumerate(obj)]
            elif (isinstance(obj, str) and len(obj) >= 16 and re.search(r"secret|key|token|pass", path.rsplit(".", 1)[-1], re.I)
                  and not obj.startswith(("x-", "http")) and not obj.isupper()):
                values[obj] = os.path.basename(f) + ":" + path.lstrip(".")
    return values


def repo_names():
    """The names this repo's own list may be filed under: its GitHub name (from origin) and its folder name."""
    names = [os.path.basename(REPO)]
    try:
        url = git("config", "--get", "remote.origin.url").decode().strip()
        names.insert(0, re.sub(r"\.git$", "", url.rstrip("/").rsplit("/", 1)[-1]))
    except (subprocess.CalledProcessError, OSError):
        pass
    return list(dict.fromkeys(n for n in names if n))


def private_terms():
    terms = []
    for path in [PRIVATE_TERMS] + [os.path.join(SETTINGS_DIR, f"private_terms.{n}.txt") for n in repo_names()]:
        try:
            lines = open(path, encoding="utf-8").read().splitlines()
        except OSError:
            continue
        terms += [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]
    terms = list(dict.fromkeys(terms))
    return [(t, re.compile(r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9])", re.I)) for t in terms if len(t) >= 4]


def allowed():
    emails, phones = set(ALWAYS_ALLOWED_EMAILS), set()
    try:
        for line in open(ALLOW_FILE, encoding="utf-8"):
            item = line.split("#", 1)[0].strip()
            if "@" in item:
                emails.add(item.lower())
            elif item:
                phones.add(re.sub(r"\D", "", item))
    except OSError:
        pass
    return emails, phones


class Checker:
    def __init__(self):
        self.values = secret_values()
        self.terms = private_terms()
        self.emails, self.phones = allowed()
        self.problems = []

    def file_name(self, path, size):
        for pat, what in BLOCKED_NAMES:
            if pat.search(path.replace("\\", "/")) and not path.replace("\\", "/").endswith("claude-lock.example.json"):
                self.problems.append((path, 0, f"{what} must never be committed"))
        if size > MAX_BYTES:
            self.problems.append((path, 0, f"the file is {size // (1024 * 1024)} MB (limit 5 MB): keep big files out of git"))

    def text(self, where, text):
        for n, line in enumerate(text.splitlines(), 1):
            if ALLOW_MARK in line:
                continue
            for what, pat in KEY_PATTERNS.items():
                if re.search(pat, line):
                    self.problems.append((where, n, f"looks like {what} (value not shown)"))
            for value, source in self.values.items():
                if value in line:
                    self.problems.append((where, n, f"holds the real key from {source} (value not shown)"))
            for m in EMAIL.finditer(line):
                e = m.group(0).lower()
                if e not in self.emails and not e.endswith(ALLOWED_EMAIL_DOMAINS):
                    self.problems.append((where, n, f"an email address ({m.group(0)}): use someone@example.com"))
            for m in PHONE.finditer(line):
                if re.sub(r"\D", "", m.group(0)) not in self.phones:
                    self.problems.append((where, n, f"a phone number ({m.group(0).strip()})"))
            for m in LEAD_ID.finditer(line):
                self.problems.append((where, n, f"what looks like a real lead id ({m.group(0)}): use LEAD-000 or DEMO-001"))
            for term, pat in self.terms:
                if pat.search(line):
                    self.problems.append((where, n, f"a real person, business, domain or id from the private lists ({term})"))

    def blob(self, where, data):
        self.file_name(where.split(" @ ")[0], len(data))
        if b"\x00" in data[:8000]:
            return  # binary: name and size checked only
        self.text(where, data.decode("utf-8", "replace"))

    def report(self, action):
        if not self.problems:
            return 0
        seen, rows = set(), []
        for p in self.problems:
            if p not in seen:
                seen.add(p)
                rows.append(p)
        print(f"repo check: {action} blocked ({len(rows)} problem{'s' if len(rows) != 1 else ''})")
        for where, n, what in rows:
            print(f"  {where}{':' + str(n) if n else ''}  {what}")
        print("Fix those lines (made-up examples: LEAD-000, DEMO-001, someone@example.com), then try again.")
        print(f'A false alarm: end the line with "{ALLOW_MARK}" and say why in the commit message.')
        return 1


def notes(c):
    if not c.values:
        print("repo check: note: no settings files found in %s, so the exact-key check was skipped (pattern checks still ran)" % SETTINGS_DIR)
    if not c.terms:
        print("repo check: note: no private lists found in %s, so real names were not checked "
              "(set REPO_CHECK_SETTINGS or write the folder into tools/repo_check.local)" % SETTINGS_DIR)


def staged():
    c = Checker()
    names = [n for n in git("diff", "--cached", "--name-only", "--diff-filter=ACMR", "-z").decode("utf-8").split("\0") if n]
    for name in names:
        c.blob(name, git("show", ":" + name))
    notes(c)
    return c.report("commit")


def message(path):
    text = open(path, encoding="utf-8", errors="replace").read()
    text = text.split("# ------------------------ >8 ------------------------")[0]  # git commit -v adds the diff below
    lines = [line.rstrip() for line in text.splitlines() if not line.startswith("#")]
    while lines and not lines[0]:
        lines.pop(0)
    subject = lines[0] if lines else ""
    c = Checker()
    c.text("commit message", "\n".join(lines))
    if re.match(r"^(Merge|Revert) |^(fixup|squash)! ", subject):
        return c.report("commit")
    if not CONVENTION.match(subject):
        c.problems.append(("commit message", 1, 'first line must look like "type(scope): what changed", '
                           "type = feat, fix, docs, chore, refactor, test, perf, build, ci or revert (CONTRIBUTING.md)"))
    if len(subject) > 72:
        c.problems.append(("commit message", 1, f"first line is {len(subject)} characters (72 at most)"))
    if subject.endswith("."):
        c.problems.append(("commit message", 1, "first line ends with a full stop"))
    if len(lines) > 1 and lines[1]:
        c.problems.append(("commit message", 2, "leave line 2 empty (the summary, a blank line, then the why)"))
    return c.report("commit")


def scan_commits(c, commits):
    for sha in commits:
        c.text(f"message of {sha[:7]}", git("log", "-1", "--format=%B", sha).decode("utf-8", "replace"))
        out = git("diff-tree", "--no-commit-id", "-r", "--root", "-z", sha).decode("utf-8", "replace").split("\0")
        for meta, path in zip(out[0::2], out[1::2]):  # ":old new oldsha newsha status" then the path
            parts = meta.split()
            if len(parts) >= 5 and parts[4][0] in "AMC" and parts[3] != "0" * 40:
                c.blob(f"{path} @ {sha[:7]}", git("cat-file", "-p", parts[3]))


def push():
    c = Checker()
    commits = []
    lines = [] if sys.stdin is None or sys.stdin.isatty() else sys.stdin.read().splitlines()
    for line in lines:  # "<local ref> <local sha> <remote ref> <remote sha>" per ref being pushed
        parts = line.split()
        if len(parts) == 4 and parts[1] != "0" * 40:
            try:
                span = [parts[1], "^" + parts[3]] if parts[3] != "0" * 40 else [parts[1], "--not", "--remotes=origin"]
                commits += git("rev-list", *span).decode().split()
            except subprocess.CalledProcessError:  # GitHub has a commit this copy lacks: check all that is not there
                commits += git("rev-list", parts[1], "--not", "--remotes=origin").decode().split()
    if not lines:
        commits = git("rev-list", "HEAD", "--not", "--remotes=origin").decode().split()
    commits = list(dict.fromkeys(commits))  # a commit reached by both a branch and a tag is checked and counted once
    scan_commits(c, commits)
    notes(c)
    if not c.problems:
        print(f"repo check: {len(commits)} commit(s) to push, nothing found")
    return c.report("push")


def tree():
    c = Checker()
    for name in [n for n in git("ls-files", "-z").decode("utf-8").split("\0") if n]:
        try:
            c.blob(name, open(os.path.join(REPO, name), "rb").read())
        except OSError:
            pass
    notes(c)
    if not c.problems:
        print("repo check: every tracked file is clean")
    return c.report("check")


def history():
    c = Checker()
    commits = git("rev-list", "--all").decode().split()
    scan_commits(c, commits)
    notes(c)
    if not c.problems:
        print(f"repo check: {len(commits)} commits on every branch, nothing found")
    return c.report("history check")


def install():
    git("config", "core.hooksPath", ".githooks")
    print("hooks on: every commit and push in this copy now runs tools/repo_check.py (git config core.hooksPath .githooks)")
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    a = sys.argv[1:]
    actions = {"install": install, "staged": staged, "push": push, "tree": tree, "history": history,
               "message": lambda: message(a[1]) if len(a) > 1 else sys.exit("message needs the commit message file")}
    if not a or a[0] not in actions:
        sys.exit(__doc__)
    sys.exit(actions[a[0]]())
