"""Draw the map background (AZ, NM, CO outlines) and the two source badges as SVG for the report.

Outlines are simplified and drawn by hand from border coordinates; no map service is used.
Power BI image visuals take the SVG as is.  Run: python scripts/make_report_art.py
"""
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "art")          # SVG sources live in the repo (reproducible)
RES = os.path.join(ROOT, "powerbi", "MiningOperationsSafety.Report", "StaticResources", "RegisteredResources")
os.makedirs(OUT, exist_ok=True)

# ------------------------------------------------------------------ map
LON0, LON1, LAT0, LAT1 = -114.9, -104.3, 31.0, 41.2
W, H = 1040, 1237


def px(lon, lat):
    return ((lon - LON0) / (LON1 - LON0) * W, (LAT1 - lat) / (LAT1 - LAT0) * H)


def poly(pts, **style):
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in (px(*p) for p in pts))
    attrs = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in style.items())
    return f'<polygon points="{d}" {attrs}/>'


AZ = [(-114.05, 37.0), (-109.05, 37.0), (-109.05, 31.33), (-111.07, 31.33), (-114.81, 32.49), (-114.72, 32.72),
      (-114.52, 33.03), (-114.72, 33.41), (-114.52, 33.69), (-114.14, 34.30), (-114.43, 34.27), (-114.57, 34.80),
      (-114.63, 35.00), (-114.75, 36.10), (-114.05, 36.20)]
NM = [(-109.05, 37.0), (-103.0, 37.0), (-103.06, 32.0), (-106.62, 32.0), (-106.53, 31.78), (-108.21, 31.78),
      (-108.21, 31.33), (-109.05, 31.33)]
CO = [(-109.05, 41.0), (-102.05, 41.0), (-102.05, 37.0), (-109.05, 37.0)]
UT = [(-114.05, 45.0), (-111.05, 45.0), (-111.05, 41.0), (-109.05, 41.0), (-109.05, 37.0), (-114.05, 37.0)]
WEST = [(-130, 45), (-114.05, 45), (-114.05, 36.2), (-114.75, 36.1), (-114.63, 35.0), (-114.57, 34.8), (-114.43, 34.27),
        (-114.14, 34.30), (-114.52, 33.69), (-114.72, 33.41), (-114.52, 33.03), (-114.72, 32.72), (-114.81, 32.49), (-130, 32.5)]
MEX = [(-130, 20), (-100, 20), (-104.5, 29.5), (-106.53, 31.78), (-108.21, 31.78), (-108.21, 31.33), (-111.07, 31.33),
       (-114.81, 32.49), (-130, 32.5)]
TX = [(-103.0, 37.0), (-90, 37.0), (-90, 20), (-104.5, 29.5), (-106.53, 31.78), (-106.62, 32.0), (-103.06, 32.0)]

LABELS = [  # (text, lon, lat, dx, dy, anchor)
    ("Morenci", -109.335, 33.063, 12, -10, "start"),
    ("Sierrita", -111.101, 31.876, -12, 4, "end"),
    ("Bagdad", -113.169, 34.595, 12, 4, "start"),
    ("Chino · Tyrone", -108.084, 32.790, 14, 30, "start"),
    ("Safford", -109.701, 32.955, -12, 22, "end"),
    ("Henderson", -105.846, 39.771, -14, -10, "end"),
    ("Climax", -106.184, 39.369, -14, 10, "end"),
]
STATES = [("ARIZONA", -112.4, 34.9), ("NUEVO MÉXICO", -106.55, 35.6), ("COLORADO", -105.9, 38.1)]
NEIGH = [("UTAH", -111.9, 38.6), ("MÉXICO", -110.0, 31.12)]

svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">',
       f'<rect width="{W}" height="{H}" fill="#E2DCD1"/>',
       poly(WEST, fill="#E2DCD1"), poly(UT, fill="#E2DCD1"),
       poly(TX, fill="#E2DCD1"), poly(MEX, fill="#DAD3C7")]
for pts in (AZ, NM, CO):
    svg.append(poly(pts, fill="#FBF9F5", stroke="#9C9384", stroke_width=3, stroke_linejoin="round"))
for t, lon, lat in STATES:
    x, y = px(lon, lat)
    svg.append(f'<text x="{x:.0f}" y="{y:.0f}" text-anchor="middle" font-size="40" font-weight="600" letter-spacing="5" fill="#D8D0C2">{t}</text>')
for t, lon, lat in NEIGH:
    x, y = px(lon, lat)
    svg.append(f'<text x="{x:.0f}" y="{y:.0f}" text-anchor="middle" font-size="30" font-weight="600" letter-spacing="5" fill="#C2BAAB">{t}</text>')
for t, lon, lat, dx, dy, anchor in LABELS:
    x, y = px(lon, lat)
    svg.append(f'<text x="{x + dx:.0f}" y="{y + dy:.0f}" text-anchor="{anchor}" font-size="25" font-weight="600" fill="#2B2F33" '
               f'stroke="#FBF9F5" stroke-width="7" paint-order="stroke" stroke-linejoin="round">{t}</text>')
svg.append('</svg>')
open(os.path.join(OUT, "mapa_suroeste.svg"), "w", encoding="utf-8").write("\n".join(svg))

# ------------------------------------------------------------------ badges
def badge(name, label, title, sub, icon):
    s = f'''<svg xmlns="http://www.w3.org/2000/svg" width="960" height="300" viewBox="0 0 960 300" font-family="Segoe UI, Arial, sans-serif">
<rect x="3" y="3" width="954" height="294" rx="28" fill="#FFFFFF" stroke="#E3DED7" stroke-width="6"/>
<rect x="3" y="3" width="26" height="294" rx="13" fill="#B8602A"/>
<circle cx="150" cy="150" r="84" fill="#F4EADF"/>
{icon}
<text x="270" y="108" font-size="30" font-weight="600" letter-spacing="5" fill="#8A5A3A">{label}</text>
<text x="270" y="178" font-size="62" font-weight="700" fill="#2B2F33">{title}</text>
<text x="270" y="228" font-size="30" fill="#4A5058">{sub}</text>
</svg>'''
    open(os.path.join(OUT, name + ".svg"), "w", encoding="utf-8").write(s)


shield = '<path d="M150 92 L196 108 L196 152 C196 182 176 202 150 212 C124 202 104 182 104 152 L104 108 Z" fill="#B8602A"/><path d="M128 150 L144 166 L174 130" fill="none" stroke="#FFFFFF" stroke-width="11" stroke-linecap="round" stroke-linejoin="round"/>'
mountain = '<path d="M90 196 L132 124 L156 160 L176 132 L212 196 Z" fill="#B8602A"/><path d="M132 124 L145 146 L132 142 L120 146 Z" fill="#F4EADF"/><rect x="90" y="196" width="122" height="10" fill="#4F6D8F"/>'
badge("insignia_msha", "FUENTE DE DATOS", "MSHA", "Mine Safety and Health Administration (EE. UU.)", shield)
badge("insignia_freeport", "MINAS ANALIZADAS", "Freeport-McMoRan", "43 minas en AZ, NM, CO y OR · 2000 a 2026", mountain)

# ------------------------------------------------------------------ copy into the report's registered resources
for name in ("mapa_suroeste", "insignia_msha", "insignia_freeport"):
    shutil.copy(os.path.join(OUT, name + ".svg"), os.path.join(RES, name + ".svg"))
    print("ok", name)
