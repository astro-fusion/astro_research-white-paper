#!/usr/bin/env python3
"""Expand ``studies/combinations/grammar.yaml`` into candidate combinations.

Usage::

    python studies/combinations/scripts/enumerate.py [--csv out.csv]

The expansion is deterministic: the same grammar always gives the same
candidates in the same order with the same ids (``atl-00001``, ...). Each
candidate is a list of clauses (dicts) plus a canonical ``key`` and a
plain-words ``definition``.
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List

import yaml

GRAMMAR = Path(__file__).resolve().parents[1] / "grammar.yaml"

SIGNS = ("Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra",
         "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces")
VIMSHOTTARI = ("KETU", "VENUS", "SUN", "MOON", "MARS", "RAHU", "JUPITER",
               "SATURN", "MERCURY")
NAKSHATRAS = ("Ashvini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
              "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
              "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha",
              "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha",
              "Shravana", "Dhanishtha", "Shatabhisha", "Purva Bhadrapada",
              "Uttara Bhadrapada", "Revati")
PLACEMENT_KINDS = ("sign", "house_from_lagna", "house_from_moon", "nakshatra_group")


def load_grammar(path: Path = GRAMMAR) -> Dict:
    """Read the grammar file."""
    return yaml.safe_load(Path(path).read_text())


def _name(planet: str) -> str:
    return planet.capitalize()


def placements(g: Dict) -> List[Dict]:
    """Every placement clause, in planet then kind then value order."""
    out = []
    for p in g["planets"]:
        for kind in PLACEMENT_KINDS:
            if kind == "house_from_moon" and p == "MOON":
                continue
            n = 9 if kind == "nakshatra_group" else 12
            for v in range(n):
                out.append({"kind": "placement", "planet": p, "frame": kind,
                            "value": v})
    return out


def relations(g: Dict, actor: str = None) -> List[Dict]:
    """Aspect (ordered) and conjunction clauses, optionally for one actor."""
    planets = g["planets"]
    out = []
    for a in planets:
        if actor is not None and a != actor:
            continue
        for b in planets:
            if b != a:
                out.append({"kind": "aspect", "from": a, "to": b})
    for i, a in enumerate(planets):
        for b in planets[i + 1:]:
            if actor is None:
                out.append({"kind": "conjunction", "a": a, "b": b})
    if actor is not None:
        for b in planets:
            if b != actor:
                out.append({"kind": "conjunction", "a": actor, "b": b})
    return out


def dashas(g: Dict, levels=None) -> List[Dict]:
    """Dasha-lord clauses."""
    levels = levels or g["dasha"]["levels"]
    return [{"kind": "dasha", "planet": p, "level": int(lv)}
            for lv in levels for p in g["planets"]]


def clause_key(c: Dict) -> str:
    """Canonical text for one clause."""
    if c["kind"] == "placement":
        return f"{c['planet']}@{c['frame']}={c['value']}"
    if c["kind"] == "aspect":
        return f"{c['from']}>aspect>{c['to']}"
    if c["kind"] == "conjunction":
        return f"{c['a']}~conj~{c['b']}"
    return f"dasha{c['level']}={c['planet']}"


def clause_words(c: Dict, g: Dict, study: Dict) -> str:
    """Plain-words description of one clause."""
    if c["kind"] == "placement":
        p, v = _name(c["planet"]), c["value"]
        if c["frame"] == "sign":
            return f"{p} in {SIGNS[v]}"
        if c["frame"] == "house_from_lagna":
            loc = study.get("reference_location", {}).get("name", "the reference place")
            return f"{p} in house {v + 1} from the moment's lagna at {loc}"
        if c["frame"] == "house_from_moon":
            return f"{p} in house {v + 1} from the Moon"
        lord = VIMSHOTTARI[v]
        naks = ", ".join(NAKSHATRAS[i] for i in range(v, 27, 9))
        return f"{p} in a {_name(lord)}-ruled nakshatra ({naks})"
    if c["kind"] == "aspect":
        return f"{_name(c['from'])} casts a Parashari aspect on {_name(c['to'])}"
    if c["kind"] == "conjunction":
        orb = g["relations"]["conjunction"]["orb_deg"]
        return f"{_name(c['a'])} within {orb} deg of {_name(c['b'])}"
    level = {1: "mahadasha", 2: "antardasha"}[c["level"]]
    chart = study.get("reference_chart", {}).get("name", "the reference chart")
    return f"{_name(c['planet'])} {level} ({chart})"


def _template_clauses(t: Dict, g: Dict) -> List[List[Dict]]:
    tid = t["id"]
    if tid == "T1":
        return [[c] for c in placements(g)]
    if tid == "T2":
        return [[c] for c in relations(g)]
    if tid == "T3":
        return [[c] for c in dashas(g)]
    signs = [c for c in placements(g) if c["frame"] == "sign"]
    if tid == "T4":
        return [[pl, r] for pl in signs for r in relations(g, actor=pl["planet"])]
    if tid == "T5":
        return [[pl, d] for pl in placements(g) for d in dashas(g)
                if d["planet"] == pl["planet"]]
    if tid == "T6":
        out = []
        for r in relations(g):
            pair = (r.get("from", r.get("a")), r.get("to", r.get("b")))
            for d in dashas(g, levels=[1]):
                if d["planet"] in pair:
                    out.append([r, d])
        return out
    if tid == "T7":
        return [[pl, r, d] for pl in signs for r in relations(g, actor=pl["planet"])
                for d in dashas(g, levels=[1]) if d["planet"] == pl["planet"]]
    raise KeyError(f"unknown template {tid}")


def expand(g: Dict = None, study_id: str = "earthquake") -> List[Dict]:
    """Return every candidate of the grammar, with ids, keys and definitions."""
    g = g or load_grammar()
    study = next(s for s in g["studies"] if s["id"] == study_id)
    out, seen = [], set()
    for t in g["templates"]:
        for clauses in _template_clauses(t, g):
            if len(clauses) > int(g["max_depth"]):
                continue
            key = " & ".join(clause_key(c) for c in clauses)
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "id": f"atl-{len(out) + 1:05d}",
                "template": t["id"],
                "depth": len(clauses),
                "key": key,
                "clauses": clauses,
                "definition": "; and ".join(clause_words(c, g, study)
                                            for c in clauses),
            })
    return out


def main(argv=None) -> int:
    """Print the count per template; optionally write the candidate list."""
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--csv", type=Path, default=None)
    args = ap.parse_args(argv)
    cands = expand()
    counts: Dict[str, int] = {}
    for c in cands:
        counts[c["template"]] = counts.get(c["template"], 0) + 1
    for t, n in counts.items():
        print(f"{t}: {n}")
    print(f"total: {len(cands)}")
    if args.csv:
        import pandas as pd

        pd.DataFrame([{k: c[k] for k in ("id", "template", "depth", "key",
                                         "definition")} for c in cands]).to_csv(
            args.csv, index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
