# Office PC: monthly portfolio download for AMCs that block GitHub

HDFC, Navi, Union, Angel One and WhiteOak block requests from GitHub's servers (403 Forbidden, a Cloudflare
bot check, or a refused connection). Sundaram, Mahindra Manulife, Bandhan, LIC and HSBC can't yet be downloaded
from GitHub either (time-outs, encrypted APIs, or pages without file links), so the PC handles them too. A PC on an ordinary office or home connection can download their monthly
portfolio files. `tools/pc_download.py` downloads them and uploads them to `data/holdings_inbox/<month>/` in this repo.
The monthly run on the 12th picks them up automatically. If the PC misses a month, the engine keeps those funds'
previous portfolio, and the ops log shows it.

## One-time setup (about 15 minutes)

1. Install **Python 3.12** from python.org. Tick "Add python.exe to PATH".
2. Install **Git for Windows** from git-scm.com.
3. Open *Command Prompt* and clone the repo. Sign in when Git asks; Git Credential Manager remembers it.
   ```
   cd %USERPROFILE%
   git clone https://github.com/aeternawealth/aeterna-mf-engine.git
   cd aeterna-mf-engine
   python -m venv .venv
   .venv\Scripts\pip install -r requirements.txt
   ```
4. Test it once with the browser visible:
   ```
   .venv\Scripts\python tools\pc_download.py --show
   ```
   It prints one line per AMC (`OK` / `NOT_YET` / `FAILED`) and pushes the files. Send that output to Claude.
5. Schedule it. Open *Task Scheduler* and choose *Create Basic Task*:
   - Name: `Aeterna portfolio download`
   - Trigger: Monthly; Months: all; Days: **10, 11**; time **10:30**
   - Action: Start a program: `%USERPROFILE%\aeterna-mf-engine\tools\pc_download.bat`
   - After it's created, open the task's Properties and tick "Run task as soon as possible after a scheduled start is missed".

   It's safe to run more than once: AMCs already uploaded for that month are skipped.

## Notes
- On Windows the script drives the PC's own Microsoft Edge, so no separate Chromium download is needed. To use Playwright's Chromium instead, set `PW_CHANNEL=chromium` (and run `.venv\Scripts\python -m playwright install chromium`).
- The PC needs to be on, and logged in, on the 10th or 11th. Output goes to `pc_download.log` in the repo folder.
- To run it by hand for one AMC: `.venv\Scripts\python tools\pc_download.py --month 2026-10 --only HDFC --show`
- The repo is private. The PC only needs permission to push to it.
