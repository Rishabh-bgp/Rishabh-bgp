"""Build self-hosted GitHub stats and top-language SVGs from the GitHub GraphQL API.

Outputs:
  assets/github-stats.svg
  assets/top-langs.svg

These replace third-party github-readme-stats.vercel.app images so the profile
README cannot show a rate-limit / "Something went wrong" card. Run with
GH_TOKEN or GITHUB_TOKEN set. A GitHub Action refreshes the cards daily.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import urllib.request
from collections import defaultdict
from pathlib import Path

USER = "Rishabh-bgp"
ROOT = Path(__file__).resolve().parent.parent
TOKEN = os.environ.get("GH_TOKEN") or os.environ["GITHUB_TOKEN"]
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
M = "font-family:'Courier New',Consolas,'DejaVu Sans Mono',monospace"
S = "font-weight:900;font-family:Impact,Haettenschweiler,'Arial Black',sans-serif"

QUERY = """
query {
  user(login: "%s") {
    name
    followers { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC) {
      totalCount
      nodes {
        isFork
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalRepositoriesWithContributedCommits
    }
  }
}
""" % USER


def gql(q: str) -> dict:
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        json.dumps({"query": q}).encode(),
        {"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    payload = json.load(urllib.request.urlopen(req))
    if "errors" in payload:
        raise SystemExit(payload["errors"])
    return payload["data"]


def xml(s) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def defs(prefix: str) -> str:
    return (
        f"<defs>\n"
        f'<pattern id="{prefix}scan" width="4" height="4" patternUnits="userSpaceOnUse">'
        f'<rect width="4" height="1.2" fill="#000" opacity=".35"/></pattern>\n'
        f"</defs>"
    )


def frame(w: int, h: int, prefix: str) -> str:
    return (
        f'<rect width="{w}" height="{h}" fill="#0a0a0a"/>'
        f'<polygon points="0,0 18,0 0,18" fill="#ff0033"/>'
        f'<polygon points="{w},0 {w-18},0 {w},18" fill="#00f0ff"/>'
        f'<polygon points="0,{h} 18,{h} 0,{h-18}" fill="#39ff6a"/>'
        f'<polygon points="{w},{h} {w-18},{h} {w},{h-18}" fill="#ff2bd6"/>'
        f'<rect x="1" y="1" width="{w-2}" height="{h-2}" fill="none" stroke="#ff0033" stroke-width="1.5"/>'
        f'<rect width="{w}" height="{h}" fill="url(#{prefix}scan)"/>'
    )


def main() -> None:
    data = gql(QUERY)["user"]
    repos = data["repositories"]["nodes"]
    owned = [r for r in repos if not r["isFork"]]
    stars = sum(r["stargazerCount"] for r in repos)
    public_repos = data["repositories"]["totalCount"]
    original = len(owned)
    forks = public_repos - original
    followers = data["followers"]["totalCount"]
    cc = data["contributionsCollection"]
    commits = cc["totalCommitContributions"]
    issues = cc["totalIssueContributions"]
    prs = cc["totalPullRequestContributions"]
    today = dt.datetime.now(IST).date()
    stamp = today.strftime("%d %b %Y")
    year = today.year

    langs: dict[str, list] = defaultdict(lambda: [0, "#8a8a8a"])
    for r in owned:
        for e in r["languages"]["edges"]:
            langs[e["node"]["name"]][0] += e["size"]
            if e["node"]["color"]:
                langs[e["node"]["name"]][1] = e["node"]["color"]
    lang_total = sum(v[0] for v in langs.values()) or 1
    top = sorted(langs.items(), key=lambda x: -x[1][0])[:6]

    rows = [
        ("PUBLIC REPOS", f"{public_repos}", "#ff0033"),
        ("ORIGINAL REPOS", f"{original}", "#00f0ff"),
        (f"COMMITS ({year})", f"{commits:,}", "#39ff6a"),
        ("TOTAL STARS", f"{stars}", "#ffd400"),
        ("FOLLOWERS", f"{followers}", "#ff2bd6"),
    ]
    row_svg = []
    y0 = 58
    for i, (label, val, col) in enumerate(rows):
        y = y0 + i * 24
        row_svg.append(
            f'<text x="22" y="{y}" style="{M};font-weight:bold" font-size="13" fill="#f2e6cf">{xml(label)}</text>'
            f'<text x="468" y="{y}" text-anchor="end" style="{S}" font-size="20" fill="{col}">{xml(val)}</text>'
            f'<path d="M22 {y+6}H468" stroke="#222" stroke-width="1"/>'
        )

    stats_svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="490" height="195" viewBox="0 0 490 195" '
        f'role="img" aria-label="GitHub stats as of {stamp}: {public_repos} public repositories '
        f'({original} original, {forks} forks), {commits} commits in {year}, {stars} stars, {followers} followers">\n'
        f"{defs('st')}\n{frame(490, 195, 'st')}\n"
        f'<text x="22" y="28" style="{M};font-weight:bold" font-size="13" fill="#39ff6a">'
        f"GITHUB STATS // GRAPHQL · {stamp.upper()} (IST)</text>\n"
        f'<text x="468" y="28" text-anchor="end" style="{M}" font-size="11" fill="#8a8a8a">RA-01 · LIVE</text>\n'
        f'<path d="M22 36H468" stroke="#ff0033" stroke-width="1.5"/>\n'
        f"{''.join(row_svg)}\n"
        f"</svg>\n"
    )
    (ROOT / "assets" / "github-stats.svg").write_text(stats_svg)

    bar_max_w = 250
    lang_svg = []
    y0 = 58
    for i, (name, (size, color)) in enumerate(top):
        pct = 100.0 * size / lang_total
        bw = max(2, round(bar_max_w * size / lang_total))
        y = y0 + i * 21
        lang_svg.append(
            f'<text x="22" y="{y}" style="{M};font-weight:bold" font-size="12" fill="#f2e6cf">{xml(name)}</text>'
            f'<rect x="200" y="{y-11}" width="{bar_max_w}" height="10" fill="#161616" stroke="#222"/>'
            f'<rect x="200" y="{y-11}" width="{bw}" height="10" fill="{color}"/>'
            f'<text x="468" y="{y}" text-anchor="end" style="{M};font-weight:bold" font-size="12" fill="#00f0ff">{pct:.2f}%</text>'
        )

    aria = ", ".join(f"{n} {100 * s[0] / lang_total:.2f}%" for n, s in top)
    langs_svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="490" height="195" viewBox="0 0 490 195" '
        f'role="img" aria-label="Most used languages in owned public repositories as of {stamp}: {xml(aria)}">\n'
        f"{defs('lg')}\n{frame(490, 195, 'lg')}\n"
        f'<text x="22" y="28" style="{M};font-weight:bold" font-size="13" fill="#39ff6a">'
        f"TOP LANGUAGES // OWNED REPOS · {stamp.upper()} (IST)</text>\n"
        f'<text x="468" y="28" text-anchor="end" style="{M}" font-size="11" fill="#8a8a8a">BY BYTES</text>\n'
        f'<path d="M22 36H468" stroke="#ff0033" stroke-width="1.5"/>\n'
        f"{''.join(lang_svg)}\n"
        f"</svg>\n"
    )
    (ROOT / "assets" / "top-langs.svg").write_text(langs_svg)

    print(json.dumps({
        "as_of": stamp,
        "public_repos": public_repos,
        "original": original,
        "forks": forks,
        "commits": commits,
        "stars": stars,
        "followers": followers,
        "issues": issues,
        "prs": prs,
        "languages": [{"name": n, "pct": round(100 * s[0] / lang_total, 2), "bytes": s[0]} for n, s in top],
    }, indent=2))


if __name__ == "__main__":
    main()
