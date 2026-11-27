# SEO backlog (top = next). The daily SEO run takes one item a day and marks it done.

## Next
1. AI visibility baseline: create docs/seo/ai_visibility.md with 10 tracked questions (geo-ai-search skill) and the
   owner's first by-hand check in ChatGPT, Perplexity, Gemini and Google AI Mode.
2. Split the sitemap into a sitemap index by type (funds, stocks, categories, tax, guides, data) so Search Console shows
   indexing by section.
3. Sitemap lastmod: the date a page's content fingerprint last changed (data/page-hashes.json history), not today's date
   on every URL.
4. Fund pages: make Regular and Direct pages more distinct (each leads with what is specific to its plan) and add
   "related funds" links within the category.
5. Tax season cluster ahead of January: ELSS and 80C last-minute page (published early January), "tax saving before 31
   March" checklist, capital gains harvesting before 31 March (from our own calculators).
6. Monthly data story template (docs/seo/pitch_template.md): 3 numbers, one chart image from the bought-and-sold page,
   credit line; used by the Monday outreach.
7. Embeddable SIP / advance tax calculator (iframe) with a visible "by Aeterna Wealth" credit (nofollow), and a page
   explaining how to embed it.
8. Dataset structured data on the data pages (what funds bought and sold, crowded stocks, money flows).
9. Home page: hidden app views carry their own H1s (11 on the page); make only the home view's H1 an H1.
10. Titles over 70 characters (about 580 pages): shorten the template endings so the fund or stock name and the key
    number show in full.

## Done
- 2026-11-27: "Who makes these ratings" trust box on every fund, category, stock-holding, comparison, insight and tax
  page (no names; ARN linked to AMFI's distributor search; sources; data date). /editorial-policy/ (sources, checks,
  update schedule, corrections), linked from the footer, the trust box, llms.txt and the organisation's
  publishingPrinciples. llms-full.txt brought in line with the live method (it still described cost as 10% of the
  score); llms.txt gained a "How to cite" line. Stock pages already open with a plain-English reading (old item 3).
  Skills added: seo-programmatic, seo-content, geo-ai-search.
- 2026-11-25: /compare/ hub (the menu linked to a missing page); IndexNow only for changed pages; www visitors
  redirected by script (a Cloudflare 301 still needed); tools/seo_audit.py; fonts served locally (layout shift under
  0.03 everywhere); ARN and legal name in structured data; llms.txt lists the market-data and tax pages; /links/ page.
