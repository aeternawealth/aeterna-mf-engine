# Aeterna Wealth SEO strategy (25 Nov 2026)

## Where we stand
- Launched early November 2026: about 3,600 indexable pages in 3 weeks, almost no links from other sites, finance topic.
  Google holds finance pages ("Your Money or Your Life") to its strictest quality and trust bar.
- Early rankings for a new site often come and go for 2-4 months while Google tests it. Losing page 1 on a few searches
  in one day is usually that testing, not a penalty. What moves a site from "tested" to "trusted" is links and mentions
  from other sites, branded searches, and pages that are clearly the best answer.
- Audit of 25 Nov (tools/seo_audit.py): pages technically clean (no duplicate titles, no stray noindex, valid structured
  data, canonical tags correct). Fixed the same day: a menu link to a missing /compare/ page on every page; IndexNow was
  sent all 3,600 URLs on every deploy (now only changed pages). Open: www.aeternawealth.com serves a second copy (needs a
  Cloudflare redirect rule, owner, 1 minute).
- We cannot see Search Console from here. Until we can, decisions use the owner's weekly export (Performance: queries and
  pages, last 28 days vs previous) and Cloudflare analytics.

## The five levers, in order of effect

### 1. Trust (finance sites live or die on it)
- Who stands behind the numbers, on every data page: company, ARN-317889 with a link to AMFI's ARN search, address,
  regulated status, what Aeterna is not (not an investment adviser), how it is paid. Present: footer and About. To add: a
  short "Who makes these ratings" box on rating, fund and tax pages linking to Method, Disclosures and About.
- Editorial and corrections policy page (how data is sourced, checked, corrected; date of every update).
- Reviewer line on tax pages: "Checked by a chartered accountant" (no names, owner's rule), with the date checked.
- Google Business Profile (owner): verified address, phone, hours, photos, and genuine client reviews. The strongest
  single trust signal for a local financial business, and it feeds the knowledge panel that tells Google which
  "Aeterna" we are.
- Same name, address and phone everywhere (site, Business Profile, LinkedIn, Justdial, Instagram, X).

### 2. Authority: links and mentions from real sites
What works for a data site: being the source journalists and writers quote.
- **Monthly data story** from data only we publish: what fund managers bought and sold, crowded stocks, fund houses
  whose funds move together, money flows. Pitched in the first week after portfolios land (12th-16th) to personal-finance
  and markets journalists and newsletter writers, as a short note with 3 numbers and a chart, crediting
  aeternawealth.com. One story picked up by a national outlet is worth more than a hundred directory links.
- **Free, citable tools**: SIP, advance tax and income tax calculators that bloggers and CA firms link to. Offer an
  embeddable calculator with a visible "by Aeterna Wealth" credit (Google's rule: widget links are nofollow; the value is
  the brand mention and the people it sends).
- **Business listings** (each one link and one consistent NAP): Google Business Profile, Justdial, Sulekha, LinkedIn
  company page, Crunchbase, Tracxn, IndiaFilings/Zauba-style company pages, Bing Places, Apple Business Connect.
- **Partners**: CA firms that work with Aeterna can mention it on their sites. Where Aeterna pays the firm, the link must
  be marked rel="sponsored" (Google's rule for paid relationships).
- **Answers where people ask**: genuine answers on Quora, Reddit (r/IndiaInvestments, r/personalfinanceindia, following
  each forum's rules on self-promotion) and LinkedIn, linking to the specific page that answers the question. By the
  owner's or team's own account, never fake accounts.
- **Guest articles and podcasts**: finance blogs, CA and CS community sites, startup and HR newsletters (tax season
  content for employees).

### 3. Pages that are the best answer
- Data pages first: stock holding pages (one per listed stock), what funds bought and sold, crowded stocks, fund-house
  watch, money flows. No one else publishes these together, free. Each should answer its search in the first screen
  and add a 2-3 sentence plain-English reading of the numbers.
- Fund pages: lead with what people search for ("<fund> NAV, returns, rating"), keep Regular and Direct pages distinct
  (each says what is specific to its plan), and link related funds.
- Tax season calendar: advance tax (June, September, December, March), ELSS and 80C (January to March), ITR filing
  (June to July), capital gains (March and July). Publish and refresh 4-6 weeks before each peak.
- Keyword choice: searches with real volume where the top results are weak (forums, thin aggregator pages). Recorded in
  docs/seo/keywords.md with the page that targets each.
- Prune or merge pages that get no impressions after 3 months (noindex, keep for visitors).

### 4. Technical hygiene (daily, automated)
- tools/seo_audit.py --live every day: titles, descriptions, canonicals, sitemap, broken links, orphans, JSON-LD,
  redirects, preview hosts noindexed, key pages up.
- IndexNow on changed pages only (Bing, and through Bing ChatGPT search and Copilot). Google reads the sitemap.
- Speed: fonts served from the site, no layout jumps (all key pages under 0.03), pages under 100 KB compressed.
- llms.txt and clear structured data (organisation with ARN, breadcrumbs, FAQ where real) so AI answers cite us.

### 5. Measure, then double down
- Weekly: Search Console export from the owner (queries, pages, positions, 28 days vs previous). Track 30 target
  searches in docs/seo/keywords.md: position, clicks, which page ranks.
- Monthly: which pages gained and lost impressions; extend what works, fix or merge what does not.

### 6. AI answers (ChatGPT, Gemini, AI Overviews, Perplexity)
Same foundations: indexed pages, answer-first passages with a number and a date, trust on the page, consistent
entity data, and mentions on other sites (news, Reddit, Quora, listings), which AI assistants weigh most. Rules and
measurement: `.claude/skills/geo-ai-search/SKILL.md`. Programmatic pages: `.claude/skills/seo-programmatic/SKILL.md`
(no new page types while Google is rationing indexing).

## What we will not do, and why
Buying links, link networks, mass link swaps, comment and forum spam, fake reviews or accounts, AI-spun mass pages,
hidden text or cloaking, copying other sites' content. These are Google spam-policy violations. Finance sites that use
them get demoted or removed, and recovery takes months. Several also breach AMFI's code for distributors and SEBI's
advertising rules, which matter more to Aeterna than any ranking. Faster results come from the data stories and the
Business Profile, not shortcuts.

## Owner's to-dos that unlock the most
1. Cloudflare redirect rule: www.aeternawealth.com to aeternawealth.com, 301 (Rules > Redirect Rules > template
   "Redirect from WWW to root").
2. Google Business Profile: create and verify; ask 5 real clients for reviews.
3. Search Console: weekly export to the agent (or add read access when a connector exists); also verify the site in
   Bing Webmaster Tools (import from Search Console, 2 minutes).
4. Send the outreach drafts the SEO agent prepares in Gmail (it drafts; you send from your own account).
