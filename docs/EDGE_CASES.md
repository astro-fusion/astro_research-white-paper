# ⚠️ Edge Cases Catalog

This document catalogs **known edge cases** in the Vedic Astrology Research Platform — situations where calculations behave in non-obvious ways near boundary conditions.

> **Found a new edge case?** Please [open an issue](https://github.com/astro-fusion/astro_research-white-paper/issues/new?template=bug_report.yml), then add it here and write a test.
> **This document is a living reference** — every edge case listed here should have a corresponding test in `tests/`.

---

## 📋 Table of Contents

1. [Planetary Degree Edge Cases](#1-planetary-degree-edge-cases)
2. [Ayanamsa Boundary Cases](#2-ayanamsa-boundary-cases)
3. [Retrograde Motion Cases](#3-retrograde-motion-cases)
4. [Date & Time Edge Cases](#4-date--time-edge-cases)
5. [Numerology Boundary Cases](#5-numerology-boundary-cases)
6. [Data / Input Edge Cases](#6-data--input-edge-cases)
7. [Known Limitations](#7-known-limitations)

---

## 1. Planetary Degree Edge Cases

### 1.1 Exaltation Point vs. Exaltation Sign

A planet in its **exaltation sign** gets a high dignity score, but the **exact exaltation point** (specific degree) gets the maximum score.

| Planet  | Exaltation Sign | Exact Exaltation Degree |
| ------- | --------------- | ----------------------- |
| Sun     | Aries           | 10°                     |
| Moon    | Taurus          | 3°                      |
| Mars    | Capricorn       | 28°                     |
| Mercury | Virgo           | 15°                     |
| Jupiter | Cancer          | 5°                      |
| Venus   | Pisces          | 27°                     |
| Saturn  | Libra           | 20°                     |

```python
# Edge case: Mars at exactly 28° Capricorn = MAX score
result = calculate_planetary_dignity("Mars", "Capricorn", 28.0)
assert result["score"] == 100.0

# Mars at 27.9° Capricorn = near-max but NOT at exact point
result = calculate_planetary_dignity("Mars", "Capricorn", 27.9)
assert result["score"] < 100.0  # Still exalted, but not peak
```

**Test coverage**: `tests/test_dignity.py::TestPlanetaryDignity::test_exact_exaltation_point`

---

### 1.2 Sign Boundary (29°59' → 0°00')

When a planet is at the very edge of a sign (e.g., 29°59'59" Aries), it is still in Aries. The next second (30°00') places it in Taurus.

```python
# 29.999° Aries → still Aries
assert get_sign_for_degree(29.999) == "Aries"

# 30.000° → Taurus
assert get_sign_for_degree(30.0) == "Taurus"
```

**⚠️ Risk**: Floating-point precision in degree calculations near sign boundaries. Always use `>= 30.0` (not `== 30.0`) for sign transitions.

**Test coverage**: `tests/test_astrology.py::TestSignBoundary`

---

### 1.3 Combust Planet Near Exaltation

A planet that is **both combust (too close to Sun) and in its exaltation sign** presents a conflict: classical texts disagree on which rule takes precedence.

**Current behavior**: Dignity score uses exaltation, but a `combustion_penalty` is applied.

**Open question**: Should severe combustion override exaltation? This is an open research question — see [Discussion #TBD](https://github.com/astro-fusion/astro_research-white-paper/discussions).

---

## 2. Ayanamsa Boundary Cases

### 2.1 Tropical-to-Sidereal Conversion at Year 285 CE

The Lahiri Ayanamsa is approximately 0° at ~285 CE. For ancient dates (BCE), ayanamsa is negative.

```python
# 285 CE: ayanamsa ≈ 0
ayanamsa = calculate_lahiri_ayanamsa(date="0285-01-01")
assert abs(ayanamsa) < 1.0  # Very close to zero

# Ancient date: negative ayanamsa
ayanamsa = calculate_lahiri_ayanamsa(date="0001-01-01")
assert ayanamsa < 0
```

**Test coverage**: `tests/test_astrology.py::TestAyanamsa::test_ancient_date_ayanamsa`

---

### 2.2 Ayanamsa Accumulation Per Year

The ayanamsa increases by approximately **50.3 arcseconds per year**. For precision, always use the actual calculation, not a linear approximation.

---

## 3. Retrograde Motion Cases

### 3.1 Station-Retrograde and Station-Direct Days

On the exact day a planet **turns retrograde** or **turns direct**, its daily motion is nearly zero. Velocity-based direction detection (`daily_motion > 0`) can be unreliable on these boundary days.

```python
# Saturn station retrograde (example date)
is_retro = is_retrograde("Saturn", date="2023-06-17")
# ⚠️ Velocity ≈ 0 on this day — result may differ by engine version
```

**Current mitigation**: Use a 3-day window average to determine direction near stations.

**Test coverage**: `tests/test_astrology.py::TestRetrograde::test_station_day`

---

### 3.2 Mercury Retrograde Combust Sequence

Mercury retrogrades while combust (within 3° of the Sun) more often than other planets. In this state, both `is_retrograde` and `is_combust` are True simultaneously.

---

## 4. Date & Time Edge Cases

### 4.1 Daylight Saving Time (DST) Transitions

Birth times during DST transitions (e.g., 2:30 AM when clocks skip to 3:00 AM) may be ambiguous.

```python
# 2:30 AM during spring-forward DST → does not exist!
# These times should raise an error, not silently compute
with pytest.raises(AmbiguousTimeError):
    VedicChart("1990-04-01", "02:30", timezone="America/New_York")
```

**Test coverage**: `tests/test_astrology.py::TestDSTHandling`

---

### 4.2 Date at Midnight (Boundary of Vedic Day)

In Vedic tradition, the **day boundary** is often considered **sunrise**, not midnight. For birth times between midnight and sunrise, the Vedic date may differ from the calendar date.

---

### 4.3 Historical Julian Calendar Dates

Dates before 1582-10-15 use the **Julian calendar**, but `datetime` and most time libraries assume the Gregorian calendar. Swiss Ephemeris handles this correctly internally, but be careful when parsing user-supplied historical dates.

---

## 5. Numerology Boundary Cases

### 5.1 Date Reduction to 11, 22, 33 (Master Numbers)

Master numbers `11`, `22`, `33` may or may not be reduced further, depending on the tradition.

```python
# Birth date summing to 11: is the result 11 or 2?
result = calculate_mulanka("1979-11-29")  # 1+9+7+9+1+1+2+9 = 39 → 3+9=12 → 1+2=3
# vs.
result = calculate_bhagyanka("1979-02-11")  # Sum = 1+1 = 11 (master number)
```

**Current decision**: The library preserves master numbers. Pass `reduce_master_numbers=True` to force full reduction.

---

### 5.2 Zero in Lo Shu Grid

A digit from 1–9 may be **absent** from a Lo Shu grid (no positions), which is a significant reading. The grid should represent this as an empty list, not `0`.

```python
grid = build_lo_shu_grid("1984-08-27")
assert grid.get("5") == []  # May be empty — not 0
```

---

## 6. Data / Input Edge Cases

### 6.1 High-Latitude Birth Locations

Above ~66.5°N or below ~66.5°S (Arctic/Antarctic circles), the Sun may not rise or set for extended periods. House calculations that depend on sunrise/sunset will fail or produce undefined results.

**Current behavior**: Raises `HighLatitudeError` for latitudes beyond ±66°.

---

### 6.2 Unknown Birth Time

Many historical records lack birth times. The library should gracefully handle charts computed at noon (common convention for unknown times).

```python
# Unknown birth time → noon chart
chart = VedicChart("1984-08-27", birth_time=None)
# Should not raise; should use 12:00 noon as default
```

---

## 7. Known Limitations

| Limitation                            | Details                           | Workaround                                      |
| ------------------------------------- | --------------------------------- | ----------------------------------------------- |
| Swiss Ephemeris date range            | Accurate from 2000 BCE to 3000 CE | Use historical approximations for earlier dates |
| No Krishnamurti Paddhati (KP) support | Only Lahiri ayanamsa implemented  | Open feature request if needed                  |
| No divisional charts (Navamsha, etc.) | Only Rashi (D1) chart supported   | Planned for v0.3                                |
| Arabic Parts / Lots                   | Not implemented                   | Opens for contribution                          |

---

## 🙋 Contributing New Edge Cases

1. Document the edge case in this file under the appropriate section
2. Add a failing test (or a test that now passes after a fix) in the relevant test file
3. Fix the library code if you can — or open a PR with just the test

```bash
# Example: adding a new edge case test
pytest tests/test_dignity.py::TestPlanetaryDignity::test_your_new_edge_case -v
```
