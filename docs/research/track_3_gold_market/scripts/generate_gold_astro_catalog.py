#!/usr/bin/env python3
"""Generate exhaustive astrology principles catalog for gold (Vedic + Western)."""
from pathlib import Path
import pandas as pd

PLANETS = ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Uranus","Neptune","Pluto","Rahu","Ketu"]
MALEFICS_VEDIC = ["Mars","Saturn","Rahu","Ketu"]
ASPECTS = {
    "conjunction": 0,
    "sextile": 60,
    "square": 90,
    "trine": 120,
    "opposition": 180,
}
MINOR_ASPECTS = {
    "semisextile": 30,
    "semisquare": 45,
    "sesquiquadrate": 135,
    "quincunx": 150,
}
ORBS = [1, 3, 5, 8]
SIGNS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces",
]
WINDOWS = [0,1,3,7,14,30]

SOURCES = "Vedic + Western (comprehensive)"

rows = []

def add(category, rule, parameters=None, **fields):
    combo_id = f"{category}:{len(rows)+1:06d}"
    row = {
        "combo_id": combo_id,
        "category": category,
        "rule": rule,
        "parameters": parameters or "",
        "sources": SOURCES.strip(),
    }
    row.update(fields)
    rows.append(row)

# Major aspects (all planet pairs)
for i, p1 in enumerate(PLANETS):
    for p2 in PLANETS[i+1:]:
        for name, deg in ASPECTS.items():
            for orb in ORBS:
                add("major_aspect", f"{p1}-{p2} {name}", f"angle={deg}±{orb}°", p1=p1, p2=p2, aspect=name, aspect_deg=deg, orb=orb)

# Minor aspects (western)
for i, p1 in enumerate(PLANETS):
    for p2 in PLANETS[i+1:]:
        for name, deg in MINOR_ASPECTS.items():
            for orb in [1,2,3]:
                add("minor_aspect", f"{p1}-{p2} {name}", f"angle={deg}±{orb}°", p1=p1, p2=p2, aspect=name, aspect_deg=deg, orb=orb)

# Vedic malefic aspects subset
for i, p1 in enumerate(MALEFICS_VEDIC):
    for p2 in MALEFICS_VEDIC[i+1:]:
        for name, deg in ASPECTS.items():
            for orb in ORBS:
                add("vedic_malefic_aspect", f"{p1}-{p2} {name}", f"angle={deg}±{orb}°", p1=p1, p2=p2, aspect=name, aspect_deg=deg, orb=orb)

# Retrograde & combustion
for p in PLANETS:
    add("retrograde", f"{p} retrograde", p1=p)
    if p not in ["Sun", "Moon", "Rahu", "Ketu"]:
        add("combustion", f"{p} combust", "orb<=8°", p1=p, orb=8)

# Ingress (planet enters sign)
for p in PLANETS:
    for s in SIGNS:
        add("ingress", f"{p} ingress into {s}", p1=p, sign=s)

# Lunar phases
add("lunar_phase", "New Moon", "tithi=30", phase="new")
add("lunar_phase", "Full Moon", "tithi=15", phase="full")
add("lunar_phase", "First Quarter", "sun-moon=90°", phase="first_quarter")
add("lunar_phase", "Last Quarter", "sun-moon=270°", phase="last_quarter")

# Eclipses (proxy)
add("eclipse", "Solar eclipse window", "syzygy + node proximity", eclipse_type="solar")
add("eclipse", "Lunar eclipse window", "syzygy + node proximity", eclipse_type="lunar")

# Vedic Nakshatra lords (Moon)
for lord in ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"]:
    add("nakshatra_lord", f"Moon in nakshatra ruled by {lord}", lord=lord)

# Vimshottari dasha (global baseline)
for lord in ["Ketu","Venus","Sun","Moon","Mars","Rahu","Jupiter","Saturn","Mercury"]:
    add("dasha", f"Global Vimshottari Mahadasha: {lord}", "system=vimshottari", lord=lord)

# Windowed compound examples
for w in WINDOWS:
    add("compound", "Mars-Saturn hard aspect within window", "aspect=square/opposition; windowed", window_days=w)

out_dir = Path(__file__).resolve().parents[1] / "data"
out_dir.mkdir(parents=True, exist_ok=True)
cat_path = out_dir / "gold_astro_catalog.csv"
pd.DataFrame(rows).to_csv(cat_path, index=False)
print(f"Wrote {cat_path} with {len(rows)} combinations")
