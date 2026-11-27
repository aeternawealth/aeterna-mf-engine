"""Every internal link on the built site: does it land on a real page, directly?

    python tools/link_audit.py [site/dist]

Reports: links to pages that do not exist (404), links that go through a redirect (should point at the final page),
links into the single-page app's hash views (/#...) where a real page exists, and #anchors that are missing on the
target page. Exit code 1 if any link is broken.
"""
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

DIST = Path(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "site/dist")
APP_VIEWS = {"home", "ratings", "fund", "compare", "method", "insights", "solutions", "tools", "about", "contact", "disclosures"}
REAL_FOR_VIEW = {"about": "/about/", "contact": "/contact/", "disclosures": "/disclosures/", "method": "/method/", "insights": "/insights/"}  # ratings and compare are the interactive app views
_OLD = {
                 "solutions": "/invest/", "ratings": "/mutual-funds/"}


def page_exists(path):
    p = path.split("#")[0].split("?")[0]
    if not p.startswith("/"):
        return True
    f = DIST / p.lstrip("/")
    return (f / "index.html").exists() if p.endswith("/") else f.exists() or (f / "index.html").exists()


def main():
    red = {}
    rf = DIST / "_redirects"
    if rf.exists():
        for ln in rf.read_text().splitlines():
            a = ln.split()
            if len(a) >= 2:
                red[a[0]] = a[1]
    ids = {}
    broken, via, spa, anchors = defaultdict(set), defaultdict(set), defaultdict(set), defaultdict(set)
    pages = list(DIST.rglob("*.html"))
    hrefs = {}
    for f in pages:
        h = f.read_text(encoding="utf-8", errors="ignore")
        rel = "/" + str(f.relative_to(DIST)).replace("index.html", "")
        ids[rel] = set(re.findall(r'\sid=["\']([^"\']+)["\']', h))
        body = re.sub(r"<script\b.*?</script>", "", h, flags=re.S)
        hrefs[rel] = set(re.findall(r'href=["\'](/[^"\'\s]*)["\']', body))
    for src, hs in hrefs.items():
        for u in hs:
            if u.startswith("//"):
                continue
            path, _, frag = u.partition("#")
            path = path.split("?")[0] or "/"
            if path == "/" and frag:
                v = frag.split("-")[0].split("/")[0]
                if v in REAL_FOR_VIEW:
                    spa[u].add(src)
                elif v not in APP_VIEWS:
                    spa[u].add(src)
                continue
            if path in red or path.rstrip("/") in red:
                via[f"{u} -> {red.get(path) or red.get(path.rstrip('/'))}"].add(src)
                continue
            if not page_exists(path):
                broken[u].add(src)
                continue
            if frag and path.endswith("/") and path in ids and frag not in ids[path] and not frag.startswith(("tools", ":~")):
                anchors[u].add(src)
    def show(title, d, n=40):
        print(f"\n== {title}: {len(d)} distinct links")
        for u, s in sorted(d.items(), key=lambda x: -len(x[1]))[:n]:
            print(f"  {u}  ({len(s)} pages, e.g. {sorted(s)[0]})")
    print(f"{len(pages)} pages, {sum(len(v) for v in hrefs.values())} internal links")
    show("BROKEN (no such page)", broken)
    show("Through a redirect", via)
    show("Into the app's hash views where a real page exists, or unknown views", spa)
    show("Missing #anchor on the target page", anchors)
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
