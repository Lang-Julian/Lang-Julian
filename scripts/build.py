#!/usr/bin/env python3
"""Render every SVG in assets/ from the data below. Stdlib only.

    python3 scripts/build.py

Each image is written twice, -dark.svg and -light.svg; README.md picks one
per viewer theme with <picture>. Animations play once on load and freeze on
the final frame. A renderer that ignores animation shows that final frame.
"""
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parent.parent / "assets"

MONO = "ui-monospace,SFMono-Regular,'SF Mono',Menlo,Monaco,Consolas,'Liberation Mono','DejaVu Sans Mono',monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"

THEMES = {
    "dark": dict(
        bg="#0b0d12", chrome="#12151c", panel="#0f1218", border="#262b38",
        text="#e6e9ef", muted="#8d95a8", faint="#4b5367",
        accent="#ffb547", accent2="#ff7a45", ok="#7ee787",
        dots=("#ff5f57", "#febc2e", "#28c840"),
        blocks=("#1a1d25", "#ff5f57", "#7ee787", "#febc2e",
                "#58a6ff", "#d2a8ff", "#56d4dd", "#e6e9ef"),
    ),
    "light": dict(
        bg="#fbfaf7", chrome="#f0eee8", panel="#ffffff", border="#dcd8ce",
        text="#1b1e25", muted="#5b6372", faint="#a8adb8",
        accent="#b45309", accent2="#c2410c", ok="#1a7f37",
        dots=("#ff5f57", "#febc2e", "#28c840"),
        blocks=("#1b1e25", "#cf222e", "#1a7f37", "#9a6700",
                "#0969da", "#8250df", "#1b7c83", "#d0d7de"),
    ),
}

# Linguist colours, so the dots match the ones GitHub shows on each repo.
LANG = {"C": "#555555", "TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Shell": "#89e051"}

MONOGRAM = [
    "     ██╗ █████╗ ██╗     ",
    "     ██║██╔══██╗██║     ",
    "     ██║███████║██║     ",
    "██   ██║██╔══██║██║     ",
    "╚█████╔╝██║  ██║███████╗",
    " ╚════╝ ╚═╝  ╚═╝╚══════╝",
]

# Every value here is checked against a source; see README "Where the facts come from".
FETCH = [
    ("name", "Julian Antony Lang"),
    ("role", "CTO · AI-Z Group"),
    ("invented", "Brane AIF — the AI Interaction Firewall"),
    ("base", "Stuttgart, DE"),
    ("stack", "TypeScript · Python · Rust · Swift · C"),
    ("likes", "on-device AI · NEON asm · terminals"),
    ("host", "Apple M5 · macOS 26 · zsh + ct"),
]

CARDS = [
    dict(repo="pidigit", glyph="π", tag="C · ARM64 NEON asm", lang="C",
         desc=["One hex digit of π from two billion places in —",
               "in 8 seconds and 2 MB, without the digits before it."],
         art=[("pos 536870909 → ", "muted"), ("b0f6c61365a861eb", "accent")],
         foot="MIT · 55.7× naive on 10 cores"),
    dict(repo="glyphfall", glyph="◆", tag="TypeScript", lang="TypeScript",
         desc=["A roguelike deckbuilder that lives in your terminal —",
               "about the order you do things in."],
         art=[("◆ EMBER  ", "#e8590c"), ("▲ FROST  ", "#1c7ed6"), ("● VOID  ", "#7950f2"),
              ("■ IRON  ", "muted"), ("◉ PRISM", "#d4a106")],
         foot="MIT · zero runtime deps · Node ≥ 20"),
    dict(repo="claude-tower", glyph="◎", tag="JavaScript", lang="JavaScript",
         desc=["Air-traffic control for your Claude Code swarm:",
               "every session, remote approvals, cost — on localhost."],
         art=[("s1 ", "muted"), ("● thinking   ", "ok"), ("s2 ", "muted"),
              ("◐ approve?   ", "accent"), ("s3 ", "muted"), ("○ done", "faint")],
         foot="MIT · alpha · talks to nothing online"),
    dict(repo="facettn", glyph="◇", tag="TypeScript · Next.js", lang="TypeScript",
         desc=["A personality test that stores nothing — scored in",
               "your browser, the result lives in the URL fragment."],
         art=[("cookies ", "muted"), ("0", "accent"), ("  ·  trackers ", "muted"), ("0", "accent"),
              ("  ·  database ", "muted"), ("0", "accent")],
         foot="MIT · German · open questions & weights"),
    dict(repo="ct", glyph="▍", tag="zsh · iTerm2 · WezTerm", lang="Shell",
         desc=["Tag terminals, not tabs — a persistent visual",
               "watermark so you know which terminal is which."],
         art=[("[ ", "faint"), ("deploy", "accent"), (" ]  ", "faint"), ("[ api ]  [ docs ]  [ bench ]", "faint")],
         foot="MIT · cw <tag> jumps back"),
    dict(repo="price-globe", glyph="◍", tag="Next.js 16 · React 19", lang="TypeScript",
         desc=["Cost of living across 6 countries — seasonal price",
               "patterns, a daily-budget calculator, travel insights."],
         art=[("hotels TH  ", "muted"), ("▇▆▅▃▂▁▁▂▃▅▆▇", "accent"), ("  jan → dec", "faint")],
         foot="MIT · 6 countries · 20 products"),
]


def esc(s):
    return escape(s, {'"': "&quot;"})


def style(t, extra=""):
    return f"""<style>
  .m {{ font-family: {MONO}; }}
  .s {{ font-family: {SANS}; }}
  .f {{ animation: in .45s cubic-bezier(.2,.7,.2,1) both; }}
  @keyframes in {{ from {{ opacity: 0; transform: translateY(5px); }} to {{ opacity: 1; transform: none; }} }}
  @keyframes blink {{ 50% {{ opacity: 0; }} }}
  @media (prefers-reduced-motion: reduce) {{ .f, .cur {{ animation: none !important; }} }}{extra}
</style>"""


def color(t, c):
    return t.get(c, c)


def monogram_row(line, x0, y0, t, cw=12, ch=22, gap=2.2):
    """One row of the ANSI Shadow monogram, drawn as cells instead of glyphs.

    Box-drawing and block glyphs differ in height and width from font to font,
    so as text the letters only line up on some systems. As rects and paths
    they line up everywhere.
    """
    blocks, shadow = [], []
    for i, glyph in enumerate(line):
        x, y = x0 + i * cw, y0
        cx, cy, r, b = x + cw / 2, y + ch / 2, x + cw, y + ch
        if glyph == "█":
            blocks.append(f'<rect x="{x}" y="{y}" width="{cw + 0.3}" height="{ch + 0.3}"/>')
        elif glyph == "═":
            shadow.append(f"M{x} {cy - gap}H{r}M{x} {cy + gap}H{r}")
        elif glyph == "║":
            shadow.append(f"M{cx - gap} {y}V{b}M{cx + gap} {y}V{b}")
        elif glyph == "╗":
            shadow.append(f"M{x} {cy - gap}H{cx + gap}V{b}M{x} {cy + gap}H{cx - gap}V{b}")
        elif glyph == "╔":
            shadow.append(f"M{r} {cy - gap}H{cx - gap}V{b}M{r} {cy + gap}H{cx + gap}V{b}")
        elif glyph == "╝":
            shadow.append(f"M{x} {cy + gap}H{cx + gap}V{y}M{x} {cy - gap}H{cx - gap}V{y}")
        elif glyph == "╚":
            shadow.append(f"M{r} {cy + gap}H{cx - gap}V{y}M{r} {cy - gap}H{cx + gap}V{y}")
    return (
        f'<path d="{"".join(shadow)}" fill="none" stroke="{t["faint"]}" stroke-width="1.3"/>'
        f'<g fill="url(#ink)">{"".join(blocks)}</g>'
    )


def hero(name, t):
    W, H = 880, 404
    cw14 = 8.43  # advance of a 14 px monospace cell
    cmd = "fastfetch"
    px, py = 32, 78  # prompt baseline
    type_start, per_char = 0.35, 0.09
    type_dur = per_char * len(cmd)
    total = type_start + type_dur
    # Discrete steps: hidden until type_start, then one more character per tick.
    widths = ";".join(["0"] + [f"{i * cw14:.2f}" for i in range(len(cmd) + 1)])
    times = ";".join(["0"] + [f"{(type_start + i * per_char) / total:.4f}" for i in range(len(cmd) + 1)])

    info_x, info_y, lh = 362, 120, 22
    cell_w, cell_h = 12, 22
    rows = 2 + len(FETCH) + 2  # header, rule, pairs, gap, colour blocks
    logo_y = info_y - 15 + (rows * lh - len(MONOGRAM) * cell_h) / 2

    reveal = type_start + type_dur + 0.25
    parts = []
    for i, line in enumerate(MONOGRAM):
        parts.append(
            f'<g class="f" style="animation-delay:{reveal + i * 0.06:.2f}s">'
            f"{monogram_row(line, px, logo_y + i * cell_h, t, cell_w, cell_h)}</g>"
        )

    d = reveal + 0.15
    y = info_y
    parts.append(
        f'<text class="m f" x="{info_x}" y="{y}" font-size="14" font-weight="700" style="animation-delay:{d:.2f}s">'
        f'<tspan fill="{t["accent"]}">julian</tspan><tspan fill="{t["text"]}">@</tspan>'
        f'<tspan fill="{t["accent"]}">ai-z-group</tspan></text>'
    )
    y += lh
    d += 0.07
    parts.append(
        f'<text class="m f" x="{info_x}" y="{y}" font-size="14" fill="{t["faint"]}" style="animation-delay:{d:.2f}s">'
        f'{"─" * 17}</text>'
    )
    for key, val in FETCH:
        y += lh
        d += 0.07
        parts.append(
            f'<text class="m f" x="{info_x}" y="{y}" font-size="14" xml:space="preserve" style="animation-delay:{d:.2f}s">'
            f'<tspan fill="{t["accent"]}" font-weight="700">{esc(key.ljust(10))}</tspan>'
            f'<tspan fill="{t["text"]}">{esc(val)}</tspan></text>'
        )
    y += lh * 2 - 14
    d += 0.1
    blocks = "".join(
        f'<rect x="{info_x + i * 26}" y="{y}" width="22" height="14" rx="2" fill="{c}"/>'
        for i, c in enumerate(t["blocks"])
    )
    parts.append(f'<g class="f" style="animation-delay:{d:.2f}s">{blocks}</g>')

    end_y = H - 34
    d += 0.3
    body = "\n  ".join(parts)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">
<title id="title">jal@m5 — fastfetch</title>
<desc id="desc">A terminal window. The command fastfetch prints a JAL monogram in block letters next to: name Julian Antony Lang; role CTO, AI-Z Group; invented Brane AIF, the AI Interaction Firewall; base Stuttgart, Germany; stack TypeScript, Python, Rust, Swift, C; likes on-device AI, NEON assembly, terminals.</desc>
{style(t)}
<defs>
  <linearGradient id="ink" gradientUnits="userSpaceOnUse" x1="{px}" y1="{logo_y}" x2="{px + 24 * cell_w}" y2="{logo_y + 6 * cell_h}">
    <stop offset="0" stop-color="{t["accent"]}"/><stop offset="1" stop-color="{t["accent2"]}"/>
  </linearGradient>
  <clipPath id="win"><rect width="{W}" height="{H}" rx="12"/></clipPath>
  <clipPath id="typed"><rect x="{px + 4 * cw14:.2f}" y="{py - 16}" width="{len(cmd) * cw14:.2f}" height="22">
    <animate attributeName="width" begin="0s" dur="{total:.2f}s" fill="freeze" calcMode="discrete" values="{widths}" keyTimes="{times}"/>
  </rect></clipPath>
</defs>
<g clip-path="url(#win)">
  <rect width="{W}" height="{H}" fill="{t["bg"]}"/>
  <rect width="{W}" height="38" fill="{t["chrome"]}"/>
  <line x1="0" y1="38.5" x2="{W}" y2="38.5" stroke="{t["border"]}"/>
  <circle cx="22" cy="19" r="6" fill="{t["dots"][0]}"/><circle cx="42" cy="19" r="6" fill="{t["dots"][1]}"/><circle cx="62" cy="19" r="6" fill="{t["dots"][2]}"/>
  <text class="m" x="{W / 2}" y="23.5" font-size="12" fill="{t["muted"]}" text-anchor="middle">jal@m5 — ~ — zsh</text>
  <text class="m" x="{px}" y="{py}" font-size="14" xml:space="preserve"><tspan fill="{t["accent"]}" font-weight="700">~ ❯ </tspan></text>
  <text class="m" x="{px + 4 * cw14:.2f}" y="{py}" font-size="14" fill="{t["text"]}" clip-path="url(#typed)">{cmd}</text>
  {body}
  <text class="m f" x="{px}" y="{end_y}" font-size="14" xml:space="preserve" style="animation-delay:{d:.2f}s"><tspan fill="{t["accent"]}" font-weight="700">~ ❯ </tspan></text>
  <rect class="cur" x="{px + 4 * cw14:.2f}" y="{end_y - 13}" width="8" height="16" fill="{t["accent"]}" style="animation: in .3s {d:.2f}s both, blink 1.05s steps(1) {d + 0.6:.2f}s infinite"/>
</g>
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="11.5" fill="none" stroke="{t["border"]}"/>
</svg>
"""


def card(c, t):
    W, H = 424, 172
    art = "".join(f'<tspan fill="{color(t, col)}">{esc(s)}</tspan>' for s, col in c["art"])
    desc = "".join(
        f'<text class="s" x="22" y="{74 + i * 20}" font-size="13.5" fill="{t["text"]}">{esc(line)}</text>'
        for i, line in enumerate(c["desc"])
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title">
<title id="title">{esc(c["repo"])} — {esc(" ".join(c["desc"]))}</title>
{style(t)}
<rect x=".5" y=".5" width="{W - 1}" height="{H - 1}" rx="10.5" fill="{t["panel"]}" stroke="{t["border"]}"/>
<text class="m" x="22" y="38" font-size="16" font-weight="700"><tspan fill="{t["accent"]}">{esc(c["glyph"])}</tspan><tspan fill="{t["text"]}" dx="9">{esc(c["repo"])}</tspan></text>
<text class="m" x="{W - 22}" y="37" font-size="11.5" fill="{t["muted"]}" text-anchor="end">{esc(c["tag"])}</text>
{desc}
<text class="m" x="22" y="124" font-size="12" xml:space="preserve">{art}</text>
<line x1="22" y1="139.5" x2="{W - 22}" y2="139.5" stroke="{t["border"]}"/>
<circle cx="27" cy="155" r="5" fill="{LANG[c["lang"]]}"/>
<text class="m" x="39" y="159" font-size="11.5" fill="{t["muted"]}" xml:space="preserve">{esc(c["lang"])} · {esc(c["foot"])}</text>
</svg>
"""


def rule(label, t, sub=""):
    W, H = 880, 44
    lab = f"~/{label}"
    x_after = 32 + (len(lab) + 4) * 8.43 + 10
    sub_svg = (
        f'<text class="m" x="{W - 2}" y="27" font-size="12" fill="{t["muted"]}" text-anchor="end">{esc(sub)}</text>'
        if sub else ""
    )
    x_end = W - 2 - (len(sub) * 7.23 + 14 if sub else 0)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{esc(lab)}">
{style(t)}
<text class="m" x="2" y="27" font-size="14" xml:space="preserve"><tspan fill="{t["accent"]}" font-weight="700">~ ❯ </tspan><tspan fill="{t["text"]}">cd {esc(lab)}</tspan></text>
<line x1="{x_after:.1f}" y1="22.5" x2="{x_end:.1f}" y2="22.5" stroke="{t["border"]}" stroke-dasharray="2 4"/>
{sub_svg}
</svg>
"""


def footer(t):
    W, H = 880, 60
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="exit — process completed">
{style(t)}
<line x1="0" y1="10.5" x2="{W}" y2="10.5" stroke="{t["border"]}"/>
<text class="m" x="2" y="40" font-size="14" xml:space="preserve"><tspan fill="{t["accent"]}" font-weight="700">~ ❯ </tspan><tspan fill="{t["text"]}">exit</tspan><tspan fill="{t["faint"]}">    [process completed]</tspan></text>
<text class="m" x="{W - 2}" y="40" font-size="12" fill="{t["muted"]}" text-anchor="end">no trackers · no widgets · plain SVG from this repo</text>
</svg>
"""


def main():
    OUT.mkdir(exist_ok=True)
    for name, t in THEMES.items():
        files = {
            f"hero-{name}.svg": hero(name, t),
            f"rule-projects-{name}.svg": rule("projects", t, "public · MIT"),
            f"rule-activity-{name}.svg": rule("activity", t, "every commit, eaten in order"),
            f"footer-{name}.svg": footer(t),
        }
        for c in CARDS:
            files[f"card-{c['repo']}-{name}.svg"] = card(c, t)
        for fn, svg in files.items():
            (OUT / fn).write_text(svg, encoding="utf-8")
    print(f"wrote {len(list(OUT.glob('*.svg')))} files to {OUT}")


if __name__ == "__main__":
    main()
