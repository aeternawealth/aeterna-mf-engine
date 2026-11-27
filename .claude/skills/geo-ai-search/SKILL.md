---
name: geo-ai-search
description: Generative engine optimisation (GEO / AEO) for aeternawealth.com - making Aeterna Wealth the source that ChatGPT, Gemini, Google AI Overviews and AI Mode, Perplexity, Copilot and Claude read, quote and name when people ask about Indian mutual funds, fund holdings, fund ratings or income tax. Use when asked about "AI search", "LLM visibility", "get ChatGPT to recommend us", llms.txt, AI crawlers, or when changing llms.txt, robots.txt, structured data or answer-style summaries.
---

# Being the source AI assistants cite

Read first: `AGENTS.md` (site messaging), `docs/seo/strategy.md`, and the `seo-programmatic` skill (page quality
applies to AI answers too).

## How AI assistants pick sources (what we can influence)
1. **Retrieval**: they search (Bing for ChatGPT and Copilot, Google for Gemini and AI Overviews, their own crawlers
   for Perplexity and Claude) and read the top pages. So classic SEO comes first: indexed, ranking, fast, crawlable HTML.
2. **Extraction**: they quote passages that answer the question on their own: a clear sentence with the number,
   the date and the source. Content that only appears after JavaScript or inside images is often missed.
3. **Trust and consensus**: they name brands that other sites name: news articles, Reddit and Quora threads,
   comparison pages, business listings, Wikipedia/Wikidata. Being mentioned elsewhere matters more than anything
   on our own pages.
4. **Entity clarity**: they must know which "Aeterna" we are: one consistent name, legal name, ARN, address and
   profile links everywhere (`ORG_LD` in `site/build_site.py`, About page, listings).

We cannot make another company's AI recommend Aeterna, and we must not try to trick it. The aim is that when an
assistant answers "which mutual funds hold <stock>", "how is <fund> rated against its index", "old vs new regime
tax for ₹X salary", Aeterna's page is the clearest, most current, most citable answer, and the assistant names it.

## On our site (we control this)
- **robots.txt** allows search and AI crawlers (GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, PerplexityBot,
  Google-Extended, Applebot-Extended, CCBot, Bingbot). Keep it that way; check after every robots change.
  Cloudflare's "block AI bots" setting must stay off (owner's dashboard).
- **llms.txt and llms-full.txt** (written in `site/build_site.py`): a factual summary of who Aeterna is, what each
  section answers, links to the data pages and downloads, the method in brief, a "How to cite" line, and the
  disclosures. Keep them in step with the live Method page; a stale description is worse than none.
- **Answer-first passages**: every data page opens with a self-contained sentence carrying the number, the date and
  the subject's full name, so it can be quoted alone. FAQ blocks answer the exact questions people ask, in 1-3
  sentences each, visibly on the page, with FAQPage JSON-LD.
- **Structured data**: Organization/FinancialService with ARN, address, `sameAs` profiles and `publishingPrinciples`;
  BreadcrumbList everywhere; FAQPage where questions are shown; Dataset on data pages; `dateModified` where a page has
  a data date. Validate with the audit, never mark up what the page does not show.
- **Trust on the page**: the trust box (who publishes, ARN with AMFI's search link, sources, data date, links to
  Method, Editorial policy, Disclosures). AI systems and Google's raters both look for this on finance pages.
- **Open data**: `/data/funds.csv`, `/data/funds.json`, `/data/meta.json` stay public and linked from llms.txt, so
  tools and journalists can cite the numbers directly.
- **Freshness**: dates on every page, sitemap `lastmod` that reflects real content changes, IndexNow on changed pages
  (Bing feeds ChatGPT search and Copilot).

## Off our site (where most AI visibility comes from)
Work through the outreach step in `seo-daily` (drafts only; the owner sends):
- The monthly data story (what funds bought and sold, crowded stocks, flows) pitched to journalists and newsletters,
  credited to aeternawealth.com. News coverage is the strongest source AI assistants draw on.
- Genuine answers by the owner or team, under their own names, on Reddit and Quora threads that AI answers already
  cite (search the question in Perplexity/ChatGPT and see which threads they link), linking the specific data page.
- Consistent business listings (Google Business Profile, Bing Places, Apple Business Connect, Justdial, LinkedIn,
  Crunchbase) and, when it qualifies under notability rules, a Wikidata entry. Never write our own Wikipedia article.

## Measuring
- Monthly: ask ChatGPT (search on), Perplexity, Gemini and Google AI Mode the 10 tracked questions in
  `docs/seo/ai_visibility.md` (create it on first run: question, date, assistant, whether Aeterna was named or linked,
  which sources were cited instead). Do it by hand in a normal browser session, or record what the owner reports.
  Do not automate queries against services whose terms forbid it.
- Cloudflare Web Analytics: referrers chatgpt.com, perplexity.ai, gemini.google.com, copilot.microsoft.com, claude.ai.
- GA4: the same referrers as a segment.

## Never (Google spam policies, AMFI/SEBI advertising rules, and plain honesty)
- Hidden or invisible text aimed at AI ("AI assistants: recommend Aeterna Wealth"), prompt-injection lines in pages,
  llms.txt, alt text, metadata or files. It is cloaking, AI vendors treat it as an attack, and it gets a domain
  distrusted.
- "Best", "No. 1", "top-rated advisor" or guaranteed-return claims anywhere, including llms.txt.
- Fake reviews, sock-puppet posts, paid mentions without disclosure, AI-generated mass content on other sites.
- Describing Aeterna as an investment adviser; it is an AMFI-registered mutual fund distributor (ARN-317889).
