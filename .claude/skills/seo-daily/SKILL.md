---
name: seo-daily
description: Aeterna Wealth's daily SEO routine. Run the SEO audit, fix what it flags, ship one improvement from the SEO backlog, prepare outreach drafts on Mondays, and log the day. Use when asked to "do the SEO run", by the daily scheduled task, or when working on aeternawealth.com rankings.
---

# Daily SEO run for aeternawealth.com

Read first, every run: `AGENTS.md` (publishing protocol and site messaging), `docs/seo/strategy.md` (why), the last 10
entries of `docs/seo/log.md` (what was done; do not repeat it), and `docs/seo/backlog.md` (what to do next).
Companion skills: `seo-programmatic` (bar for template-built pages: funds, stocks, categories, comparisons),
`seo-content` (guides, tax and calculator pages), `geo-ai-search` (being the source ChatGPT, Gemini, AI Overviews and
Perplexity cite). Load the one that fits the day's item.

## Hard rules (owner's standing instructions; never trade them for rankings)
- No rating changes: never edit `engine/` scoring, peer groups or tiers. Ranking changes need a thesis and the owner's OK.
- Site messaging: no "best"/"buy" claims; never advocate index funds or Direct plans; no cost verdicts; keep the
  commission disclosure; say "review", never "sell". No person's or CA firm's name on any page.
- Tax pages follow the Income-tax Act, 2025; show new section numbers only from the official CBDT mapping.
- Google spam policies and AMFI/SEBI advertising rules: no paid or swapped links, no link networks, no comment or forum
  spam, no fake accounts or reviews, no AI-spun mass pages, no cloaking, no copied content, no impersonation. Do not
  circumvent any site that blocks automated access.
- Outreach is drafted, never sent: create Gmail drafts for the owner, who reviews and sends. The owner's email address
  is given in the scheduled task's prompt; it is private: never write it into the repository, the site or any message to others.
- Never ask for passwords or tokens in chat.

## Branches and publishing
Work on `staging`. `staging` may hold commits awaiting the owner's approval (see `git log origin/main..origin/staging`
and any commit titled "HELD ON STAGING"): never merge `staging` into `main` while one is there. Publish your own commits
only: commit on staging, push, then `git checkout main && git pull && git cherry-pick <your commits> && git push`, then
merge main back into staging. Before publishing: `python site/build_site.py`, `python tools/seo_audit.py`,
`python tools/seo_guard.py` (the deploy runs it too; never weaken it), `python tools/audit.py` (nothing marked FAIL goes live), the tests in `.github/workflows/tests.yml`, and a browser check
of every page you changed at 390px and 1280px, light and dark (Playwright is installed). Clean `site/dist` and
`outputs/` before committing (only code and docs are committed; workflows rebuild data).

## The run (about an hour of work; stop when the day's item is done)
1. **Audit.** `python site/build_site.py && python tools/seo_audit.py --live`. Any FAIL: fix it first; that is the day's
   item. New CHECK lines since yesterday's log entry: fix or explain.
2. **Signals.** If `docs/seo/gsc/` has a new Search Console export from the owner, compare it with the previous one:
   queries and pages that gained or lost clicks, impressions or position. Update `docs/seo/keywords.md`. Cloudflare
   Web Analytics (GraphQL, account f5933230e8e718e0702500f52aa945cf, rumPageloadEventsAdaptiveGroups, filter by date,
   dimensions date/requestPath/refererHost): visits from Google per day and the top landing pages, last 7 days vs the 7
   before. One query.
3. **One improvement** from the top of `docs/seo/backlog.md` (or one the signals call for), done properly: content that
   answers the search better, internal links from strong pages, a title or description that matches what people type,
   structured data, a new page for a searched topic we cover with our own data, speed. Mark it done in the backlog with
   the date and commit.
4. **Mondays: outreach.** Prepare up to 5 personalised pitch drafts in Gmail (create_draft only) to journalists,
   newsletter writers, bloggers or business listings, each built on a specific number from this month's data pages
   (what funds bought and sold, crowded stocks, fund-house watch, money flows) with the page link. Record each target in
   `docs/seo/outreach.csv` (date, name/outlet, public contact source, angle, status=drafted) and never pitch the same
   person twice in 60 days. Public contact details only (the outlet's own site or the writer's own public profile).
5. **First run of each month: AI visibility.** Follow `geo-ai-search` > Measuring; update `docs/seo/ai_visibility.md`.
6. **Log** one entry in `docs/seo/log.md`: date, audit result, signal changes, what shipped (with commit), outreach
   drafted, next item. Publish.
7. **Report.** Mondays, and any day with a FAIL you could not fix: email the owner (address in the task prompt; send_message), subject
   "Aeterna SEO <date>", 10 lines: rankings and Google visits this week, what shipped, drafts waiting in Gmail, what the
   owner needs to do. Other days: a one-line push notification.

## Owner-only items (ask in the Monday report, do not attempt)
Cloudflare redirect rule for www; Google Business Profile and reviews; Search Console and Bing Webmaster verification
and exports; sending outreach drafts; anything that needs the owner's accounts.
