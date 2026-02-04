#!/usr/bin/env python3
"""Generate exhaustive Classical Jyotish combination catalog."""
from pathlib import Path
import pandas as pd

PLANETS = ["Sun","Moon","Mars","Mercury","Jupiter","Venus","Saturn","Rahu","Ketu"]
MALEFICS = ["Mars","Saturn","Rahu","Ketu"]
ASPECTS = {
    "conjunction": 0,
    "sextile": 60,
    "square": 90,
    "trine": 120,
    "opposition": 180,
}
ORBS = [1, 3, 5, 8]
HOUSES = list(range(1, 13))
SIGNS = [
    "Aries","Taurus","Gemini","Cancer","Leo","Virgo",
    "Libra","Scorpio","Sagittarius","Capricorn","Aquarius","Pisces",
]
TITHI = list(range(1, 31))
KARANAS = [
    "Bava","Balava","Kaulava","Taitila","Gara","Vanija","Vishti",
    "Shakuni","Chatushpada","Naga","Kimstughna",
]
YOGAS = list(range(1, 28))
WINDOWS = [0, 1, 3, 7, 14, 30]

SOURCES = "Brihat Samhita; BPHS; Surya Siddhanta; Jataka Parijata; Saravali"

rows = []

def add(category, rule, parameters=None, window=None, **fields):
    combo_id = f"{category}:{len(rows)+1:06d}"
    row = {
        "combo_id": combo_id,
        "category": category,
        "rule": rule,
        "parameters": parameters or "",
        "window_days": window if window is not None else "",
        "sources": SOURCES,
    }
    row.update(fields)
    rows.append(row)

# Planetary aspects (all pairs, all major aspects, all orbs)
for i, p1 in enumerate(PLANETS):
    for p2 in PLANETS[i+1:]:
        for asp_name, asp_deg in ASPECTS.items():
            for orb in ORBS:
                rule = f"Aspect {asp_name} between {p1} and {p2}"
                params = f"angle={asp_deg}±{orb}°"
                add("aspects", rule, params, p1=p1, p2=p2, aspect=asp_name, aspect_deg=asp_deg, orb=orb)

# Malefic aspects (subset)
for i, p1 in enumerate(MALEFICS):
    for p2 in MALEFICS[i+1:]:
        for asp_name, asp_deg in ASPECTS.items():
            for orb in ORBS:
                rule = f"Malefic aspect {asp_name} between {p1} and {p2}"
                params = f"angle={asp_deg}±{orb}°"
                add("malefic_aspects", rule, params, p1=p1, p2=p2, aspect=asp_name, aspect_deg=asp_deg, orb=orb)

# Graha Yuddha (close conjunction)
for i, p1 in enumerate(PLANETS):
    for p2 in PLANETS[i+1:]:
        add("graha_yuddha", f"Graha Yuddha between {p1} and {p2}", "orb<=1°", p1=p1, p2=p2, orb=1)

# Combustion & retrograde
for p in PLANETS:
    add("combustion", f"{p} combust", "orb<=8°", p1=p, orb=8)
    add("retrograde", f"{p} retrograde", p1=p)

# Shadbala thresholds (low/medium/high)
for p in PLANETS:
    for band in ["low","medium","high"]:
        add("shadbala", f"{p} shadbala {band}", "band=0-33/34-66/67-100", p1=p, band=band)

# Houses and signs (all planets in all houses/signs)
for p in PLANETS:
    for h in HOUSES:
        add("house", f"{p} in house {h}", p1=p, house=h)
    for s in SIGNS:
        add("sign", f"{p} in sign {s}", p1=p, sign=s)

# Nakshatra lords
for lord in PLANETS:
    add("nakshatra", f"Moon in nakshatra ruled by {lord}", p1=lord)

# Panchanga elements
for t in TITHI:
    add("tithi", f"Tithi {t}", tithi=t)
for k in KARANAS:
    add("karana", f"Karana {k}", karana=k)
for y in YOGAS:
    add("yoga", f"Yoga {y}", yoga=y)

# Eclipses and syzygy windows
add("eclipse", "Solar eclipse window", "syzygy + node proximity", eclipse_type="solar")
add("eclipse", "Lunar eclipse window", "syzygy + node proximity", eclipse_type="lunar")
add("syzygy", "New Moon (Amavasya)", phase="new")
add("syzygy", "Full Moon (Purnima)", phase="full")

# Vimshottari dasha (India + Nepal reference charts)
for lord in PLANETS:
    add("india_dasha", f"India Vimshottari Mahadasha: {lord}", "system=vimshottari", lord=lord)
    add("india_antardasha", f"India Vimshottari Antardasha: {lord}", "system=vimshottari", sub_lord=lord)

for lord in PLANETS:
    add("nepal_dasha", f"Nepal Vimshottari Mahadasha: {lord}", "system=vimshottari", lord=lord)
    add("nepal_antardasha", f"Nepal Vimshottari Antardasha: {lord}", "system=vimshottari", sub_lord=lord)

for india_lord in PLANETS:
    for nepal_lord in PLANETS:
        add(
            "india_nepal_dasha_pair",
            f"India {india_lord} Mahadasha with Nepal {nepal_lord} Mahadasha",
            "pair=mahadasha",
            india_lord=india_lord,
            nepal_lord=nepal_lord,
        )
        add(
            "india_nepal_antardasha_pair",
            f"India {india_lord} Antardasha with Nepal {nepal_lord} Antardasha",
            "pair=antardasha",
            india_lord=india_lord,
            nepal_lord=nepal_lord,
        )

# Compound examples (pairwise triggers with windows)
for window in WINDOWS:
    add("compound", "Malefic conjunction during eclipse window", "Mars/Saturn/Rahu/Ketu within orb; eclipse window", window, compound="malefic_conj_eclipse")

out_dir = Path(__file__).resolve().parents[1] / "data"
out_dir.mkdir(parents=True, exist_ok=True)
cat_path = out_dir / "combination_catalog.csv"
pd.DataFrame(rows).to_csv(cat_path, index=False)
print(f"Wrote {cat_path} with {len(rows)} combinations")
