# SEO backlog (top = next). The daily SEO run takes one item a day and marks it done.

## Next
1. "Who makes these ratings" trust box on rating, fund, stock-holding and tax pages: Aeterna Wealth Private Limited,
   ARN-317889 (link to AMFI's ARN search), regulated status, data sources, date updated, links to Method, Disclosures,
   About. No names.
2. Editorial and corrections policy page (/editorial-policy/): sources, checks, update schedule, how to report an error;
   link from footer and the trust box.
3. Stock holding pages: a 2-3 sentence plain-English reading at the top ("376 schemes hold Axis Bank, worth about
   ₹82,692 cr; 12 bought more in October, 5 sold out...") so the page answers "which mutual funds hold <stock>" at once.
4. Split the sitemap into a sitemap index by type (funds, stocks, categories, tax, guides, data) so Search Console shows
   indexing by section.
5. Sitemap lastmod: the date a page's content fingerprint last changed (data/page-hashes.json history), not today's date
   on every URL.
6. Fund pages: make Regular and Direct pages more distinct (each leads with what is specific to its plan) and add
   "related funds" links within the category.
7. Tax season cluster ahead of January: ELSS and 80C last-minute page (published early January), "tax saving before 31
   March" checklist, capital gains harvesting before 31 March (from our own calculators).
8. Monthly data story template (docs/seo/pitch_template.md): 3 numbers, one chart image from the bought-and-sold page,
   credit line; used by the Monday outreach.
9. Embeddable SIP / advance tax calculator (iframe) with a visible "by Aeterna Wealth" credit (nofollow), and a page
   explaining how to embed it.
10. Dataset structured data on the data pages (what funds bought and sold, crowded stocks, money flows).
11. Home page: hidden app views carry their own H1s (11 on the page); make only the home view's H1 an H1.
12. Titles over 70 characters (about 580 pages): shorten the template endings so the fund or stock name and the key
    number show in full.

## Done
- 2026-11-25: /compare/ hub (the menu linked to a missing page); IndexNow only for changed pages; www visitors
  redirected by script (a Cloudflare 301 still needed); tools/seo_audit.py; fonts served locally (layout shift under
  0.03 everywhere); ARN and legal name in structured data; llms.txt lists the market-data and tax pages; /links/ page.
