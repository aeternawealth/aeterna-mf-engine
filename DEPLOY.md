# Deploying aeternawealth.com (Cloudflare Pages)

The engine repo stays private. GitHub Actions refresh the data and commit the built site to `site/dist/`.
Cloudflare Pages watches the repo, runs `site/build_site.py` and republishes `site/dist/` on every push.

## One-time setup (about 10 minutes)
1. Create a free account at dash.cloudflare.com.
2. Go to Workers & Pages → Create → Pages → Connect to Git, then authorise the `aeternawealth/aeterna-mf-engine` repo.
3. Build settings:
   - Framework preset: None
   - Build command: `python3 site/build_site.py`
   - Build output directory: `site/dist`
   - Production branch: `main`
   - Environment variable: `PYTHON_VERSION` = `3.11`
   The build makes the 1,700 fund and category pages, the sitemap, llms files and open data from the committed
   `site/data/` (standard library only; about 10 seconds). They are not committed to git, so the repo stays small.
4. Custom domains → add `aeternawealth.com` and `www.aeternawealth.com`.
   Cloudflare will ask you to move the domain's nameservers to Cloudflare (at your domain registrar), or to add a CNAME record.
   Before switching nameservers, check that the existing email (MX) records were copied across.

## Schedule
- Daily NAV refresh: Tue–Sat at 08:45 IST (`.github/workflows/daily.yml`)
- Monthly re-rating: the 11th and 16th at 14:50 IST (`.github/workflows/monthly.yml`); the office PC uploads blocked AMCs at 10:30 the same days
- Both can be run by hand from GitHub → Actions → choose the workflow → Run workflow.

## Launch switch
Until launch, every page says `noindex` and `robots.txt` blocks crawlers, so the `*.pages.dev` preview stays out of search.
At launch: create an empty file `site/LAUNCHED` and push. Then submit `https://aeternawealth.com/sitemap.xml` in Google
Search Console and Bing Webmaster Tools.

## Analytics
`site/site_config.json`: `cloudflare_beacon_token` (Cloudflare Web Analytics, cookieless) and `ga4_id` (Google Analytics 4,
standard tag, no cookie banner; disclose it in the privacy notice). Empty = not loaded.
