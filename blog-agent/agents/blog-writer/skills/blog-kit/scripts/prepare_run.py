"""Get one cloud run ready: a writable copy of the kit, what is already on the content sheet, the site's live posts and
the next free publishing slots. Run it first, every run.

Usage:  python prepare_run.py --site example --mode review          (mode: review, draft or publish)
        python prepare_run.py --site example --mode review --browser   also try to install headless Chromium, so
                                                                      check_links.py can render help-centre pages
                                                                      built with JavaScript
        add --workspace <dir> to work somewhere other than /workspace (local tests)

What it does, in order:
1. Copies this kit to <workspace>/kit (the uploaded skill folder may be read-only) and the quality models to
   <workspace>/models. Every later command runs from <workspace>/kit/scripts.
2. Makes sure Pillow is installed (the thumbnail script needs it).
3. Reads the sheet through the n8n intake's context address (key header from the BLOG_INTAKE_KEY variable) and saves
   it to <workspace>/context-<site>.json. Each post already on the sheet for this site becomes a folder under
   <workspace>/batches/sheet/, so build_inventory.py and score_post.py count its keyword as taken.
4. Refreshes the site's inventory of live posts (and its sister site's) from the WordPress REST API. If a site blocks
   the request, the inventory shipped with the kit is kept and a WARN says so.
5. Lists the next free slots on the site's cadence, at least lead_days ahead for the mode (agent_config.json), skipping
   every slot the sheet already holds for this site.
6. Writes <workspace>/run.json with all of the above and prints a summary.
The site profiles, models and inventory script belong to the private writing kit (KIT.md); without them it says so.
"""
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

sys.dont_write_bytecode = True
KIT_SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCAL_TZ = dt.timezone(dt.timedelta(hours=8))  # the site's time zone (Perth: UTC+8, no daylight saving)
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def say(msg):
    print(msg, flush=True)


def arg(name, default=None):
    a = sys.argv[1:]
    return a[a.index(name) + 1] if name in a and a.index(name) + 1 < len(a) else default


def copy_kit(ws):
    kit = os.path.join(ws, "kit")
    if os.path.normcase(os.path.abspath(KIT_SRC)) != os.path.normcase(os.path.abspath(kit)):
        if os.path.isdir(kit):
            shutil.rmtree(kit)
        shutil.copytree(KIT_SRC, kit, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    models = os.path.join(ws, "models")
    if os.path.isdir(models):
        shutil.rmtree(models)
    if os.path.isdir(os.path.join(kit, "models")):
        shutil.copytree(os.path.join(kit, "models"), models)
    else:
        say("WARN no models/ folder in the kit (private writing kit, KIT.md)")
    # Point every site at this workspace's batch folder (the kit ships /workspace/batches; local tests use another root).
    batches = os.path.join(ws, "batches").replace("\\", "/")
    os.makedirs(batches, exist_ok=True)
    sites = os.path.join(kit, "sites")
    for f in (os.listdir(sites) if os.path.isdir(sites) else []):
        if f.endswith(".json") and ".inventory" not in f:
            p = os.path.join(sites, f)
            s = json.load(open(p, encoding="utf-8"))
            if s.get("batch_root") != batches:
                s["batch_root"] = batches
                json.dump(s, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    return kit


def ensure_pillow():
    try:
        import PIL  # noqa: F401
        return "Pillow already installed"
    except ImportError:
        r = subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "pillow"], capture_output=True, text=True)
        return "Pillow installed" if r.returncode == 0 else "WARN Pillow install failed: " + r.stderr[-300:]


def ensure_browser():
    for name in ("google-chrome", "chromium", "chromium-browser", "chrome"):
        if shutil.which(name):
            return "browser already available: " + shutil.which(name)
    tries = [
        ["bash", "-lc", "(sudo -n true 2>/dev/null && S=sudo || S=) ; $S apt-get update -qq && $S apt-get install -y -qq chromium || $S apt-get install -y -qq chromium-browser"],
        ["bash", "-lc", "python3 -m pip install --quiet playwright && python3 -m playwright install --with-deps chromium "
                        "&& B=$(ls -d $HOME/.cache/ms-playwright/chromium-*/chrome-linux*/chrome | head -1) "
                        "&& mkdir -p $HOME/.local/bin && ln -sf \"$B\" $HOME/.local/bin/chromium"],
    ]
    for cmd in tries:
        try:
            subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        except Exception as e:  # noqa: BLE001
            say("  browser attempt failed: %s" % e)
        os.environ["PATH"] = os.path.expanduser("~/.local/bin") + os.pathsep + os.environ.get("PATH", "")
        for name in ("chromium", "chromium-browser", "google-chrome"):
            if shutil.which(name):
                return "browser installed: %s (add ~/.local/bin to PATH in later shells if check_links.py cannot find it)" % shutil.which(name)
    return "WARN no headless browser: check_links.py marks JavaScript help-centre links JS (unverified)"


def get_context(cfg, host):
    if "YOUR-N8N-HOST" in cfg["context_url"]:
        raise SystemExit("agent_config.json still has the YOUR-N8N-HOST placeholder")
    key = os.environ.get(cfg["key_env"], "")
    if not key:
        raise SystemExit("%s is not set: the vault credential is missing from this session" % cfg["key_env"])
    req = urllib.request.Request(cfg["context_url"] + "?site=" + host, headers={cfg["header"]: key, "Accept": "application/json"})
    last = None
    for _ in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last = "%s %s" % (e.code, e.read().decode("utf-8", "replace")[:200])
            if e.code in (401, 403):
                break
        except Exception as e:  # noqa: BLE001
            last = str(e)
    raise SystemExit("could not read the sheet through the intake: %s" % last)


def write_pipeline(ws, rows):
    root = os.path.join(ws, "batches", "sheet")
    if os.path.isdir(root):
        shutil.rmtree(root)
    for r in rows:
        name = r.get("slug") or ("row-%s" % r.get("row"))
        folder = os.path.join(root, name)
        os.makedirs(folder, exist_ok=True)
        json.dump({"topic": r.get("topic", ""), "blog_title": r.get("title") or r.get("topic", ""), "slug": r.get("slug", ""),
                   "focus_keyword": r.get("keyword", ""), "sheet_status": r.get("status", ""), "sheet_row": r.get("row")},
                  open(os.path.join(folder, "meta.json"), "w", encoding="utf-8"), indent=1)
    return root


def refresh_inventory(kit, site):
    script = os.path.join(kit, "scripts", "build_inventory.py")
    if not os.path.exists(script):
        return False, "build_inventory.py is not in this copy (private writing kit, KIT.md)"
    r = subprocess.run([sys.executable, script, "--site", site],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    out = (r.stdout + r.stderr).strip()
    if r.returncode != 0:
        try:
            fetched = json.load(open(os.path.join(kit, "sites", site + ".inventory.json"), encoding="utf-8")).get("fetched", "?")
        except Exception:  # noqa: BLE001
            fetched = "?"
        why = ("the site answered with the host's bot check instead of data" if "JSONDecodeError" in out or "Expecting value" in out
               else (out.splitlines() or ["unknown error"])[-1][:200])
        return False, ("%s; using the saved inventory from %s plus the sheet. Posts published since then outside the sheet are "
                       "not in it: also web_search site:<host> \"<keyword>\" before you settle on a keyword" % (why, fetched[:10]))
    return True, out.splitlines()[0] if out else "ok"


def free_slots(site_cfg, taken, lead_days, count=5):
    cad = site_cfg.get("cadence") or {"days": ["Tue", "Thu"], "time": "09:00"}
    hh, mm = [int(x) for x in cad.get("time", "09:00").split(":")]
    wanted = {DAYS.index(d) for d in cad.get("days", ["Tue", "Thu"])}
    earliest = dt.datetime.now(LOCAL_TZ) + dt.timedelta(days=lead_days)
    out, day = [], earliest.date()
    for _ in range(400):
        when = dt.datetime(day.year, day.month, day.day, hh, mm, tzinfo=LOCAL_TZ)
        text = when.strftime("%Y-%m-%d %H:%M")
        if when >= earliest and when.weekday() in wanted and text not in taken:
            out.append(text)
            if len(out) == count:
                break
        day += dt.timedelta(days=1)
    return out


def photos(kit):
    pdir = os.path.join(kit, "assets", "photos")
    if not os.path.isdir(pdir):
        return []
    listing = os.path.join(pdir, "photos.json")
    if os.path.exists(listing):
        return json.load(open(listing, encoding="utf-8"))
    return [{"file": f} for f in sorted(os.listdir(pdir)) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]


def main():
    site, mode = arg("--site"), (arg("--mode") or "review").lower()
    ws = arg("--workspace", "/workspace")
    if not site or mode not in ("review", "draft", "publish"):
        sys.exit(__doc__)
    os.makedirs(ws, exist_ok=True)
    kit = copy_kit(ws)
    cfg = json.load(open(os.path.join(kit, "agent_config.json"), encoding="utf-8"))
    profile = os.path.join(kit, "sites", site + ".json")
    if not os.path.exists(profile):
        sys.exit("no site profile at sites/%s.json: it comes from the private writing kit (KIT.md)" % site)
    site_cfg = json.load(open(profile, encoding="utf-8"))
    host = site_cfg.get("intake_site") or site_cfg["host"]
    now = dt.datetime.now(LOCAL_TZ)
    say("run prepared %s (site time) | site %s (%s) | mode %s" % (now.strftime("%a %d %b %Y %H:%M"), site, host, mode))
    say("kit: %s/scripts (run every script from here)" % kit.replace("\\", "/"))
    say(ensure_pillow())
    if "--browser" in sys.argv:
        say(ensure_browser())

    ctx = get_context(cfg, host)
    json.dump(ctx, open(os.path.join(ws, "context-%s.json" % site), "w", encoding="utf-8"), indent=1)
    rows = ctx.get("rows", [])
    write_pipeline(ws, rows)
    say("sheet: %d posts already on the content sheet for %s (saved to %s/context-%s.json)"
        % (len(rows), host, ws.replace("\\", "/"), site))
    for r in rows:
        say("  row %-3s %-10s %-16s %-34s %s" % (r.get("row"), r.get("status", "")[:10], r.get("slot", ""), r.get("keyword", "")[:34], r.get("title", "")[:60]))
    if ctx.get("other_sites"):
        say("other sites on the same sheet (sister sites): %s" % sorted({o["keyword"] for o in ctx["other_sites"] if o.get("keyword")}))

    ok, note = refresh_inventory(kit, site)
    say(("inventory refreshed: " if ok else "WARN inventory not refreshed (kept the copy shipped with the kit): ") + note)
    for sister in site_cfg.get("sister_sites", []):
        if os.path.exists(os.path.join(kit, "sites", sister + ".json")):
            ok2, note2 = refresh_inventory(kit, sister)
            say(("sister inventory refreshed (%s): " % sister if ok2 else "WARN sister inventory %s not refreshed: " % sister) + note2)

    taken = {r.get("slot") for r in rows if r.get("slot") and r.get("status") not in ("Binned", "WP Error")}
    lead = int(cfg.get("lead_days", {}).get(mode, 2))
    slots = free_slots(site_cfg, taken, lead)
    say("next free slots (%s, at least %d days ahead, site time): %s" % ("/".join(site_cfg.get("cadence", {}).get("days", [])), lead, ", ".join(slots)))
    pics = photos(kit)
    say("thumbnail photos in the kit: %s" % (", ".join(p["file"] for p in pics) if pics else "none (render with --photo none)"))

    run = {"prepared_at": now.isoformat(timespec="seconds"), "site": site, "host": host, "mode": mode, "workspace": ws,
           "kit": kit, "scripts": os.path.join(kit, "scripts"), "batch_root": site_cfg.get("batch_root"),
           "models": os.path.join(ws, "models"), "free_slots": slots, "taken_keywords": sorted({r.get("keyword", "") for r in rows if r.get("keyword")}),
           "taken_slugs": sorted({r.get("slug", "") for r in rows if r.get("slug")}), "photos": pics}
    json.dump(run, open(os.path.join(ws, "run.json"), "w", encoding="utf-8"), indent=1)
    say("saved %s/run.json" % ws.replace("\\", "/"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
