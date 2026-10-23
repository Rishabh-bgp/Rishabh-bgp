"""Build assets/contrib-card.svg from the GitHub GraphQL API (public contribution calendar).

Run with GH_TOKEN (or GITHUB_TOKEN) set. Totals = sum of the contribution calendar for every contribution year,
which is the same number GitHub shows on the profile graph.
"""
import datetime as dt
import json
import os
import urllib.request
from pathlib import Path

USER = "Rishabh-bgp"
OUT = Path(__file__).resolve().parent.parent / "assets" / "contrib-card.svg"
TOKEN = os.environ.get("GH_TOKEN") or os.environ["GITHUB_TOKEN"]


def gql(q):
    req = urllib.request.Request("https://api.github.com/graphql", json.dumps({"query": q}).encode(),
                                 {"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))["data"]


years = gql(f'{{user(login:"{USER}"){{contributionsCollection{{contributionYears}}}}}}')["user"]["contributionsCollection"]["contributionYears"]
days = {}
for y in sorted(years):
    q = (f'{{user(login:"{USER}"){{contributionsCollection(from:"{y}-01-01T00:00:00Z",to:"{y}-12-31T23:59:59Z")'
         '{contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}')
    for w in gql(q)["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]:
        for d in w["contributionDays"]:
            days[d["date"]] = d["contributionCount"]
today = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).date()
dates = sorted(d for d in days if dt.date.fromisoformat(d) <= today)
total = sum(days[d] for d in dates)
this_year = sum(days[d] for d in dates if d.startswith(str(today.year)))
longest = cur = run = 0
for d in dates:
    run = run + 1 if days[d] else 0
    longest = max(longest, run)
i = len(dates) - 1
if i >= 0 and days[dates[i]] == 0:  # today may not have a contribution yet
    i -= 1
while i >= 0 and days[dates[i]]:
    cur += 1
    i -= 1
active = sum(1 for d in dates if days[d])
stamp = today.strftime("%d %b %Y")
M = "font-family:'Courier New',Consolas,'DejaVu Sans Mono',monospace"
S = "font-weight:900;font-family:Impact,Haettenschweiler,'Arial Black',sans-serif"


def panel(x, label, val, col):
    return (f'<g transform="translate({x} 40)"><polygon points="0,0 230,0 240,10 240,104 10,104 0,94" fill="#111" stroke="{col}" stroke-width="1.5"/>'
            f'<text x="120" y="58" text-anchor="middle" style="{S}" font-size="44" fill="{col}">{val}</text>'
            f'<text x="120" y="86" text-anchor="middle" style="{M};font-weight:bold" font-size="12" fill="#f2e6cf">{label}</text></g>')


svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="160" viewBox="0 0 1000 160" role="img" aria-label="Contributions as of {stamp}: {total} all-time, {this_year} in {today.year}, current streak {cur} days, longest streak {longest} days">
<defs><pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1.2" fill="#000" opacity=".35"/></pattern></defs>
<rect width="1000" height="160" fill="#0a0a0a"/>
<text x="16" y="26" style="{M};font-weight:bold" font-size="13" fill="#39ff6a">CONTRIBUTION TELEMETRY // GITHUB GRAPHQL · AS OF {stamp.upper()} (IST)</text>
<text x="984" y="26" text-anchor="end" style="{M}" font-size="12" fill="#8a8a8a">{active} ACTIVE DAYS</text>
{panel(4, "TOTAL CONTRIBUTIONS", f"{total:,}", "#ff0033")}{panel(252, f"IN {today.year}", f"{this_year:,}", "#00f0ff")}{panel(500, "CURRENT STREAK (DAYS)", cur, "#39ff6a")}{panel(748, "LONGEST STREAK (DAYS)", longest, "#ff2bd6")}
<rect width="1000" height="160" fill="url(#scan)"/></svg>'''
OUT.write_text(svg)
print(json.dumps({"total": total, "this_year": this_year, "current_streak": cur, "longest_streak": longest, "active_days": active, "as_of": stamp}))
