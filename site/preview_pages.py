"""Design preview of a new home page (/preview/), unlisted: not linked, not in the sitemap, marked noindex.
Product-first layout: real data from site/data/funds.json in the hero, a tiled feature grid, three-step plan cards.
Shares the site's colours and fonts, so the comparison is about layout, not branding."""
import json
from pathlib import Path

HERE = Path(__file__).parent
PATH = "/preview/"

CSS = """<style>
.pv{--glow:rgba(31,107,88,.16);--card-sh:0 1px 2px rgba(20,33,30,.05),0 12px 32px -12px rgba(20,33,30,.18)}
.pv section{padding:72px 0}.pv .wrap{max-width:1180px}
.pv h1{font-size:clamp(38px,5.2vw,64px);line-height:1.04;letter-spacing:-.01em}
.pv h2{font-size:clamp(28px,3.4vw,42px);line-height:1.1}
.pv .eyebrow{color:var(--teal-2)}
.pv .lead{font-size:clamp(17px,1.5vw,19px);line-height:1.6;color:var(--ink-2);max-width:56ch;margin-top:18px}
.pv .btn{border-radius:999px;padding:13px 22px}
.pv-hero{position:relative;overflow:hidden;padding-top:64px!important}
.pv-hero:before{content:"";position:absolute;right:-12%;top:-10%;width:70%;height:120%;background:radial-gradient(closest-side,var(--glow),transparent 72%);pointer-events:none}
.pv-hg{display:grid;grid-template-columns:1.05fr .95fr;gap:56px;align-items:center;position:relative}
.pv-trust{display:flex;flex-wrap:wrap;gap:10px 22px;margin-top:28px;font-size:13.5px;color:var(--ink-3)}
.pv-trust b{font:600 14px var(--f-mono);color:var(--ink)}
.pv-stack{position:relative;display:grid;gap:16px}
.pv-card{background:var(--surface);border:1px solid var(--rule);border-radius:18px;box-shadow:var(--card-sh);padding:20px 22px}
.pv-card h3{font:600 15px var(--f-body);color:var(--ink-2);display:flex;justify-content:space-between;align-items:center}
.pv-card h3 span{font:500 12px var(--f-mono);color:var(--ink-3)}
.pv-rt{width:100%;border-collapse:collapse;margin-top:10px;font-size:14px}
.pv-rt td{padding:9px 0;border-top:1px solid var(--rule);text-align:left}.pv-rt td:last-child{text-align:right;font-family:var(--f-mono);color:var(--good)}
.pv-rt .tier{margin-right:10px}
.pv-plan{display:grid;grid-template-columns:1fr auto;gap:12px;align-items:center}
.pv-plan b{font:600 30px/1 var(--f-display);color:var(--ink)}.pv-plan small{display:block;color:var(--ink-3);font-size:13px;margin-top:6px}
.pv-ring{width:76px;height:76px}
.pv-float{margin-left:12%}
.pv-bento{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:18px;margin-top:34px}
.pv-tile{grid-column:span 2;background:var(--surface);border:1px solid var(--rule);border-radius:20px;padding:26px;display:flex;flex-direction:column;gap:10px;text-decoration:none;color:inherit;transition:transform .15s,box-shadow .15s;min-height:230px}
.pv-tile:hover{transform:translateY(-2px);box-shadow:var(--card-sh)}
.pv-tile.wide{grid-column:span 4}.pv-tile.tint{background:linear-gradient(160deg,var(--teal-soft),var(--surface) 70%)}
.pv-tile b{font:600 21px/1.25 var(--f-display);color:var(--ink)}.pv-tile p{margin:0;color:var(--ink-2);font-size:15px;line-height:1.55}
.pv-tile .go{margin-top:auto;font-weight:600;color:var(--teal)}
.pv-vis{margin-top:6px}
.pv-steps{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:18px;margin-top:34px}
.pv-step{background:var(--surface);border:1px solid var(--rule);border-radius:20px;padding:26px}
.pv-step i{font:600 13px var(--f-mono);color:var(--teal-2);font-style:normal}.pv-step b{display:block;font:600 21px var(--f-display);margin-top:10px}.pv-step p{margin:8px 0 0;color:var(--ink-2);font-size:15px}
.pv-band{background:var(--band)}
.pv-nums{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:18px;margin-top:30px}
.pv-nums div{border-left:2px solid var(--teal-soft);padding-left:16px}.pv-nums b{display:block;font:600 34px/1.1 var(--f-display);color:var(--ink)}.pv-nums span{color:var(--ink-3);font-size:14px}
.pv-cta{background:var(--teal);color:#fff;border-radius:24px;padding:48px;display:flex;justify-content:space-between;align-items:center;gap:24px;flex-wrap:wrap}
.pv-cta h2{color:#fff}.pv-cta p{color:rgba(255,255,255,.82);margin-top:10px;max-width:52ch}.pv-cta .btn{background:#fff;color:var(--teal);border-color:#fff}
.pv-note{background:var(--surface);border:1px dashed var(--rule);border-radius:12px;padding:10px 14px;font-size:13px;color:var(--ink-3);margin-bottom:22px}
@media (max-width:960px){.pv-hg{grid-template-columns:1fr;gap:36px}.pv-bento{grid-template-columns:1fr 1fr}.pv-tile,.pv-tile.wide{grid-column:span 2}.pv-steps,.pv-nums{grid-template-columns:1fr 1fr}.pv-float{margin-left:0}}
@media (max-width:600px){.pv section{padding:48px 0}.pv-bento{grid-template-columns:1fr}.pv-tile,.pv-tile.wide{grid-column:span 1;min-height:0}.pv-steps,.pv-nums{grid-template-columns:1fr}.pv-cta{padding:28px}}
</style>"""


def _spark(points, w=260, h=60):
    lo, hi = min(points), max(points)
    xs = [i * w / (len(points) - 1) for i in range(len(points))]
    ys = [h - 6 - (p - lo) / ((hi - lo) or 1) * (h - 12) for p in points]
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(xs, ys))
    return (f'<svg class="pv-vis" viewBox="0 0 {w} {h}" width="100%" height="{h}" aria-hidden="true"><polyline points="{d}" fill="none" '
            f'stroke="var(--teal)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def preview_pages(B, urls):
    funds = json.loads((HERE / "data" / "funds.json").read_text(encoding="utf-8"))
    funds = funds["funds"] if isinstance(funds, dict) else funds
    n = len(funds)
    rated = sum(1 for f in funds if f.get("tier") in ("A+", "A", "B", "C"))
    cats = len({f.get("category") for f in funds})
    top = sorted([f for f in funds if f.get("category") == "Flexi Cap" and f.get("plan_type") == "Regular" and f.get("tier") == "A+"
                  and f.get("excess_3Y") is not None], key=lambda f: -(f.get("score") or 0))[:3]
    rows = "".join(f'<tr><td>{B.tier_badge(f["tier"])}{B.e(f["name"][:34])}</td><td>+{f["excess_3Y"] * 100:.1f}%</td></tr>' for f in top)
    ring = ('<svg class="pv-ring" viewBox="0 0 36 36" aria-hidden="true"><circle cx="18" cy="18" r="15.5" fill="none" stroke="var(--rule)" stroke-width="3.5"/>'
            '<circle cx="18" cy="18" r="15.5" fill="none" stroke="var(--teal)" stroke-width="3.5" stroke-linecap="round" stroke-dasharray="58 100" transform="rotate(-90 18 18)"/>'
            '<text x="18" y="21" text-anchor="middle" style="font:600 8px var(--f-mono);fill:var(--ink)">58%</text></svg>')
    ring = '<div style="text-align:center">' + ring + '<small style="display:block;font-size:11px;color:var(--ink-3)">of target<br>covered today</small></div>'
    body = CSS + f"""<div class="pv">
<section class="pv-hero"><div class="wrap">
 <p class="pv-note">Design preview, not linked from the site. Same data and brand, new layout. <a href="/">Current home page</a></p>
 <div class="pv-hg"><div>
  <div class="eyebrow">Aeterna Wealth · AMFI-registered mutual fund distributor</div>
  <h1 style="margin-top:14px">Every fund in India, measured. Your money, planned.</h1>
  <p class="lead">We rate {n:,} mutual fund plans against the right benchmark every month and turn your goals into an exact monthly plan. Then we help you stay with it.</p>
  <div class="row" style="margin-top:28px;gap:12px"><a class="btn primary" href="/plan/">Build my Money Plan</a><a class="btn" href="/#ratings">See fund ratings</a></div>
  <div class="pv-trust"><span><b>{n:,}</b> plans tracked</span><span><b>{cats}</b> categories</span><span>Updated <b>every weekday</b></span><span><b>ARN-317889</b></span></div>
 </div>
 <div class="pv-stack">
  <div class="pv-card"><h3>Flexi Cap · top rated <span>vs Nifty 500 TRI, 3Y a year</span></h3><table class="pv-rt">{rows}</table></div>
  <div class="pv-card pv-float"><h3>Your Money Plan <span>example</span></h3><div class="pv-plan"><div><b>₹26,400 a month</b><small>Secure retirement target ₹4.62 cr in today's money, two weddings funded first</small></div>{ring}</div></div>
 </div></div></div></section>

<section><div class="wrap">
 <div class="eyebrow">What you get</div><h2 style="margin-top:10px;max-width:22ch">Everything you need to choose well, in one place</h2>
 <div class="pv-bento">
  <a class="pv-tile wide tint" href="/#ratings"><b>Fund ratings: equity, hybrid and debt</b><p>Every fund compared only with its own category, against the right index, every month. A+ to C, with the reasons shown.</p>{_spark([3, 4, 3.6, 5, 4.8, 6, 5.7, 7, 7.6, 7.2, 8.4])}<span class="go">Browse ratings →</span></a>
  <a class="pv-tile" href="/plan/"><b>Money Plan</b><p>How much to invest, and where, for each goal and a secure retirement.</p><span class="go">Build yours →</span></a>
  <a class="pv-tile" href="/#compare"><b>Compare and overlap</b><p>Up to four funds side by side, and how much of the same stocks they hold.</p><span class="go">Compare →</span></a>
  <a class="pv-tile" href="/learn/4-percent-rule-india/"><b>Your freedom number</b><p>The corpus that lasts for life, tested on Indian markets since 2007.</p><span class="go">Read →</span></a>
  <a class="pv-tile" href="/calculators/"><b>Calculators</b><p>SIP, goal, SWP, EMI and capital-gains tax, with real fund returns.</p><span class="go">Open →</span></a>
 </div></div></section>

<section class="pv-band"><div class="wrap">
 <div class="eyebrow">How it works</div><h2 style="margin-top:10px">Three inputs. One clear plan.</h2>
 <div class="pv-steps">
  <div class="pv-step"><i>01</i><b>Tell us your goals</b><p>A wedding next year, a child's education, retirement at 60. Two minutes for a quick plan, six for a detailed one.</p></div>
  <div class="pv-step"><i>02</i><b>See your number</b><p>The monthly amount for each goal, what your existing money already covers, and your plan replayed through 2008 and 2020.</p></div>
  <div class="pv-step"><i>03</i><b>Invest and review</b><p>Funds chosen from the ratings, reviewed every year with you. You can talk to a person whenever you want.</p></div>
 </div>
 <div class="pv-nums"><div><b>{n:,}</b><span>fund plans tracked</span></div><div><b>{rated:,}</b><span>with a track-record rating</span></div><div><b>Monthly</b><span>ratings recalculated</span></div><div><b>₹0</b><span>to build your plan</span></div></div>
</div></section>

<section><div class="wrap"><div class="pv-cta"><div><h2>Start with a conversation</h2><p>A first call is free. We reply within one working day, and we tell you what we earn.</p></div><a class="btn" href="/#contact">Talk to us</a></div>
 <p class="note" style="margin-top:18px">Mutual fund investments are subject to market risks; read all scheme-related documents carefully. Aeterna Wealth Private Limited is an AMFI-registered mutual fund distributor (ARN-317889). Ratings describe past track records and are not forecasts.</p>
</div></section>
</div>"""
    html = B.page("Aeterna Wealth: design preview", "Design preview of the Aeterna Wealth home page.", PATH, body)
    html = html.replace('<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">', '<meta name="robots" content="noindex,nofollow">')
    B.write(PATH, html)   # deliberately not added to urls (sitemap)
