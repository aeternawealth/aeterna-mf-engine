---
name: seo-content
description: Writing or rewriting a hand-made page on aeternawealth.com (investor guide, tax guide, calculator page, insight, landing page) so it ranks and gets cited under Google's YMYL and E-E-A-T standards. Use when creating or improving a guide, tax page, calculator page or any non-templated page, choosing its target search, or writing its title, description, FAQ and internal links.
---

# Hand-written pages that rank on a finance site

Read first: `AGENTS.md` (site messaging), `docs/seo/strategy.md`, `docs/seo/keywords.md`. Templated data pages
follow `seo-programmatic`; this skill is for guides, tax pages, calculators and landing pages.

## 1. Pick the search
- One page per search intent. Check `docs/seo/keywords.md` and the site (`grep -r` in `site/dist`) for a page that
  already targets it; improve that page instead of adding a near-duplicate.
- Prefer searches where the top results are thin (forums, aggregator stubs) and we hold data or a calculator
  that answers better. Seasonal tax searches: publish or refresh 4-6 weeks before the peak (calendar in strategy.md).
- Record the target search and page in `docs/seo/keywords.md`.

## 2. Write it (Experience, Expertise, Authority, Trust)
- **Answer in the first two sentences**, with the number and the date ("For tax year 2026-27, income up to ₹12 lakh
  is tax-free under the new regime after the rebate").
- **Show our own working or data**: a worked example, a calculator result, a figure from our fund data. This is
  the "experience" Google looks for, and what AI answers quote.
- **Cite primary sources** by name with links: the Income-tax Act, 2025 and CBDT notifications (new section numbers
  only from the official CBDT mapping), SEBI circulars, AMFI. No figures copied from other blogs.
- **Plain English**, short paragraphs, headings phrased as the questions people ask, a table where a comparison is
  needed.
- **Dated**: "Updated <date>" and, for tax pages, the tax year in the title and H1. Refresh dates only when content
  changes.
- **No people's names or CA firms' names** on pages (owner's rule). Authority comes from the organisation, the ARN,
  the trust box, the editorial policy and the method page.

## 3. Messaging rules (owner's, non-negotiable)
No "best fund", "buy", "top picks" or guaranteed-return claims. Never advocate index funds or Direct plans; no cost
verdicts ("cheaper", "costs less"); plain expense-ratio figures as data are fine. Say "review", never "sell".
Positive framing: what an investor can gain. Keep the commission disclosure in the footer.

## 4. On-page SEO checklist
- Title under 65 characters: the search, then the qualifier (tax year, month, number). Description under 158
  characters with a concrete number.
- One H1; H2s as questions; descriptive URL (`/income-tax/<topic>/`, `/learn/<topic>/`).
- FAQ block (3-6 real questions, visible) with FAQPage JSON-LD; BreadcrumbList; HowTo only for real step lists.
- 3-8 internal links out (related calculators, data pages, method) and at least 2 links in from strong pages
  (hub, menu, related guides). Add the page to the hub and, if it is a key page, to `llms.txt`.
- Page in the sitemap (the generator's `urls.append`), canonical to itself, indexable.
- Images: real charts from our data, with alt text that states what the chart shows.

## 5. Ship
Build, `python tools/seo_audit.py`, `python tools/audit.py`, tests, Playwright look at 390px and 1280px in light
and dark, then publish per `AGENTS.md`. Log it in `docs/seo/log.md` and mark the backlog item done.
