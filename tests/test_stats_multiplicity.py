"""Tests for BH, BY and Bonferroni corrections and the family helper."""

import numpy as np
import pandas as pd
import pytest
from statsmodels.stats.multitest import multipletests

from vedic_astrology_core.stats.multiplicity import (
    adjust,
    benjamini_hochberg,
    benjamini_yekutieli,
    bonferroni,
    family,
)


def test_bh_known_answer():
    """Hand-computed BH q-values."""
    q = benjamini_hochberg([0.01, 0.04, 0.03, 0.005])
    np.testing.assert_allclose(q, [0.02, 0.04, 0.04, 0.02])


def test_by_is_bh_times_harmonic_number():
    """BY equals BH scaled by sum(1/i), capped at 1."""
    p = np.array([0.001, 0.01, 0.02, 0.2])
    c = 1 + 1 / 2 + 1 / 3 + 1 / 4
    np.testing.assert_allclose(
        benjamini_yekutieli(p), np.minimum(1, benjamini_hochberg(p) * c)
    )


@pytest.mark.parametrize(
    "ours,theirs", [("bh", "fdr_bh"), ("by", "fdr_by"), ("bonferroni", "bonferroni")]
)
def test_matches_statsmodels(ours, theirs):
    """Agreement with statsmodels on random p-values."""
    p = np.random.default_rng(9).uniform(size=60) ** 3
    np.testing.assert_allclose(adjust(p, ours), multipletests(p, method=theirs)[1])


def test_bonferroni_caps_at_one():
    """Bonferroni never exceeds 1."""
    np.testing.assert_allclose(bonferroni([0.5, 0.01]), [1.0, 0.02])


def test_family_adds_columns_and_rejects_duplicates():
    """One correction across all (rule, target) pairs."""
    df = pd.DataFrame(
        {
            "rule": ["a", "a", "b"],
            "target": ["x", "y", "x"],
            "p_value": [0.001, 0.5, 0.02],
        }
    )
    out = family(df, method="bh")
    assert list(out["family_size"]) == [3, 3, 3]
    assert out["significant"].tolist() == [True, False, True]
    with pytest.raises(ValueError):
        family(pd.concat([df, df.iloc[:1]]))
    with pytest.raises(ValueError):
        adjust([0.1, np.nan])
    with pytest.raises(ValueError):
        adjust([0.1], "holm")
