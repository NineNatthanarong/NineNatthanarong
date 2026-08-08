#!/usr/bin/env python3
"""Render the animated SVG panels used by the profile README.

Data comes from the GitHub GraphQL API when GITHUB_TOKEN is set; otherwise the
last committed snapshot in assets/data.json is reused so the panels still build.
"""

from __future__ import annotations

import json
import os
import pathlib
import urllib.error
import urllib.request

USER = "NineNatthanarong"
ROOT = pathlib.Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
SNAPSHOT = ASSETS / "data.json"

INK = "#08070A"
PANEL = "#100A0D"
RED = "#FF2E4C"
RED_SOFT = "#FF6B7F"
RED_DEEP = "#7A0C1F"
WHITE = "#F5F5F7"
GRAY = "#86868B"
LINE = "#241419"

SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Inter,Helvetica,Arial,sans-serif"
MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,monospace"

MONTH_LABELS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
                "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
      }
      totalCommitContributions
      totalPullRequestContributions
      totalRepositoryContributions
      commitContributionsByRepository(maxRepositories: 25) {
        repository { name primaryLanguage { name } }
        contributions { totalCount }
      }
    }
  }
}
"""


def fetch() -> dict | None:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        return None
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except (urllib.error.URLError, TimeoutError):
        return None
    return payload.get("data", {}).get("user")


def summarize(user: dict) -> dict:
    collection = user["contributionsCollection"]
    calendar = collection["contributionCalendar"]
    days = [day for week in calendar["weeks"] for day in week["contributionDays"]]

    monthly: dict[str, int] = {}
    for day in days:
        monthly[day["date"][:7]] = monthly.get(day["date"][:7], 0) + day["contributionCount"]

    streak = best = 0
    for day in days:
        streak = streak + 1 if day["contributionCount"] else 0
        best = max(best, streak)

    languages: dict[str, int] = {}
    repositories = []
    for entry in collection["commitContributionsByRepository"]:
        commits = entry["contributions"]["totalCount"]
        language = (entry["repository"]["primaryLanguage"] or {}).get("name") or "Other"
        languages[language] = languages.get(language, 0) + commits
        repositories.append({"name": entry["repository"]["name"], "commits": commits})

    repositories.sort(key=lambda item: -item["commits"])

    return {
        "total": calendar["totalContributions"],
        "commits": collection["totalCommitContributions"],
        "pull_requests": collection["totalPullRequestContributions"],
        "repositories_started": collection["totalRepositoryContributions"],
        "monthly": [{"month": key, "value": value} for key, value in sorted(monthly.items())][-13:],
        "active_days": sum(1 for day in days if day["contributionCount"]),
        "peak_day": max(day["contributionCount"] for day in days),
        "longest_streak": best,
        "languages": sorted(languages.items(), key=lambda item: -item[1]),
        "repositories": repositories[:6],
    }


def load_data() -> dict:
    user = fetch()
    if user:
        data = summarize(user)
        SNAPSHOT.write_text(json.dumps(data, indent=2) + "\n")
        return data
    return json.loads(SNAPSHOT.read_text())


def defs(extra_css: str = "") -> str:
    return f"""  <defs>
    <linearGradient id="bar" x1="0" y1="1" x2="0" y2="0">
      <stop offset="0%" stop-color="{RED_DEEP}"/>
      <stop offset="100%" stop-color="{RED}"/>
    </linearGradient>
    <linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{RED}" stop-opacity="0"/>
      <stop offset="50%" stop-color="{RED}" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="{RED}" stop-opacity="0"/>
    </linearGradient>
    <radialGradient id="halo" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="{RED}" stop-opacity="0.30"/>
      <stop offset="100%" stop-color="{RED}" stop-opacity="0"/>
    </radialGradient>
    <filter id="glow" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur stdDeviation="5" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <filter id="soft" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur stdDeviation="2.2" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <style>
    .sans {{ font-family: {SANS}; }}
    .mono {{ font-family: {MONO}; }}
    .fade {{ opacity: 0; animation: fade .8s ease forwards; }}
    @keyframes fade {{ to {{ opacity: 1; }} }}
    @keyframes pulse {{ 0%,100% {{ opacity: .35; }} 50% {{ opacity: 1; }} }}
    @keyframes drift {{ from {{ transform: translateX(-320px); }} to {{ transform: translateX(1220px); }} }}
{extra_css}
  </style>
"""


def write(name: str, markup: str) -> None:
    ASSETS.mkdir(exist_ok=True)
    (ASSETS / name).write_text(markup)
    print(f"wrote assets/{name}")


def hero() -> str:
    grid = []
    for x in range(0, 1000, 40):
        grid.append(f'<line x1="{x}" y1="0" x2="{x}" y2="260" stroke="{LINE}" stroke-width="1"/>')
    for y in range(0, 260, 40):
        grid.append(f'<line x1="0" y1="{y}" x2="1000" y2="{y}" stroke="{LINE}" stroke-width="1"/>')

    css = """    .sweep { animation: drift 5.5s linear infinite; }
    .dot { animation: pulse 1.8s ease-in-out infinite; }
    .rule { stroke-dasharray: 620; stroke-dashoffset: 620; animation: draw 1.4s .3s ease forwards; }
    @keyframes draw { to { stroke-dashoffset: 0; } }
    .l1 { animation-delay: .1s; } .l2 { animation-delay: .35s; } .l3 { animation-delay: .6s; }"""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 260" width="1000" height="260" role="img" aria-label="Natthanarong Tiangjit — AI Software Developer">
{defs(css)}
  <rect width="1000" height="260" fill="{INK}"/>
  <g opacity="0.55">{''.join(grid)}</g>
  <ellipse cx="500" cy="150" rx="440" ry="180" fill="url(#halo)"/>
  <rect class="sweep" x="-320" y="0" width="320" height="260" fill="url(#sweep)"/>

  <g class="fade l1">
    <circle class="dot" cx="60" cy="66" r="4" fill="{RED}" filter="url(#soft)"/>
    <text x="76" y="71" class="mono" font-size="13" letter-spacing="3.5" fill="{RED}">BANGKOK · BUILDING NOW</text>
  </g>

  <text x="58" y="139" class="sans fade l2" font-size="46" font-weight="700" letter-spacing="-1" fill="{WHITE}">Natthanarong Tiangjit</text>
  <text x="58" y="176" class="sans fade l3" font-size="21" fill="{GRAY}">AI systems, full-stack products, and machines that move.</text>

  <line class="rule" x1="58" y1="204" x2="678" y2="204" stroke="{RED}" stroke-width="2" filter="url(#soft)"/>

  <g class="mono fade l3" font-size="12" letter-spacing="2.5" fill="{GRAY}">
    <text x="58" y="228">AI ENGINEERING</text>
    <text x="228" y="228">·</text>
    <text x="252" y="228">FULL-STACK</text>
    <text x="378" y="228">·</text>
    <text x="402" y="228">ROBOTICS</text>
  </g>

  <g class="fade l3">
    <path d="M942 34 h24 v24" fill="none" stroke="{RED}" stroke-width="2"/>
    <path d="M942 226 h24 v-24" fill="none" stroke="{RED}" stroke-width="2"/>
  </g>
</svg>
"""


def pulse(data: dict) -> str:
    months = data["monthly"]
    peak = max(item["value"] for item in months) or 1
    base_y, top_y = 252.0, 116.0
    span = base_y - top_y
    left, right = 60.0, 950.0
    slot = (right - left) / len(months)
    width = min(46.0, slot - 14)

    bars, labels, css = [], [], []
    for index, item in enumerate(months):
        height = max(3.0, item["value"] / peak * span)
        x = left + index * slot + (slot - width) / 2
        y = base_y - height
        delay = 0.08 * index
        is_peak = item["value"] == peak
        fill = RED if is_peak else "url(#bar)"
        peak_filter = ' filter="url(#soft)"' if is_peak else ""
        css.append(
            f"    .b{index} {{ transform-origin: {x + width / 2:.1f}px {base_y}px; "
            f"animation: grow .9s cubic-bezier(.2,.8,.2,1) {delay:.2f}s both; }}"
        )
        bars.append(
            f'<rect class="b{index}" x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" '
            f'rx="6" fill="{fill}"{peak_filter}/>'
        )
        if is_peak:
            labels.append(
                f'<text x="{x + width / 2:.1f}" y="{y - 14:.1f}" class="mono fade" font-size="13" '
                f'font-weight="700" text-anchor="middle" fill="{RED}" style="animation-delay:1.1s">{item["value"]}</text>'
            )
        month = MONTH_LABELS[int(item["month"][5:7]) - 1]
        labels.append(
            f'<text x="{x + width / 2:.1f}" y="{base_y + 22:.1f}" class="mono" font-size="10.5" '
            f'letter-spacing="1" text-anchor="middle" fill="{GRAY}">{month}</text>'
        )

    chips = [
        (f'{data["active_days"]}', "ACTIVE DAYS"),
        (f'{data["longest_streak"]}', "DAY STREAK"),
        (f'{data["peak_day"]}', "BEST DAY"),
        (f'{data["pull_requests"]}', "PULL REQUESTS"),
    ]
    chip_markup = []
    for index, (value, label) in enumerate(chips):
        x = 60 + index * 232
        chip_markup.append(
            f'<g class="fade" style="animation-delay:{1.2 + index * 0.1:.1f}s">'
            f'<rect x="{x}" y="294" width="212" height="62" rx="12" fill="{PANEL}" stroke="{LINE}"/>'
            f'<text x="{x + 20}" y="326" class="sans" font-size="24" font-weight="700" fill="{RED}">{value}</text>'
            f'<text x="{x + 20}" y="344" class="mono" font-size="10" letter-spacing="1.8" fill="{GRAY}">{label}</text>'
            f'</g>'
        )

    grid_lines = "".join(
        f'<line x1="60" y1="{base_y - span * fraction:.1f}" x2="950" y2="{base_y - span * fraction:.1f}" '
        f'stroke="{LINE}" stroke-width="1"/>'
        for fraction in (0.25, 0.5, 0.75, 1.0)
    )

    extra = "    @keyframes grow { from { transform: scaleY(0); } to { transform: scaleY(1); } }\n" + "\n".join(css)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 372" width="1000" height="372" role="img" aria-label="{data['total']} contributions in the last year">
{defs(extra)}
  <rect width="1000" height="372" rx="16" fill="{INK}"/>
  <ellipse cx="500" cy="240" rx="480" ry="150" fill="url(#halo)" opacity="0.55"/>

  <text x="60" y="52" class="sans" font-size="24" font-weight="700" fill="{WHITE}">A year of building.</text>
  <text x="60" y="76" class="sans" font-size="14" fill="{GRAY}">Contributions, month by month.</text>
  <text x="950" y="60" class="sans" font-size="42" font-weight="700" text-anchor="end" fill="{RED}" filter="url(#soft)">{data['total']}</text>
  <text x="950" y="80" class="mono" font-size="10.5" letter-spacing="2" text-anchor="end" fill="{GRAY}">CONTRIBUTIONS · 12 MONTHS</text>

  {grid_lines}
  <line x1="60" y1="{base_y}" x2="950" y2="{base_y}" stroke="{RED_DEEP}" stroke-width="1.5"/>
  {''.join(bars)}
  {''.join(labels)}
  {''.join(chip_markup)}
</svg>
"""


def split(data: dict) -> str:
    total = sum(count for _, count in data["languages"]) or 1
    named = [(name, count) for name, count in data["languages"] if name != "Other"]
    languages = named[:4]
    remainder = total - sum(count for _, count in languages)
    if remainder > 0:
        languages = languages + [("Other", remainder)]

    shades = [RED, "#D81E3C", "#A5142C", "#6E0F1E", "#3D0A12"]
    radius, cx, cy, thickness = 78.0, 172.0, 178.0, 26.0
    circumference = 2 * 3.14159265 * radius

    ring, legend, css = [], [], []
    offset = 0.0
    for index, (name, count) in enumerate(languages):
        fraction = count / total
        length = circumference * fraction
        ring.append(
            f'<circle class="seg s{index}" cx="{cx}" cy="{cy}" r="{radius}" fill="none" '
            f'stroke="{shades[index]}" stroke-width="{thickness}" stroke-linecap="butt" '
            f'stroke-dasharray="{length - 3:.2f} {circumference - length + 3:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 {cx} {cy})"/>'
        )
        css.append(
            f"    .s{index} {{ animation: reveal 1s cubic-bezier(.2,.8,.2,1) {0.15 * index:.2f}s both; }}"
        )
        y = 116 + index * 34
        legend.append(
            f'<g class="fade" style="animation-delay:{0.5 + index * 0.1:.1f}s">'
            f'<rect x="300" y="{y - 11}" width="10" height="10" rx="2" fill="{shades[index]}"/>'
            f'<text x="322" y="{y - 1}" class="sans" font-size="14" fill="{WHITE}">{name}</text>'
            f'<text x="472" y="{y - 1}" class="mono" font-size="12" text-anchor="end" fill="{GRAY}">{fraction * 100:.0f}%</text>'
            f'</g>'
        )
        offset += length

    repositories = data["repositories"][:5]
    busiest = max(item["commits"] for item in repositories) or 1
    bars = []
    for index, item in enumerate(repositories):
        y = 108 + index * 42
        width = item["commits"] / busiest * 300
        bars.append(
            f'<text x="560" y="{y - 4}" class="mono" font-size="12" fill="{GRAY}">{item["name"][:22]}</text>'
            f'<rect x="560" y="{y + 4}" width="300" height="8" rx="4" fill="{PANEL}"/>'
            f'<rect class="rb r{index}" x="560" y="{y + 4}" width="{width:.1f}" height="8" rx="4" fill="url(#bar)"/>'
            f'<text x="940" y="{y + 12}" class="mono" font-size="12" text-anchor="end" fill="{RED}">{item["commits"]}</text>'
        )
        css.append(
            f"    .r{index} {{ transform-origin: 560px 0px; animation: stretch .9s cubic-bezier(.2,.8,.2,1) {0.2 + index * 0.09:.2f}s both; }}"
        )

    extra = (
        "    @keyframes reveal { from { stroke-dasharray: 0 " f"{circumference:.0f}" "; } }\n"
        "    @keyframes stretch { from { transform: scaleX(0); } to { transform: scaleX(1); } }\n"
        + "\n".join(css)
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 330" width="1000" height="330" role="img" aria-label="Where the commits go">
{defs(extra)}
  <rect width="1000" height="330" rx="16" fill="{INK}"/>
  <ellipse cx="200" cy="180" rx="260" ry="160" fill="url(#halo)" opacity="0.5"/>

  <text x="60" y="52" class="sans" font-size="24" font-weight="700" fill="{WHITE}">Where the work goes.</text>
  <text x="60" y="76" class="sans" font-size="14" fill="{GRAY}">Commits by language, and the repos they land in.</text>

  {''.join(ring)}
  <text x="{cx}" y="{cy + 2}" class="sans" font-size="34" font-weight="700" text-anchor="middle" fill="{WHITE}">{data['commits']}</text>
  <text x="{cx}" y="{cy + 24}" class="mono" font-size="10" letter-spacing="2" text-anchor="middle" fill="{GRAY}">COMMITS</text>
  {''.join(legend)}

  <line x1="516" y1="96" x2="516" y2="300" stroke="{LINE}" stroke-width="1"/>
  <text x="560" y="80" class="mono" font-size="10.5" letter-spacing="2" fill="{RED}">MOST ACTIVE REPOSITORIES</text>
  {''.join(bars)}
</svg>
"""


def main() -> None:
    data = load_data()
    write("hero.svg", hero())
    write("pulse.svg", pulse(data))
    write("split.svg", split(data))


if __name__ == "__main__":
    main()
