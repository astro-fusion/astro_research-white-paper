"""Geometric (longitude and declination) aspects in vedic_astrology_core.

Ported from the retired second engine's ``aspect_matrix.py`` (WP-7). Graha
drishti, the whole-sign Vedic aspect, lives in the rules predicates; these
are the orb-based geometric aspects that papers 03 and 05 describe.
"""

import numpy as np
import pytest
from vedic_astrology_core.astrology.aspects import (
    ASPECT_CATALOGUE,
    MEAN_OBLIQUITY_J2000,
    AspectHit,
    compute_aspect_matrix,
    compute_parallel_matrix,
    detect_aspects,
    detect_out_of_bounds,
)


def test_matrix_is_minimum_arc_and_symmetric():
    """Arcs wrap across 0 and never exceed 180 degrees."""
    a = compute_aspect_matrix(np.array([0.0, 90.0, 350.0, 180.0]))
    assert a.shape == (4, 4)
    assert np.allclose(np.diag(a), 0.0)
    assert np.allclose(a, a.T)
    assert a[0, 2] == pytest.approx(10.0)  # wraps across 0
    assert a[1, 2] == pytest.approx(100.0)
    assert a[0, 3] == pytest.approx(180.0)


def test_detects_trine_across_zero_with_signed_orb():
    """355 and 117 are 122 degrees apart: a trine, orb +2."""
    hits = detect_aspects(np.array([355.0, 117.0]), ["Sun", "Moon"])
    assert hits == [AspectHit(0, 1, "trine", pytest.approx(2.0))]


def test_orb_override_and_exclusivity():
    """A 65-degree arc is a sextile at orb 6 but not at orb 4."""
    lons = np.array([0.0, 65.0])
    assert [h.aspect_name for h in detect_aspects(lons, ["a", "b"])] == ["sextile"]
    assert detect_aspects(lons, ["a", "b"], orb_override={"sextile": 4.0}) == []


def test_body_names_length_checked():
    """Names and longitudes must pair up."""
    with pytest.raises(ValueError):
        detect_aspects(np.array([0.0, 1.0]), ["only-one"])


def test_catalogue_is_ptolemaic_plus_minor():
    """Wide orbs only for the five Ptolemaic aspects."""
    majors = {k for k, (_, orb) in ASPECT_CATALOGUE.items() if orb >= 6.0}
    assert majors == {"conjunction", "sextile", "square", "trine", "opposition"}


def test_out_of_bounds_uses_obliquity():
    """Out of bounds means |declination| above the obliquity."""
    mask = detect_out_of_bounds(np.array([23.0, 24.0, -25.1, -23.4]))
    assert mask.tolist() == [False, True, True, False]
    assert MEAN_OBLIQUITY_J2000 == pytest.approx(23.4393, abs=1e-4)


def test_parallel_and_contra_parallel():
    """Parallels by equal, contra-parallels by opposite declination."""
    par, cpar = compute_parallel_matrix(np.array([10.0, 10.5, -10.2, 0.0]))
    assert par[0, 1] and par[1, 0] and not par[0, 0]
    assert not par[0, 2]
    assert cpar[0, 2] and cpar[1, 2] and not cpar[0, 1]
    assert not cpar[3, 3]  # diagonal excluded even at declination 0
