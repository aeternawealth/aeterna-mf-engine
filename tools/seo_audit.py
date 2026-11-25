"""SEO audit of the built site (site/dist) and, with --live, of the live hosts. Standard library only.

    python tools/seo_audit.py            # built pages only
    python tools/seo_audit.py --live     # plus host, redirect, robots and sitemap checks on aeternawealth.com

FAIL = must fix before publishing; CHECK = look at it; INFO = numbers to track. Writes outputs/latest/seo_audit.md.
Checks: titles and descriptions (missing, too long, duplicated), canonical (missing, not self), robots (noindex pages in
the sitemap, indexable pages missing from it), one H1, valid JSON-LD, broken internal links, orphan pages, thin pages,
page weight; live: www and http redirect to https://aeternawealth.com, preview hosts noindexed, robots.txt allows
crawling, sitemap reachable, key pages 200.
"""
import collections
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "site" / "dist"
SITE = "https://aeternawealth.com"
KEY_PAGES = ["/", "/mutual-funds/", "/mutual-funds/small-cap/", "/mutual-funds/holding/", "/income-tax/calculator/",
             "/income-tax/advance-tax-calculator/", "/calculators/sip/", "/compare/", "/mutual-funds/what-funds-bought-sold/"]
out = []


def say(level, code, msg):
    out.append((level, code, msg))
    print(f"{level:5} {code:3} {msg}")


def crawl():
    sm = set(re.findall(r"<loc>https://aeternawealth\.com([^<]*)</loc>", (D / "sitemap.xml").read_text()))
    pages = {}
    for p in D.rglob("index.html"):
        rel = p.parent.relative_to(D).as_posix()
        pages["/" if rel == "." else f"/{rel}/"] = p.read_text(encoding="utf-8", errors="replace")
    P = collections.defaultdict(list)
    titles, descs, inl, broken = collections.defaultdict(list), collections.defaultdict(list), collections.Counter(), collections.Counter()
    for u, s in pages.items():
        t = re.search(r"<title>(.*?)</title>", s, re.S)
        t = html.unescape(t.group(1).strip()) if t else ""
        d = re.search(r'<meta name="description" content="([^"]*)"', s)
        d = html.unescape(d.group(1)) if d else ""
        c = re.search(r'<link rel="canonical" href="([^"]*)"', s)
        rob = re.search(r'<meta name="robots" content="([^"]*)"', s)
        noidx = bool(rob and "noindex" in rob.group(1))
        body = s[s.find("<body"):]
        if not noidx:
            titles[t].append(u)
            descs[d].append(u)
            if not t:
                P["S1 no title"].append(u)
            if not d:
                P["S2 no meta description"].append(u)
            if not c:
                P["S3 no canonical"].append(u)
            elif c.group(1) != SITE + u:
                P["S4 canonical points elsewhere"].append(f"{u} -> {c.group(1)}")
            if u not in sm:
                P["S5 indexable page missing from the sitemap"].append(u)
            if len(re.findall(r"<h1[\s>]", body)) != 1 and u != "/":
                P["S6 not exactly one H1"].append(u)
            words = len(re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>|<style.*?</style>", "", body, flags=re.S)).split())
            if words < 250:
                P["S7 thin page (<250 words)"].append(u)
            if len(t) > 70:
                P["I1 title over 70 characters (cut off in results)"].append(u)
        elif u in sm:
            P["S8 noindex page in the sitemap"].append(u)
        for m in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
            try:
                json.loads(m.group(1))
            except Exception:
                P["S9 invalid JSON-LD"].append(u)
        if len(s) > 400_000:
            P["S10 page over 400 KB"].append(u)
        for h in set(re.findall(r"""href=["'](/[^"'#?]*)""", s)):
            if h.startswith(("/assets/", "/fonts/", "/data/")) or "." in h.rsplit("/", 1)[-1] or "${" in h:
                continue
            h2 = h if h.endswith("/") else h + "/"
            if h2 in pages:
                inl[h2] += 1
            else:
                broken[h] += 1
    for u in sm - set(pages):
        P["S11 sitemap URL with no page"].append(u)
    orphans = [u for u in pages if u not in ("/", "/links/") and not inl[u] and u in sm]
    say("INFO", "S0", f"{len(pages)} pages built, {len(sm)} in the sitemap")
    fail = {"S1", "S3", "S4", "S8", "S9", "S11"}
    for k, v in sorted(P.items()):
        code = k.split()[0]
        lvl = "FAIL" if code in fail else ("INFO" if code.startswith("I") else "CHECK")
        say(lvl, code, f"{k.split(' ', 1)[1]}: {len(v)}, e.g. {'; '.join(map(str, v[:4]))}")
    dt = {t: v for t, v in titles.items() if len(v) > 1 and t}
    dd = {t: v for t, v in descs.items() if len(v) > 1 and t}
    if dt:
        say("CHECK", "S12", f"{len(dt)} titles used by more than one page, e.g. {list(dt.items())[:2]}")
    if dd:
        say("CHECK", "S13", f"{len(dd)} descriptions used by more than one page, e.g. {[(k[:50], v[:2]) for k, v in list(dd.items())[:2]]}")
    if broken:
        say("FAIL", "S14", f"{len(broken)} broken internal links, e.g. {broken.most_common(5)}")
    if orphans:
        say("CHECK", "S15", f"{len(orphans)} sitemap pages no other page links to, e.g. {orphans[:5]}")


def live():
    def get(url, head=False):
        req = urllib.request.Request(url, method="HEAD" if head else "GET", headers={"User-Agent": "Mozilla/5.0 (compatible; AeternaSEOAudit/1.0)"})

        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k):
                return None
        op = urllib.request.build_opener(NoRedirect)
        try:
            r = op.open(req, timeout=20)
            return r.status, dict(r.headers), (r.read(300_000).decode("utf-8", "replace") if not head else "")
        except urllib.error.HTTPError as e:
            return e.code, dict(e.headers), ""
        except Exception as e:
            return 0, {}, str(e)[:80]
    st, h, _ = get("https://www.aeternawealth.com/")
    if st in (301, 308) and h.get("Location", "").startswith(SITE):
        say("INFO", "L1", "www redirects to aeternawealth.com")
    else:
        say("CHECK", "L1", f"www.aeternawealth.com answers {st} instead of a 301 to {SITE} (a duplicate copy; fix with a Cloudflare redirect rule)")
    for host in ("https://aeterna-wealth.pages.dev/", "https://staging.aeterna-wealth.pages.dev/"):
        st, h, _ = get(host, head=True)
        if st == 200 and "noindex" not in str(h.get("X-Robots-Tag", h.get("x-robots-tag", ""))).lower():
            say("FAIL", "L2", f"{host} is indexable (no X-Robots-Tag: noindex)")
    st, _, robots = get(SITE + "/robots.txt")
    if st != 200 or re.search(r"(?m)^Disallow:\s*/\s*$", robots):
        say("FAIL", "L3", f"robots.txt blocks crawling or is missing ({st})")
    st, _, sm = get(SITE + "/sitemap.xml")
    say("INFO" if st == 200 and "<loc>" in sm else "FAIL", "L4", f"sitemap.xml {st}")
    for u in KEY_PAGES:
        st, h, body = get(SITE + u)
        if st != 200:
            say("FAIL", "L5", f"{u} answers {st}")
        elif 'content="noindex' in body:
            say("FAIL", "L5", f"{u} is noindex on the live site")


if __name__ == "__main__":
    crawl()
    if "--live" in sys.argv:
        live()
    md = ROOT / "outputs" / "latest" / "seo_audit.md"
    md.parent.mkdir(parents=True, exist_ok=True)
    n = collections.Counter(l for l, _, _ in out)
    md.write_text(f"# SEO audit\n\n{n['FAIL']} FAIL, {n['CHECK']} CHECK\n\n" + "\n".join(f"- **{l}** {c}: {m}" for l, c, m in out) + "\n", encoding="utf-8")
    sys.exit(1 if n["FAIL"] else 0)
