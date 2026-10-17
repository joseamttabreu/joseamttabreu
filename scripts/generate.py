#!/usr/bin/env python3
"""Gera assets/terminal.svg: um terminal animado com dados reais do GitHub."""
import json
import os
import urllib.request
from datetime import datetime, timezone
from xml.sax.saxutils import escape

USER = os.environ.get("GH_USER", "joseamttabreu")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
OUT = os.path.join(os.path.dirname(__file__), "..", "assets", "terminal.svg")

# ---------- dados ----------

def api(url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None)
    req.add_header("Accept", "application/vnd.github+json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_stats():
    user = api(f"https://api.github.com/users/{USER}")
    repos = api(f"https://api.github.com/users/{USER}/repos?per_page=100")
    stars = sum(r["stargazers_count"] for r in repos)

    langs = {}
    for r in repos:
        if r["fork"]:
            continue
        for lang, size in api(r["languages_url"]).items():
            langs[lang] = langs.get(lang, 0) + size
    total = sum(langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:4]
    top_langs = "  ".join(f"{k} {v * 100 / total:.0f}%" for k, v in top) or "—"

    commits = "?"
    if TOKEN:
        q = {"query": f'{{ user(login: "{USER}") {{ contributionsCollection {{ '
                      f'contributionCalendar {{ totalContributions }} }} }} }}'}
        data = api("https://api.github.com/graphql", q)
        commits = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["totalContributions"]

    created = datetime.fromisoformat(user["created_at"].replace("Z", "+00:00"))
    days = (datetime.now(timezone.utc) - created).days
    return {
        "since": created.year,
        "uptime": f"{days // 365} anos, {days % 365} dias",
        "repos": user["public_repos"],
        "stars": stars,
        "followers": user["followers"],
        "contribs": commits,
        "langs": top_langs,
        "updated": datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC"),
    }

# ---------- render ----------

C = {
    "bg": "#0d1117", "bar": "#161b22", "fg": "#c9d1d9", "dim": "#6e7681",
    "green": "#3fb950", "cyan": "#39c5cf", "purple": "#bc8cff",
    "yellow": "#d29922", "red": "#f85149", "blue": "#58a6ff",
}

# pixel art "JA" desenhada com <rect>, independente da fonte
ART = [
    "...####...###..",
    "....##...##.##.",
    "....##..##...##",
    "....##..##...##",
    "....##..#######",
    "##..##..##...##",
    "##..##..##...##",
    ".####...##...##",
]
PX = 11

W, LH, X0, Y0 = 860, 22, 24, 64
CHAR_W = 8.4  # largura aproximada do monospace a 14px
TYPE_SPEED = 0.06


def build(s):
    els, y, t = [], Y0, 0.6

    def show(parts, at, x=X0, yy=None):
        """Linha de output: aparece de uma vez no tempo `at`."""
        spans = "".join(f'<tspan fill="{C[c]}">{escape(txt)}</tspan>' for c, txt in parts)
        els.append(f'<text x="{x}" y="{yy or y}" opacity="0">{spans}'
                   f'<set attributeName="opacity" to="1" begin="{at:.2f}s" fill="freeze"/></text>')

    def cmd(text):
        """Prompt + comando digitado caractere a caractere."""
        nonlocal y, t
        prompt = [("green", "jose"), ("dim", "@"), ("cyan", "github"), ("dim", ":"),
                  ("blue", "~"), ("fg", "$ ")]
        show(prompt, t)
        px = X0 + CHAR_W * sum(len(p[1]) for p in prompt)
        cid = f"c{len(els)}"
        n = len(text)
        widths = ";".join(f"{i * CHAR_W:.1f}" for i in range(n)) + f";{W}"
        dur = max(n * TYPE_SPEED, 0.1)
        els.append(
            f'<clipPath id="{cid}"><rect x="{px}" y="{y - 16}" height="{LH}" width="0">'
            f'<animate attributeName="width" values="{widths}" calcMode="discrete" '
            f'begin="{t + 0.3:.2f}s" dur="{dur:.2f}s" fill="freeze"/></rect></clipPath>'
            f'<text x="{px}" y="{y}" fill="{C["fg"]}" clip-path="url(#{cid})">{escape(text)}</text>')
        t += 0.3 + dur + 0.35
        y += LH

    def out(parts, gap=0.04):
        nonlocal y, t
        show(parts, t)
        t += gap
        y += LH

    cmd("whoami")
    out([("fg", "José · "), ("purple", "TI"), ("dim", " / "), ("yellow", "Infra & DevOps"),
         ("dim", " / "), ("blue", "JavaScript · TypeScript")])
    y += 6

    cmd("neofetch")
    info = [
        [("green", "jose"), ("fg", "@"), ("green", "github")],
        [("dim", "─" * 20)],
        [("cyan", "OS       "), ("fg", f"GitHub (desde {s['since']})")],
        [("cyan", "Uptime   "), ("fg", s["uptime"])],
        [("cyan", "Shell    "), ("fg", "bash · zsh · powershell")],
        [("cyan", "Stack    "), ("fg", "TypeScript · Node · React")],
        [("cyan", "Infra    "), ("fg", "Linux · Docker · K8s · Nginx · CI/CD")],
        [("cyan", "Repos    "), ("fg", f"{s['repos']}"), ("dim", "  │  "),
         ("cyan", "Stars "), ("fg", f"{s['stars']}"), ("dim", "  │  "),
         ("cyan", "Followers "), ("fg", f"{s['followers']}")],
        [("cyan", "Contribs "), ("fg", f"{s['contribs']} nos últimos 12 meses")],
        [("cyan", "Langs    "), ("fg", s["langs"])],
    ]
    info_x = X0 + 200
    art_y, art_t = y - 4, t
    for r, line in enumerate(ART):
        for c, ch in enumerate(line):
            if ch == "#":
                at = art_t + (r + c) * 0.03
                els.append(f'<rect x="{X0 + 4 + c * PX}" y="{art_y + r * PX}" width="{PX - 1}" '
                           f'height="{PX - 1}" rx="2" fill="url(#g)" opacity="0">'
                           f'<set attributeName="opacity" to="1" begin="{at:.2f}s" fill="freeze"/></rect>')
    for row in info:
        show(row, t, x=info_x)
        t += 0.07
        y += LH
    # paleta de cores estilo neofetch
    for i, k in enumerate(["red", "yellow", "green", "cyan", "blue", "purple", "fg"]):
        els.append(f'<rect x="{info_x + i * 26}" y="{y - 13}" width="22" height="14" rx="2" '
                   f'fill="{C[k]}" opacity="0"><set attributeName="opacity" to="1" '
                   f'begin="{t:.2f}s" fill="freeze"/></rect>')
    t += 0.3
    y += LH + 6

    cmd("cat ./now.txt")
    out([("yellow", "→ "), ("fg", "automatizando tudo que dá pra automatizar")])
    out([("yellow", "→ "), ("fg", "infra como código, pipelines e muito terminal")])
    y += 6

    # prompt final com cursor piscando
    show([("green", "jose"), ("dim", "@"), ("cyan", "github"), ("dim", ":"),
          ("blue", "~"), ("fg", "$ ")], t)
    cx = X0 + CHAR_W * 15 + 2
    els.append(f'<rect x="{cx}" y="{y - 14}" width="9" height="17" fill="{C["green"]}" opacity="0">'
               f'<animate attributeName="opacity" values="1;1;0;0" dur="1s" begin="{t:.2f}s" '
               f'repeatCount="indefinite"/></rect>')
    y += LH

    H = y + 10
    head = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
        f'<style>text{{font-family:"JetBrains Mono","Fira Code",Consolas,"DejaVu Sans Mono",monospace;'
        f'font-size:14px;white-space:pre}}</style>'
        f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">'
        f'<stop offset="0" stop-color="{C["purple"]}"/><stop offset="1" stop-color="{C["cyan"]}"/>'
        f'</linearGradient></defs>'
        f'<rect width="{W}" height="{H}" rx="10" fill="{C["bg"]}" stroke="#30363d"/>'
        f'<path d="M0 10a10 10 0 0 1 10-10h{W - 20}a10 10 0 0 1 10 10v26H0z" fill="{C["bar"]}"/>'
        f'<circle cx="20" cy="18" r="6" fill="#ff5f57"/><circle cx="40" cy="18" r="6" fill="#febc2e"/>'
        f'<circle cx="60" cy="18" r="6" fill="#28c840"/>'
        f'<text x="{W / 2}" y="23" fill="{C["dim"]}" text-anchor="middle" '
        f'style="font-size:12px">jose@github: ~ — bash</text>'
        f'<text x="{W - 16}" y="{H - 10}" fill="#30363d" text-anchor="end" '
        f'style="font-size:10px">atualizado {s["updated"]}</text>'
    )
    return head + "".join(els) + "</svg>"


if __name__ == "__main__":
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(build(fetch_stats()))
    print("ok ->", os.path.abspath(OUT))
