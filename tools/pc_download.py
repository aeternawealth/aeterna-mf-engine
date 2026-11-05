"""Office-PC download of AMC portfolios whose websites block GitHub's servers.

Run on a Windows/Mac/Linux PC with this repo cloned (see PC_SETUP.md). It:
  1. pulls the latest repo,
  2. downloads the given month's portfolio files for the blocked AMCs (default: previous calendar month),
  3. copies them to data/holdings_inbox/<month>/<AMC>/ and pushes them to GitHub.
The monthly GitHub run on the 12th copies the inbox into data/holdings/<month>/ before downloading the rest.
Safe to run repeatedly: AMCs already in the inbox for that month are skipped.

    python tools/pc_download.py                 # previous month, all blocked AMCs
    python tools/pc_download.py --month 2026-10 --only HDFC --show
"""
import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Blocked from GitHub's servers (403 / bot check / refused / time-out), or not yet downloadable from there.
BLOCKED = ["HDFC-Mutual-Fund", "Navi-Mutual-Fund", "Union-Mutual-Fund", "Angel-One-Mutual-Fund", "WhiteOak-Capital-Mutual-Fund",
           "Sundaram-Mutual-Fund", "Mahindra-Mutual-Fund", "Bandhan-Mutual-Fund", "LIC-Mutual-Fund", "HSBC-Mutual-Fund"]
EXT = (".xlsx", ".xls", ".xlsm", ".xlsb", ".zip")


TASK_NAME = "Aeterna portfolio download"
TASK_DAYS = (11, 16)       # holdings days; the GitHub monthly runs follow at 14:50 IST the same days
TASK_TIME = "10:30"
TASK_VERSION = "2"        # bump to make every PC re-register its task on its next run


def ensure_schedule():
    """Windows only: keep this PC's Task Scheduler entry in line with the repo (days, time, missed-start
    catch-up), replacing any older entry that runs pc_download.bat. Runs as the current user; no admin needed."""
    if sys.platform != "win32":
        return
    marker = ROOT / "data" / ".pc_task_version"   # untracked (data/.* is not committed)
    if marker.exists() and marker.read_text().strip() == TASK_VERSION:
        return
    import tempfile
    bat = ROOT / "tools" / "pc_download.bat"
    days = "".join(f"<Day>{d}</Day>" for d in TASK_DAYS)
    xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>Aeterna MF engine: monthly portfolio download for AMCs that block GitHub (tools/pc_download.py)</Description></RegistrationInfo>
  <Triggers><CalendarTrigger><StartBoundary>2026-01-01T{TASK_TIME}:00</StartBoundary><Enabled>true</Enabled>
    <ScheduleByMonth><DaysOfMonth>{days}</DaysOfMonth><Months><January/><February/><March/><April/><May/><June/><July/><August/><September/><October/><November/><December/></Months></ScheduleByMonth>
  </CalendarTrigger></Triggers>
  <Principals><Principal id="Author"><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings><StartWhenAvailable>true</StartWhenAvailable><DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries><RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <ExecutionTimeLimit>PT2H</ExecutionTimeLimit><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><Enabled>true</Enabled></Settings>
  <Actions Context="Author"><Exec><Command>"{bat}"</Command><WorkingDirectory>{ROOT}</WorkingDirectory></Exec></Actions>
</Task>"""
    try:
        # remove older entries (any name) that run pc_download.bat, then register ours
        ps = ("Get-ScheduledTask | Where-Object { ($_.Actions | ForEach-Object { $_.Execute + ' ' + $_.Arguments }) -match 'pc_download' "
              f"-and $_.TaskName -ne '{TASK_NAME}' }} | Unregister-ScheduledTask -Confirm:$false")
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=False)
        with tempfile.NamedTemporaryFile("w", suffix=".xml", delete=False, encoding="utf-16") as f:
            f.write(xml)
        r = subprocess.run(["schtasks", "/Create", "/F", "/TN", TASK_NAME, "/XML", f.name], capture_output=True, text=True)
        Path(f.name).unlink(missing_ok=True)
        if r.returncode == 0:
            marker.write_text(TASK_VERSION)
            print(f"Scheduled task '{TASK_NAME}': days {TASK_DAYS} at {TASK_TIME}, catch-up after a missed start.")
        else:
            print("Could not update the scheduled task:", (r.stdout + r.stderr).strip()[:300])
    except Exception as e:   # never let scheduling stop the download
        print("Could not update the scheduled task:", e)


def git(*args, check=True):
    print("$ git", " ".join(args), flush=True)
    return subprocess.run(["git", *args], cwd=ROOT, check=check)


def main():
    import os
    import pandas as pd
    if sys.platform == "win32":   # Edge ships with Windows: no separate Chromium download (avoids side-by-side errors)
        os.environ.setdefault("PW_CHANNEL", "msedge")
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", default=(pd.Period(datetime.now(), "M") - 1).strftime("%Y-%m"))
    ap.add_argument("--only", default=None, help="comma-separated name parts, e.g. HDFC,Navi")
    ap.add_argument("--show", action="store_true", help="show the browser window (helps with bot checks)")
    ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args()

    git("checkout", "--", "data/holdings", check=False)
    git("pull", "--rebase", "--autostash", "origin", "main")
    ensure_schedule()
    inbox = ROOT / "data" / "holdings_inbox" / a.month
    amcs = [s for s in BLOCKED if not a.only or any(o.lower() in s.lower() for o in a.only.split(","))]
    todo = [s for s in amcs if not (inbox / s).exists() or not any(p.suffix.lower() in EXT for p in (inbox / s).rglob("*"))]
    if not todo:
        print(f"All of {', '.join(amcs)} already in the inbox for {a.month}; only uploading anything not yet pushed.")

    from engine import amc_downloader as D
    D.AMCS = todo
    D.list_amcs = lambda: todo   # only these, regardless of advisorkhoj's list
    rows = D.run(a.month, show=a.show) if todo else []

    got = []
    for slug, status, info, _ in rows:
        src = ROOT / "data" / "holdings" / a.month / slug
        files = [p for p in src.rglob("*") if p.is_file() and p.suffix.lower() in EXT] if src.exists() else []
        if status in ("OK", "SKIPPED") and files:
            dst = inbox / slug
            dst.mkdir(parents=True, exist_ok=True)
            for p in files:
                shutil.copy2(p, dst / p.name)
            got.append(slug)
        print(f"  {status:7s} {slug}: {len(files)} files  {'' if status == 'OK' else info[:160]}")
    log = inbox / "_pc_download_log.csv"
    inbox.mkdir(parents=True, exist_ok=True)
    with open(log, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M},{r[0]},{r[1]},\"{str(r[2])[:200]}\"\n")

    if a.no_push:
        return 0
    # the downloader rewrites data/holdings/<month>/_download_log.csv, which the GitHub runs track: put it back so
    # pulls and rebases never stop on it (this PC's log is kept in the inbox instead)
    git("checkout", "--", "data/holdings", check=False)
    git("add", "-f", str(inbox.relative_to(ROOT)))
    if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=ROOT).returncode != 0:
        git("commit", "-m", f"PC portfolio download {a.month}: {', '.join(got) or 'none OK'}")
    git("fetch", "origin", "main", check=False)
    ahead = subprocess.run(["git", "rev-list", "--count", "origin/main..HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if ahead == "0":
        print("Nothing new to upload.")
        return 0
    for i in range(3):   # the GitHub bot may have pushed meanwhile
        if git("push", "origin", "HEAD:main", check=False).returncode == 0:
            break
        git("pull", "--rebase", "--autostash", "origin", "main", check=False)
    else:
        print("PUSH FAILED: files are committed locally but not on GitHub. Sign in once with: git push origin HEAD:main")
        return 2
    print(f"Done: {len(got)}/{len(rows)} AMCs uploaded for {a.month}.")
    return 0 if got else 1


if __name__ == "__main__":
    sys.exit(main())
