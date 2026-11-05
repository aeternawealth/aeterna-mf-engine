# Handover: status as of 5 Nov 2026 (updated evening)

Read this file, `AGENTS.md` (methodology), `README.md` and `DEPLOY.md` before starting work.

## Done
- Engine v3: v3 pillars, tiers, guards and red flags, and 6M/1Y/3Y/5Y period ranks.
- Holdings coverage: 541 of 849 schemes (64%).
- Flows and Sharpe are shown for information only. Backtest finding: no predictive value, so the ratings are track-record ratings, not forecasts.
- Internal dashboard: `outputs/latest/dashboard.html`.
- Public site: `site/app.html`, with data built by `site/build_data.py` and the site by `site/build_site.py` into `site/dist`.
  - Covers MF, PMS, AIF and Bonds; Insurance shows "coming soon".
  - Uses the real logo.
  - Preview artifact: https://claude.ai/artifact/MF3TjNnSkiW2cZR4ZB3hh4
- Methodology audit doc: https://claude.ai/artifact/XsWiyNEVcnsaCBd9kQirf2
- GitHub Actions:
  - Daily refresh, Tue–Sat at 08:45 IST
  - Monthly re-rating on the 12th

## Backend, 5 Nov (afternoon session)
- Repo pushed to `aeternawealth/aeterna-mf-engine`. Daily and monthly workflows tested on GitHub; both pass.
- Holdings: 621 schemes / 1236 of 1687 plans (month 2026-09). 36/50 AMCs download from GitHub.
  - New direct adapters: Motilal Oswal, PGIM (.xlsb support), Groww, Canara (paginated). NJ fixed (file naming).
  - HDFC was never attempted (advisorkhoj `selected` option bug): fixed, but hdfcfund.com blocks GitHub (403).
- Safety: a month with no or partial portfolios falls back to the previous month for each fund (`holdings_month` column).
  Health checks fail the run below 450 funds with holdings, so a bad run is never committed.
- Blocked or unsolved from GitHub: HDFC, Navi, Union, Angel One, WhiteOak, Sundaram, Mahindra Manulife, Bandhan, LIC, HSBC.
  These go through the **office-PC download** (`tools/pc_download.py`, `PC_SETUP.md`), which pushes to
  `data/holdings_inbox/<month>/`; the monthly run merges it first. **Waiting on the PC setup and a first run.**
- Tools: the `Probe AMC pages` workflow (manual) inspects AMC pages and runs single-AMC download tests from GitHub;
  results go to the `probe-results` branch.
- Ops log (runs, AMC status, anomalies): https://claude.ai/artifact/8tQP7qmdP55yJGPpHFMp1b
  Scheduled checks in the Claude session: daily Tue–Sat 09:22 IST, monthly on the 12th at 11:47 IST (push + email).

## Next, in order
1. ~~Push repo, run workflows~~ done. ~~Test HDFC/Motilal/Navi/Union from GitHub~~ done: Motilal fixed; the rest go through the office PC.
2. Set up the office PC (`PC_SETUP.md`) and run it once with `--show`; fix any AMC that still fails there.
3. Set up Cloudflare Pages using `DEPLOY.md`, then point aeternawealth.com at it.
4. Scheduled Claude check-in on the 13th of each month: read the monthly run log, then fix or report problems.
5. SEO and AI discoverability:
   - Static HTML page for each fund and each category (the hash routes can't be indexed by search engines)
   - `sitemap.xml`
   - JSON-LD structured data
   - Open CSV and JSON data
   - Expand `llms.txt`
6. Remaining AMC adapters: Bandhan, Sundaram, LIC, Groww, HSBC, Mahindra, PGIM, Taurus, JM, Jio BlackRock, the rest of Canara, and the small AMCs.
7. Website placeholders still open: About bios, a backend for the contact form, and the holdings gaps.

## Rules
- Compliance:
  - Call them "track-record ratings"; no "best" or "buy" language.
  - Show ARN-317889 and the risk and commission disclosures.
- Don't tune the methodology to make the backtest look better.
- Never ask for passwords or access tokens in chat.
