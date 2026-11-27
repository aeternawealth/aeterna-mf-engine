"""SEO guard: stops a deploy that removes or breaks the site's trust and AI-search foundations (27 Nov 2026).

    python tools/seo_guard.py      # after python site/build_site.py; exit 1 = do not publish

Runs in .github/workflows/deploy.yml after the build and before the upload, so a change that removes any of these
cannot go live. To change one on purpose, change this guard in the same commit and explain why in the commit message
and docs/seo/log.md (AGENTS.md, "SEO and AI search"). Standard library only.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "site" / "dist"
fails = []


def fail(code, msg):
    fails.append(f"FAIL {code} {msg}")


def read(rel):
    p = D / rel
    return p.read_text(encoding="utf-8") if p.exists() else ""


def main():
    if not (D / "index.html").exists():
        print("FAIL G0 site/dist not built: run python site/build_site.py first")
        return 1
    launched = (ROOT / "site" / "LAUNCHED").exists()

    # G1 the editorial and corrections policy: published, indexable, in the sitemap, linked from every footer
    ed = read("editorial-policy/index.html")
    if not ed:
        fail("G1", "/editorial-policy/ is missing")
    elif launched and 'content="noindex' in ed:
        fail("G1", "/editorial-policy/ is noindex")
    if "/editorial-policy/</loc>" not in read("sitemap.xml"):
        fail("G1", "/editorial-policy/ is not in sitemap.xml")

    # G2 the trust box on every data and tax page, and the footer link to the policy
    missing, nolink, n = [], [], 0
    for pre in ("mutual-funds", "compare", "insights", "income-tax"):
        for f in (D / pre).rglob("index.html"):
            s = f.read_text(encoding="utf-8")
            if "http-equiv=\"refresh\"" in s:
                continue
            n += 1
            if "Who makes these ratings" not in s and "Who publishes this" not in s:
                missing.append("/" + str(f.parent.relative_to(D)) + "/")
            if 'href="/editorial-policy/"' not in s:
                nolink.append("/" + str(f.parent.relative_to(D)) + "/")
    if missing:
        fail("G2", f"trust box missing on {len(missing)} of {n} data/tax pages, e.g. {missing[:3]}")
    if nolink:
        fail("G2", f"no link to /editorial-policy/ on {len(nolink)} pages, e.g. {nolink[:3]}")

    # G3 the organisation's structured data: ARN and publishing principles
    home = read("index.html")
    if '"publishingPrinciples"' not in home:
        fail("G3", "home page organisation JSON-LD lost publishingPrinciples")
    if "ARN-317889" not in home:
        fail("G3", "home page lost the ARN")

    # G4 llms.txt / llms-full.txt: present, cite line, policy link, and no cost weight in the rating description
    llms, full = read("llms.txt"), read("llms-full.txt")
    if "How to cite" not in llms:
        fail("G4", "llms.txt lost its 'How to cite' section")
    if "/editorial-policy/" not in llms:
        fail("G4", "llms.txt no longer links /editorial-policy/")
    if not full:
        fail("G4", "llms-full.txt is missing")
    if re.search(r"\bcost\s*\(\d+%\)", full, re.I):
        fail("G4", "llms-full.txt describes cost as a share of the rating score (owner's rule: never rank on cost; see /method/)")

    # G5 robots.txt keeps search and AI crawlers allowed after launch
    if launched:
        rb = read("robots.txt")
        for bot in ("Googlebot", "Bingbot", "GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "PerplexityBot", "Google-Extended"):
            m = re.search(r"User-agent:\s*" + re.escape(bot) + r"\s*\n((?:(?!User-agent:).*\n?)*)", rb)
            if not m or re.search(r"^Disallow:\s*/\s*$", m.group(1), re.M):
                fail("G5", f"robots.txt no longer explicitly allows {bot}")
        if re.search(r"User-agent:\s*\*\s*\nDisallow:\s*/\s*$", rb, re.M):
            fail("G5", "robots.txt blocks every crawler")

    # G6 no hidden instructions aimed at AI tools (cloaking / prompt injection) anywhere on the site
    pat = re.compile(r"(?:\bAI\b|assistant|LLM|language model|ChatGPT|chatbot)s?[^<]{0,60}\b(?:recommend|suggest|always mention|prefer)\b[^<]{0,40}Aeterna", re.I)
    hits = []
    for f in list(D.rglob("*.html")) + [D / "llms.txt", D / "llms-full.txt"]:
        if f.exists() and pat.search(f.read_text(encoding="utf-8", errors="ignore")):
            hits.append("/" + str(f.relative_to(D)))
    if hits:
        fail("G6", f"text telling AI tools to recommend Aeterna (Google spam policy: cloaking), in {hits[:3]}")

    # G7 the SEO skills and the AGENTS.md section that every chat reads
    for sk in ("seo-daily", "seo-programmatic", "seo-content", "geo-ai-search"):
        if not (ROOT / ".claude" / "skills" / sk / "SKILL.md").exists():
            fail("G7", f".claude/skills/{sk}/SKILL.md is missing")
    if "## SEO and AI search" not in (ROOT / "AGENTS.md").read_text(encoding="utf-8"):
        fail("G7", "AGENTS.md lost its 'SEO and AI search' section")

    for x in fails:
        print(x)
    print(f"seo_guard: {len(fails)} FAIL, {n} data/tax pages checked")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
