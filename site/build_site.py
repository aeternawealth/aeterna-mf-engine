"""Wraps site/app.html into a full HTML document for GitHub Pages: site/dist/index.html (+ data/)."""
import shutil
from pathlib import Path
S = Path(__file__).resolve().parent
dist = S / "dist"; (dist / "data").mkdir(parents=True, exist_ok=True)
body = (S / "app.html").read_text(encoding="utf-8")
html = ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<style>:root{padding-top:env(safe-area-inset-top);padding-bottom:env(safe-area-inset-bottom)}[hidden]{display:none!important}img{max-width:100%}</style>'
        '<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 233 226%22%3E%3Cpath d=%22M0 0H137V43H43V137H0Z%22 fill=%22%231c1a17%22/%3E%3Cpath d=%22M185 0H233V137H145V226H0V185H90V88H185Z%22 fill=%22%230b4a3c%22/%3E%3C/svg%3E">'
        '</head><body>\n' + body + '\n</body></html>\n')
(dist / "index.html").write_text(html, encoding="utf-8")
for f in (S / "data").glob("*.json"):
    shutil.copy(f, dist / "data" / f.name)
(dist / "CNAME").write_text("aeternawealth.com\n")
# Search engines and AI assistants are welcome to read and cite the public research
(dist / "robots.txt").write_text("User-agent: *\nAllow: /\n\n# AI crawlers explicitly welcome\nUser-agent: GPTBot\nAllow: /\nUser-agent: ClaudeBot\nAllow: /\nUser-agent: PerplexityBot\nAllow: /\nUser-agent: Google-Extended\nAllow: /\n\nSitemap: https://aeternawealth.com/sitemap.xml\n")
(dist / "llms.txt").write_text("# Aeterna Wealth - Indian mutual fund research\n\n> Track-record ratings, returns vs total-return benchmarks, risk, costs, holdings and portfolio overlap for every Indian equity and index mutual fund. Published by Aeterna Wealth Private Limited, AMFI-registered mutual fund distributor (ARN-317889). Ratings describe past track records and are not forecasts or investment advice.\n\n## Open data\n- [All funds, latest metrics (JSON)](https://aeternawealth.com/data/funds.json)\n- [Dataset dates and sources (JSON)](https://aeternawealth.com/data/meta.json)\n\n## Pages\n- [Method and backtest](https://aeternawealth.com/#method)\n- [Disclosures](https://aeternawealth.com/#disclosures)\n")
print("built", dist)
