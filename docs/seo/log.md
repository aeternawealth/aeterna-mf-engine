# SEO log (newest first). One entry per daily run.

## 2026-11-28 (owner's Search Console screenshot: impressions falling since 24 Nov)
- Search Console, 28 days: 161 clicks, 33.1K impressions. Impressions about 2.4-2.8K a day 13-23 Nov, then roughly
  1.8K (24 Nov), 0.7K (25 Nov), near 0 on the last point. Clicks held at about 12 a day to 25 Nov; the last point is 6.
- The last 1-2 days in Search Console are always incomplete, so the final point understates. The fall from 24 Nov
  is real, though: it began the day the Nov 2026 core update finished and the brand sitelinks disappeared.
- Live as Googlebot today: home, hubs, a stock page, a category page and the tax calculator all 200, index,follow;
  robots.txt and sitemap fine. Not a technical block. Our trust-box changes went live 27 Nov, after the fall began.
- Reading: a new finance site re-tested after a core update, with about 1,130 pages already "Discovered - not
  indexed". Brand clicks holding means the site is not removed. Need from the owner: Performance > Pages and Queries
  with Compare (last 7 days vs previous 7), Indexing > Pages count, and Security & Manual actions, to see whether the
  fall sits in one page type (stock, compare, fund pages) before acting.
- Proposed: no URL, title, menu or page-type changes for 2 weeks while Google re-evaluates (owner to decide).

## 2026-11-27 (brand sitelinks gone since about 24 Nov)
- Owner: the "aeterna wealth" result had sitelinks until about 24 Nov; now a single result (title, description and logo correct).
- Checked live as Googlebot: home and all section hubs 200, index,follow, self canonical; robots.txt allows all. Homepage
  links vs the build of 23 Nov: none removed, 14 added (tax, compare, market-data pages). Nothing we changed before 24 Nov
  explains it; the menu, noindex and section changes came on 25-27 Nov, after the drop.
- Reading: the Nov 2026 core update finished on 24 Nov; sitelinks are algorithmic and often reshuffle for small brands
  after one. Plan: request indexing for home and section hubs; keep section names and addresses stable; re-check 4 and 11 Dec.
- www: owner added the Cloudflare 301 rule; tested www home, a deep page and a query string (all 301 to the same
  address on aeternawealth.com). Stopgap www script removed from every page.

## 2026-11-27 (trust signals, AI search, skills)
- Audit: 0 FAIL (seo_audit: I1 titles over 70 chars, 580, unchanged; audit.py CHECK lines are data items, unchanged).
- Shipped: trust box on all data and tax pages; /editorial-policy/; publishingPrinciples in the organisation's
  structured data; llms-full.txt method text corrected to match /method/ (it said cost was 10% of the score, against
  the owner's rule and the live method); "How to cite" in llms.txt. Browser-checked at 390/1280, light/dark.
- Skills: seo-programmatic (quality gate for template pages: with ~1,130 pages "Discovered - not indexed", improve
  and earn trust before adding page types), seo-content (YMYL guides and tax pages), geo-ai-search (AI assistants).
- Next: backlog item 1 (AI visibility baseline), then sitemap index by type.

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
