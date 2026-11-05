# Handover: status as of 5 Nov 2026

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

## Next, in order
1. Push this repo to `aeternawealth/aeterna-mf-engine` (private). Run the daily workflow manually, then the monthly one, and check the logs.
2. Test whether HDFC, Motilal Oswal, Navi and Union downloads work from GitHub's servers. If they don't, fall back to downloading them through the PC browser.
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
