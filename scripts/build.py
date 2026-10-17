#!/usr/bin/env python3
"""Render every SVG in assets/ from the data in this file.

    uv run --no-project --with fonttools --with uharfbuzz python scripts/build.py

Each image is written twice, -dark.svg and -light.svg; README.md picks one
per viewer theme with <picture>. Type is set in Geist and Geist Mono
(fonts/, SIL OFL) and drawn as outlines, so it looks the same on every
system. Only the halftone globe stays live text, with a subset of Geist Mono
embedded; any monospace fallback keeps its columns aligned.
"""
import base64
import io
import math
import random
from pathlib import Path
from xml.sax.saxutils import escape

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"
W = 880

# Siemens Energy was a CompuSafe client; flip once naming it is cleared.
NAME_SIEMENS = False

# Upstream pull requests, newest first: (repo, number, title, state). Only
# "merged" or "open" ones that exist on GitHub belong here.
UPSTREAM = []

THEMES = {
    "dark": dict(fg="#f5f5f5", fg2="#d4d4d4", muted="#a3a3a3", subtle="#737373",
                 faint="#525252", line="#262626", glow="#fafafa", rim="#3f3f3f"),
    "light": dict(fg="#0a0a0a", fg2="#262626", muted="#525252", subtle="#737373",
                  faint="#a3a3a3", line="#e5e5e5", glow="#0a0a0a", rim="#c4c4c4"),
}

PI_HEX = ("3.243F6A8885A308D313198A2E03707344A4093822299F31D0082EFA98EC4E6C89"
          "452821E638D01377BE5466CF34E90C6CC0AC29B7C97C50DD3F84D5B5")

# ── type ────────────────────────────────────────────────────────────────────

class Face:
    """One static instance of a variable font: shaping + outlines."""

    _cache = {}

    def __init__(self, path, weight):
        self.font = instancer.instantiateVariableFont(TTFont(path), {"wght": weight})
        buf = io.BytesIO()
        self.font.save(buf)
        self.hb = hb.Font(hb.Face(buf.getvalue()))
        self.glyphs = self.font.getGlyphSet()
        self.upm = self.font["head"].unitsPerEm
        self.key = f"{'m' if 'Mono' in path else 's'}{weight}"
        self.paths = {}

    @classmethod
    def get(cls, family, weight):
        k = (family, weight)
        if k not in cls._cache:
            path = ROOT / "fonts" / ("GeistMono.ttf" if family == "mono" else "Geist.ttf")
            cls._cache[k] = Face(str(path), weight)
        return cls._cache[k]

    def shape(self, text, tracking=0.0):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb, buf, {"kern": True, "liga": True})
        x, out = 0, []
        track = tracking * self.upm
        for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
            if info.codepoint == 0:
                raise ValueError(f"glyph missing in {self.key}: {text!r}")
            out.append((info.codepoint, x + pos.x_offset))
            x += pos.x_advance + track
        return out, x - (track if out else 0)

    def path(self, gid):
        if gid not in self.paths:
            pen = SVGPathPen(self.glyphs, ntos=lambda v: str(round(v)))
            self.glyphs[self.font.getGlyphName(gid)].draw(pen)
            self.paths[gid] = pen.getCommands()
        return self.paths[gid]


class Doc:
    def __init__(self, width, height, title, desc=""):
        self.w, self.h, self.title, self.desc = width, height, title, desc
        self.defs, self.body, self.style = {}, [], []

    def measure(self, s, size, family="sans", weight=400, tracking=0.0):
        face = Face.get(family, weight)
        return face.shape(s, tracking)[1] * size / face.upm

    def text(self, x, y, s, size, fill, family="sans", weight=400, tracking=0.0,
             anchor="start", cls=None, delay=None, opacity=None):
        face = Face.get(family, weight)
        glyphs, adv = face.shape(s, tracking)
        k = size / face.upm
        if anchor == "end":
            x -= adv * k
        elif anchor == "middle":
            x -= adv * k / 2
        uses = []
        for gid, gx in glyphs:
            d = face.path(gid)
            if not d:
                continue  # spaces
            ref = f"{face.key}-{gid}"
            self.defs.setdefault(ref, d)
            uses.append(f'<use xlink:href="#{ref}" x="{round(gx)}"/>')
        glyph_group = (f'<g fill="{fill}" transform="translate({x:.2f} {y:.2f}) scale({k:.5f} {-k:.5f})"'
                       + (f' opacity="{opacity:.2f}"' if opacity is not None else "")
                       + f'>{"".join(uses)}</g>')
        if cls:
            # The animation sets a CSS transform, which would replace the SVG one: wrap it.
            delay_attr = f' style="animation-delay:{delay:.2f}s"' if delay is not None else ""
            glyph_group = f'<g class="{cls}"{delay_attr}>{glyph_group}</g>'
        self.body.append(glyph_group)
        return adv * k

    def wrap(self, s, width, size, family="sans", weight=400):
        lines, cur = [], ""
        for word in s.split():
            trial = f"{cur} {word}".strip()
            if cur and self.measure(trial, size, family, weight) > width:
                lines.append(cur)
                cur = word
            else:
                cur = trial
        return lines + [cur]

    def raw(self, svg):
        self.body.append(svg)

    def render(self):
        defs = "".join(f'<path id="{k}" d="{d}"/>' for k, d in self.defs.items())
        style = f"<style>{''.join(self.style)}</style>" if self.style else ""
        desc = f"<desc>{escape(self.desc)}</desc>" if self.desc else ""
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" role="img">'
            f"<title>{escape(self.title)}</title>{desc}{style}<defs>{defs}</defs>"
            + "".join(self.body) + "</svg>\n"
        )


FADE = (
    ".f{animation:in .7s cubic-bezier(.2,.7,.2,1) both}"
    "@keyframes in{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}"
    "@media (prefers-reduced-motion:reduce){.f{animation:none}}"
)


def hairline(doc, y, color, x1=0, x2=W):
    doc.raw(f'<line x1="{x1}" y1="{y + .5}" x2="{x2}" y2="{y + .5}" stroke="{color}"/>')



# ── the planet ──────────────────────────────────────────────────────────────
#
# A halftone globe: three dot glyphs (· • ●) at two opacities give six tones.
# The shaded ocean and the dotted orbit are one static layer; the continents
# and a satellite are FRAMES layers shown one at a time, so the globe turns.

DOTS = "·•●"
PITCH = 6.0                       # 10 px Geist Mono advances exactly 6 px
GRID = 66                         # cells per side
RADIUS = 2.05 * 60                # planet radius, px
ORBIT = 1.52                      # orbit radius, in planet radii
TILT, ORBIT_TILT = .40, .50
FRAMES, PERIOD = 60, 30.0
LIGHT = (-.55, .52, .65)


def _noise_table(seed=11):
    rng = random.Random(seed)
    perm = list(range(256))
    rng.shuffle(perm)
    return perm * 2, [rng.random() for _ in range(256)]


PERM, VALS = _noise_table()


def _lattice(i, j, k):
    return VALS[PERM[PERM[PERM[i & 255] + (j & 255)] + (k & 255)]]


def _noise(x, y, z):
    i, j, k = math.floor(x), math.floor(y), math.floor(z)
    fx, fy, fz = (t * t * (3 - 2 * t) for t in (x - i, y - j, z - k))
    def lerp(a, b, t):
        return a + (b - a) * t

    c =[[[_lattice(i + a, j + b, k + d) for d in (0, 1)] for b in (0, 1)] for a in (0, 1)]
    return lerp(lerp(lerp(c[0][0][0], c[0][0][1], fz), lerp(c[0][1][0], c[0][1][1], fz), fy),
                lerp(lerp(c[1][0][0], c[1][0][1], fz), lerp(c[1][1][0], c[1][1][1], fz), fy), fx)


def land(x, y, z):
    v, a, f = 0.0, .5, 1.5
    for _ in range(4):
        v += a * _noise(x * f + 11, y * f + 3, z * f + 7)
        a, f = a * .5, f * 2.03
    return v / .9375 > .55


def tone(v):
    """0..1 -> (glyph, bright) or None; six steps."""
    if v < .06:
        return None
    step = min(5, int(v * 6))
    return DOTS[step // 2], step % 2 == 1


def planet_layers():
    lx, ly, lz = LIGHT
    n = math.sqrt(lx * lx + ly * ly + lz * lz)
    lx, ly, lz = lx / n, ly / n, lz / n
    half = GRID * PITCH / 2
    cells = []  # (row, col, x, y, z, shade) for every cell on the disc
    for r in range(GRID):
        for c in range(GRID):
            x = ((c + .5) * PITCH - half) / RADIUS
            y = -((r + .5) * PITCH - half) / RADIUS
            if x * x + y * y <= 1:
                z = math.sqrt(1 - x * x - y * y)
                cells.append((r, c, x, y, z, max(0.0, x * lx + y * ly + z * lz)))
    zbuf = {(r, c): z for r, c, _, _, z, _ in cells}

    ct, st = math.cos(ORBIT_TILT), math.sin(ORBIT_TILT)

    def orbit_cell(a):
        ox, oz = ORBIT * math.cos(a), ORBIT * math.sin(a)
        x, y, z = ox, -oz * st, oz * ct
        c, r = int((x * RADIUS + half) / PITCH), int((-y * RADIUS + half) / PITCH)
        if not (0 <= r < GRID and 0 <= c < GRID):
            return None
        if z < zbuf.get((r, c), -9):
            return None  # behind the planet
        return r, c, z

    base = {}
    for r, c, x, y, z, shade in cells:
        t = tone(.20 + .34 * shade + .34 * (1 - z) ** 3)  # rim light keeps the disc round
        if t:
            base[(r, c)] = t
    front_orbit = set()
    for i in range(1600):
        hit = orbit_cell(2 * math.pi * i / 1600)
        if hit:
            r, c, z = hit
            base[(r, c)] = ("·", z > 0)
            if (r, c) in zbuf:
                front_orbit.add((r, c))
    # Clear the cells just above and below the orbit where it crosses the face,
    # so the line reads as passing in front of the planet.
    gap = {(r + d, c) for r, c in front_orbit for d in (-1, 1)} - front_orbit
    for cell in gap:
        if cell in zbuf:
            base.pop(cell, None)
    front_orbit |= gap

    ct2, st2 = math.cos(TILT), math.sin(TILT)
    frames = []
    for k in range(FRAMES):
        spin = 2 * math.pi * k / FRAMES
        cs, ss = math.cos(-spin), math.sin(-spin)
        layer = {}
        for r, c, x, y, z, shade in cells:
            if (r, c) in front_orbit:
                continue
            # view -> planet frame: undo the tilt, then the spin
            y1, z1 = y * ct2 + z * st2, -y * st2 + z * ct2
            px, pz = x * cs + z1 * ss, -x * ss + z1 * cs
            if land(px, y1, pz):
                t = tone(.30 + .52 * shade)
                if t and DOTS.index(t[0]) * 2 + t[1] > DOTS.index(base[(r, c)][0]) * 2 + base[(r, c)][1]:
                    layer[(r, c)] = t
        hit = orbit_cell(-2 * math.pi * k / FRAMES * 2 + 2.2)   # two laps per turn
        if hit:
            layer[(hit[0], hit[1])] = ("●", True)
        frames.append(layer)
    return base, frames


def dot_rows(layer, x0, y0, bright):
    """Emit one <text> per row for the cells of one opacity class."""
    rows = {}
    for (r, c), (g, b) in layer.items():
        if b == bright:
            rows.setdefault(r, {})[c] = g
    out = []
    for r in sorted(rows):
        cols = rows[r]
        lo, hi = min(cols), max(cols)
        line = "".join(cols.get(c, " ") for c in range(lo, hi + 1))
        # xml:space must sit on each <text>; as an image, Chrome ignores it when inherited.
        out.append(f'<text xml:space="preserve" x="{x0 + lo * PITCH:.0f}" y="{y0 + r * PITCH + 3.6:.1f}">{line}</text>')
    return "".join(out)


def mono_subset_b64(chars):
    font = instancer.instantiateVariableFont(TTFont(str(ROOT / "fonts/GeistMono.ttf")), {"wght": 400})
    opts = Options()
    opts.name_IDs = ["*"]
    opts.notdef_outline = True
    sub = Subsetter(opts)
    sub.populate(text=chars)
    sub.subset(font)
    buf = io.BytesIO()
    font.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


FONT_B64 = None
PLANET = None


def planet(doc, t, x0, y0):
    global PLANET
    if PLANET is None:
        PLANET = planet_layers()
    base, frames = PLANET
    half = GRID * PITCH / 2
    doc.style.append(
        f"@font-face{{font-family:GM;src:url(data:font/ttf;base64,{FONT_B64})}}"
        ".a{font-family:GM,ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace;"
        "font-size:10px;white-space:pre}.dim{opacity:.5}"
        f".fr{{opacity:0;animation:turn {PERIOD}s steps(1,end) infinite}}.fr0{{opacity:1}}"
        f"@keyframes turn{{0%{{opacity:1}}{100 / FRAMES:.4f}%{{opacity:0}}100%{{opacity:0}}}}"
        "@media (prefers-reduced-motion:reduce){.fr{animation:none}}"
    )
    doc.raw(
        f'<defs><radialGradient id="lit" gradientUnits="userSpaceOnUse" cx="{x0 + half - 60:.0f}" '
        f'cy="{y0 + half - 64:.0f}" r="{RADIUS * 2.1:.0f}">'
        f'<stop offset="0" stop-color="{t["glow"]}"/><stop offset=".6" stop-color="{t["fg2"]}"/>'
        f'<stop offset="1" stop-color="{t["muted"]}"/></radialGradient></defs>'
    )
    parts = [f'<g class="dim">{dot_rows(base, x0, y0, False)}</g>{dot_rows(base, x0, y0, True)}']
    for k, layer in enumerate(frames):
        delay = f' style="animation-delay:{k * PERIOD / FRAMES:.2f}s"' if k else ""
        parts.append(
            f'<g class="fr{" fr0" if k == 0 else ""}"{delay}>'
            f'<g class="dim">{dot_rows(layer, x0, y0, False)}</g>{dot_rows(layer, x0, y0, True)}</g>'
        )
    doc.raw(f'<g class="a" fill="url(#lit)">{"".join(parts)}</g>')


# ── pieces ──────────────────────────────────────────────────────────────────

def hero(t):
    doc = Doc(W, 410, "Julian Antony Lang — Co-Founder & CTO, AI-Z Group",
              "Julian Antony Lang. Co-Founder and CTO at AI-Z Group and inventor of Brane AIF, the AI "
              "Interaction Firewall. Builds AI that runs on the machine in front of you and decides "
              "what is allowed to leave it. Previously CompuSafe Data Systems, Allianz Technology, and "
              "co-founder of Omega VR. Beside the text, a halftone globe turns while a satellite circles it.")
    doc.style.append(FADE)
    planet(doc, t, W - GRID * PITCH + 12, 8)
    doc.text(-3, 118, "Julian Antony", 62, t["fg"], "sans", 600, -.035, cls="f", delay=.2)
    doc.text(-3, 184, "Lang", 62, t["fg"], "sans", 600, -.035, cls="f", delay=.28)
    doc.text(0, 228, "Co-Founder & CTO, AI-Z Group  ·  Inventor of Brane AIF", 17, t["fg2"], "sans", 500, -.005,
             cls="f", delay=.4)
    statement = "I build AI that runs on the machine in front of you — and decides what is allowed to leave it."
    for i, line in enumerate(doc.wrap(statement, 430, 17)):
        doc.text(0, 262 + i * 26, line, 17, t["muted"], "sans", 400, -.005, cls="f", delay=.48 + i * .06)
    before = ["CompuSafe Data Systems", "Allianz Technology"]
    before += ["Siemens Energy"] if NAME_SIEMENS else []
    before += ["co-founder, Omega VR"]
    doc.text(0, 372, "PREVIOUSLY", 10, t["subtle"], "mono", 400, .14, cls="f", delay=.7)
    doc.text(92, 372, "  ·  ".join(before), 10, t["muted"], "mono", 400, .06, cls="f", delay=.74)
    return doc.render()


def section(t, num, label, right=""):
    doc = Doc(W, 54, f"{num} — {label}")
    doc.text(0, 34, num, 10.5, t["subtle"], "mono", 400, .14)
    doc.text(36, 34, label.upper(), 10.5, t["fg2"], "mono", 500, .14)
    if right:
        doc.text(W, 34, right, 10.5, t["subtle"], "mono", 400, .1, anchor="end")
    hairline(doc, 53, t["line"])
    return doc.render()


def upstream_row(t, i, u):
    repo, number, title, state = u
    doc = Doc(W, 46, f"{repo}#{number} — {title} ({state})")
    if i > 1:
        hairline(doc, 0, t["line"])
    doc.text(0, 29, repo, 13.5, t["fg"], "mono", 500, -.01)
    doc.text(260, 29, title, 13.5, t["fg2"], "sans", 400, -.003)
    doc.text(W, 28, f"#{number}  ·  {state}  ↗", 10, t["subtle"], "mono", 400, .06, anchor="end")
    return doc.render()


def footer(t):
    doc = Doc(W, 40, "π in hexadecimal, fading out")
    adv = doc.measure("0", 11, "mono", 400, .18) + 11 * .18
    digits = PI_HEX[:90]
    for i, ch in enumerate(digits):
        a = (1 - i / len(digits)) ** 1.6
        if a < .04:
            break
        doc.text(i * adv, 24, ch, 11, t["muted"], "mono", 400, opacity=a)
    return doc.render()

def pic(name, alt, link=None, src=None):
    dark, light = (f"{src}-dark.svg", f"{src}-light.svg") if src else (f"assets/{name}-dark.svg", f"assets/{name}-light.svg")
    tag = (f'<picture><source media="(prefers-color-scheme: dark)" srcset="{dark}">'
           f'<source media="(prefers-color-scheme: light)" srcset="{light}">'
           f'<img src="{dark}" width="880" alt="{escape(alt, {chr(34): "&quot;"})}"></picture>')
    return f'<a href="{link}">{tag}</a>' if link else tag


def readme():
    blocks = [[pic("hero", "Julian Antony Lang — Co-Founder & CTO, AI-Z Group, inventor of Brane AIF. I build AI "
                           "that runs on the machine in front of you and decides what is allowed to leave it. "
                           "Previously CompuSafe Data Systems, Allianz Technology; co-founder of Omega VR.")]]
    if UPSTREAM:
        rows = [pic(f"up-{r.replace('/', '-')}-{n}", f"{r}#{n} — {title} ({state})",
                    link=f"https://github.com/{r}/pull/{n}") for r, n, title, state in UPSTREAM]
        blocks.append([pic("s-upstream", "Open source: upstream pull requests"), "<br>".join(rows)])
    blocks.append([pic("footer", "Pi in hexadecimal, fading out.")])
    body = "\n\n".join("<p>\n  " + "\n  ".join(b) + "\n</p>" for b in blocks)
    return (body + "\n\n<!-- Generated by scripts/build.py, README included: edit the data there and run\n"
            "     uv run --no-project --with fonttools --with uharfbuzz python scripts/build.py -->\n")


def main():
    global FONT_B64
    FONT_B64 = mono_subset_b64(DOTS + " ")
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.svg"):
        old.unlink()
    for name, t in THEMES.items():
        files = {f"hero-{name}.svg": hero(t), f"footer-{name}.svg": footer(t)}
        if UPSTREAM:
            files[f"s-upstream-{name}.svg"] = section(t, "01", "Open source", "upstream pull requests")
            for i, u in enumerate(UPSTREAM, 1):
                files[f"up-{u[0].replace('/', '-')}-{u[1]}-{name}.svg"] = upstream_row(t, i, u)
        for fn, svg in files.items():
            (OUT / fn).write_text(svg, encoding="utf-8")
    (ROOT / "README.md").write_text(readme(), encoding="utf-8")
    total = sum(p.stat().st_size for p in OUT.glob("*.svg"))
    print(f"wrote {len(list(OUT.glob('*.svg')))} files, {total / 1024:.0f} KB, to {OUT}")


if __name__ == "__main__":
    main()
