# SEO log (newest first). One entry per daily run.

## 2026-11-26 (night re-audit: "impressions fell to under 100")
- Live, as Googlebot smartphone (Playwright, 85 pages: home, hubs, funds, stocks, compare, tax, calculators): all 200,
  rendered meta robots index, one self canonical, valid JSON-LD, visible H1, no script errors. robots.txt allows all;
  sitemap 3,948 URLs; pages.dev carries X-Robots-Tag noindex (correct). <head> holds only meta/title/link/script/style,
  so nothing closes it before the robots and canonical tags.
- Build of 24 Nov (1832e78) vs today: 0 pages removed, 27 added; titles changed 2, H1/canonical/structured data 0;
  descriptions changed only by the NAV date; internal links to stock and compare pages unchanged (43 and 16-17 each).
  Only real difference: the 312 noindex tags (removed today, c45df52).
- Cloudflare: Googlebot fetched 188-266 pages a day on 23-26 Nov, all 200 (crawl unchanged). Visits from Google
  (Web Analytics, sampled): 23 Nov 30, 24 Nov 10, 25 Nov 30, 26 Nov 20, the same range as 10-22 Nov (0-20). 404s fell
  from 2-4K a day to ~400 after 21 Nov.
- Reading: no change of ours explains a sitewide fall. Search Console's "last 24 hours" view is incomplete for 2-3 days
  and the Nov 2026 core update finished rolling out on 24 Nov, when rankings reshuffle. Re-check 25-27 Nov in the
  Performance report (Date compare) on 29 Nov before acting.
- Noindex: restored (2247782) on the 308 less-compared comparison pairs and /privacy/, /terms/, /grievances/,
  /disclosures/, /links/. Reasons: 1,129 pages sit in "Discovered - currently not indexed", so Google is already
  rationing this site; near-duplicate fund-vs-fund pairs dilute quality signals; legal pages crowd brand sitelinks.
  Google had seen only 8 of them as noindex, so neither removing nor restoring caused the fall.
- Next: backlog item 1 (trust box).

## 2026-11-25 (set up)
- Audit: pages clean (0 FAIL); fixed a sitewide broken menu link (/compare/), IndexNow flooding, www duplicate (script;
  Cloudflare 301 pending, owner). tools/seo_audit.py added.
- Signals: no Search Console access; owner reports 2-3 searches dropped off page 1 today. Cloudflare: no fall in visits
  over the last 3 days (Google visits 10-30 a day, the highest yet).
- Shipped: commits a3bc0a1 (fonts, structured data, llms.txt, /links/), 1dd9a71 (SEO fixes).
- Next: backlog item 1 (trust box).
