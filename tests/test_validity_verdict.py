"""ADR-008 WP-94: verdict function, gate and sentence allow-list.

Sections 7.1, 9.1 and the gate of 5.1 as amended (K_eff, predicted I,
supportability table, P(S given SESOI)). Table test: one row per verdict,
flag, level and eligibility combination, and every boundary (p equal to
a_test counts as passing).
"""

from __future__ import annotations

import ast
import datetime as dt
import pathlib
import random

import numpy as np
import pandas as pd
import pytest

from vedic_astrology_core.stats.exclusion import LimitRecord
from vedic_astrology_core.validity import family as fam
from vedic_astrology_core.validity import gate as G
from vedic_astrology_core.validity import sentences as S
from vedic_astrology_core.validity import verdict as V

A = 0.04 / 20  # a_test of a 20-test first batch
BUNDLE = "b" * 64
V_UNSEEN = {"id": "v1", "confirm_period": {"start": "1987-01-01", "end": "1998-12-31"}, "seen": False}
V_SEEN = {"id": "v_seen", "confirm_period": {"start": "2011-01-01", "end": "2025-12-31"}, "seen": True}
V_FRESH = {"id": "v2", "confirm_period": {"start": "1999-01-01", "end": "2005-12-31"}, "seen": False}


def cal(i):
    import hashlib
    return hashlib.sha256(f"cal-{i}".encode()).hexdigest()


def eligibility_rows():
    """Real Eligibility objects for every row of ADR-008 3.2 (and the control row)."""
    lock = fam.FamilyLock(None, "gold")
    ids = [lock.register(rule_id=f"g.r{i}", version=1, outcome="ret_dem", calendar_hash=cal(i))["test_id"]
           for i in range(20)]
    ctl = lock.register(rule_id="g.tide", version=1, outcome="ret_dem", calendar_hash=cal("tide"),
                        control=True)["test_id"]
    open_el = lock.eligibility(ids[0], V_UNSEEN)
    lock.close_batch(vintage=V_UNSEEN, seal_bundle_sha256=BUNDLE)
    late = lock.register(rule_id="g.late", version=1, outcome="ret_dem", calendar_hash=cal("late"))["test_id"]
    rows = {
        "batch_open": open_el,
        "before_close_unseen": lock.eligibility(ids[0], V_UNSEEN),
        "after_close_same_vintage": lock.eligibility(late, V_UNSEEN),
        "control": lock.eligibility(ctl, V_UNSEEN),
    }
    lock2 = fam.FamilyLock(None, "eq")
    sid = [lock2.register(rule_id=f"e.r{i}", version=1, outcome="rate", calendar_hash=cal(f"e{i}"))["test_id"]
           for i in range(20)]
    lock2.close_batch(vintage=V_SEEN, seal_bundle_sha256=BUNDLE)
    rows["before_close_seen_first_look"] = lock2.eligibility(sid[0], V_SEEN, first_look_calendars=[cal("e0")])
    rows["before_close_seen"] = lock2.eligibility(sid[1], V_SEEN, first_look_calendars=[cal("e0")])
    lock3 = fam.FamilyLock(None, "silver")
    [lock3.register(rule_id=f"s.r{i}", version=1, outcome="ret", calendar_hash=cal(f"s{i}"))["test_id"]
             for i in range(20)]
    lock3.close_batch(vintage=V_UNSEEN, seal_bundle_sha256=BUNDLE)
    b2 = [lock3.register(rule_id=f"s.n{i}", version=1, outcome="ret", calendar_hash=cal(f"n{i}"))["test_id"]
          for i in range(4)]
    lock3.close_batch(vintage=V_FRESH, seal_bundle_sha256=BUNDLE)
    rows["later_batch_fresh"] = lock3.eligibility(b2[0], V_FRESH)
    return rows


ELIG = eligibility_rows()


def lim(value, alpha=0.05):
    if value is None:
        return LimitRecord(alpha=alpha, value=None, unbounded=True, reason="too_few_informative_blocks",
                           scale="difference", informative=3, required_informative=5, k_eff=12.0)
    return LimitRecord(alpha=alpha, value=value, unbounded=False, reason=None, scale="difference",
                       informative=12, required_informative=5, k_eff=12.0)


def base(**kw):
    """A test that meets nothing: verdict N on an unseen first-batch vintage at L4."""
    d = dict(
        level=4, eligibility=ELIG["before_close_unseen"], side="greater",
        can_support=True, can_limit=True, p_sup=0.5, p_opp=0.5, p_ex=0.5,
        explore_same_sign=True, robustness={"R1": True, "R2": True, "R3": True, "R4": True},
        source_published="-0550", confirm_start="1987-01-01", sesoi=0.0025,
        informative_at_sesoi=12, k_eff=12.0, estimate_magnitude=0.003,
        x95=lim(0.002), x_strict=lim(0.0031, A), n_blocks=12,
        support_underpowered=False, p_support_at_sesoi=0.9,
    )
    d.update(kw)
    return V.VerdictInput(**d)


def run(**kw):
    return V.verdict(base(**kw))


# ------------------------------------------------------------------ rows
ROWS = [
    # id, overrides, code, flags that must be present, flags that must be absent
    ("N_default", {}, "N", (), ("limit_only",)),
    ("U_both_fail", dict(can_support=False, can_limit=False, untestable_reason="too_few_episodes"), "U", (), ()),
    ("U_all_dropped", dict(all_blocks_dropped=True, p_sup=0.0), "U", (), ()),
    ("U_beats_S", dict(can_support=False, can_limit=False, p_sup=A), "U", (), ()),
    ("S", dict(p_sup=A / 2), "S", (), ("below_sesoi",)),
    ("S_boundary_equal", dict(p_sup=A), "S", (), ()),
    ("S_just_above", dict(p_sup=A * (1 + 1e-9)), "N", (), ()),
    ("S_explore_sign", dict(p_sup=A, explore_same_sign=False), "N", (), ()),
    ("S_explore_unknown", dict(p_sup=A, explore_same_sign=None), "N", (), ()),
    ("S_R1", dict(p_sup=A, robustness={"R2": True, "R3": True, "R4": True}), "N", ("signal_not_robust",), ()),
    ("S_R2", dict(p_sup=A, robustness={"R1": True, "R2": False, "R3": True, "R4": True}), "N",
     ("signal_not_robust",), ()),
    ("S_R3", dict(p_sup=A, robustness={"R1": True, "R2": True, "R3": False, "R4": True}), "N",
     ("signal_not_robust",), ()),
    ("S_R4", dict(p_sup=A, robustness={"R1": True, "R2": True, "R3": True, "R4": False}), "N",
     ("signal_not_robust",), ()),
    ("S_source_after", dict(p_sup=A, source_published="2010"), "N", ("source_postdates_data",), ()),
    ("S_source_same_year", dict(p_sup=A, source_published=1987), "N", ("source_postdates_data",), ()),
    ("S_source_unknown", dict(p_sup=A, source_published=None), "N", ("source_postdates_data",), ()),
    ("S_source_date_before", dict(p_sup=A, source_published="1986-12-31"), "S", (), ("source_postdates_data",)),
    ("S_limit_only", dict(p_sup=A, can_support=False), "N", ("limit_only",), ()),
    ("S_below_sesoi", dict(p_sup=A, estimate_magnitude=0.001), "S", ("below_sesoi",), ()),
    ("S_and_E_gives_S", dict(p_sup=A, p_ex=A, estimate_magnitude=0.001), "S", ("below_sesoi",), ()),
    ("C", dict(p_opp=A), "C", (), ()),
    ("C_boundary_equal", dict(p_opp=A), "C", (), ()),
    ("C_just_above", dict(p_opp=A * 1.0001), "N", (), ()),
    ("C_two_sided", dict(side="two-sided", p_opp=1e-9), "N", (), ()),
    ("C_disputed", dict(p_opp=1e-9, direction_disputed=True), "N", (), ()),
    ("C_less_side", dict(side="less", p_opp=A), "C", (), ()),
    ("E", dict(p_ex=A), "E", (), ()),
    ("E_boundary_equal", dict(p_ex=A), "E", (), ()),
    ("E_just_above", dict(p_ex=A * 1.0001), "N", (), ()),
    ("E_no_sesoi", dict(p_ex=1e-9, sesoi=None), "N", (), ()),
    ("E_low_information", dict(p_ex=1e-9, informative_at_sesoi=8), "N", (), ()),  # needs ceil(log2(500)) = 9
    ("E_k_eff_low", dict(p_ex=1e-9, k_eff=7.9), "N", (), ()),
    ("E_info_unknown", dict(p_ex=1e-9, informative_at_sesoi=None), "N", (), ()),
    ("C_before_E", dict(p_opp=A, p_ex=A), "C", (), ()),
    ("underpowered", dict(support_underpowered=True, p_support_at_sesoi=0.4), "N", ("support_underpowered",), ()),
    ("known_channel", dict(p_sup=A, known_channel="festival buying"), "S", ("known_channel",), ()),
    ("reading_differs", dict(reading_differs=True, source_name="Brihat Samhita 32"), "N", ("reading_differs",), ()),
    ("project_extension", dict(project_extension=True), "N", ("project_extension",), ()),
    ("tuned", dict(tuned=True), "N", ("tuned",), ()),
    ("pseudo", dict(pseudo_out_of_sample=True), "N", ("pseudo_out_of_sample",), ()),
    ("control_nd", dict(control_not_detected=True), "N", ("control_not_detected",), ()),
    ("recomputed", dict(recomputed_bars_changed=14), "N", ("recomputed_after_confirm",), ()),
]


@pytest.mark.parametrize("name,over,code,present,absent", ROWS, ids=[r[0] for r in ROWS])
def test_verdict_rows(name, over, code, present, absent):
    v = run(**over)
    assert v.code == code, (name, v.conditions)
    for f in present:
        assert f in v.flags
    for f in absent:
        assert f not in v.flags
    assert S.disallowed(v.lines) == []


def test_min_information_boundary_at_a_test():
    from vedic_astrology_core.stats.exclusion import min_informative
    need = min_informative(A)
    assert need == 9  # ceil(log2(1 / 0.002))
    assert run(p_ex=1e-9, informative_at_sesoi=need).code == "E"
    assert run(p_ex=1e-9, informative_at_sesoi=need - 1).code == "N"
    assert run(p_ex=1e-9, k_eff=8.0).code == "E"


# ------------------------------------------------------- eligibility rows
ELIG_TABLE = [
    # row, candidate overrides, expected code, expected flags
    ("before_close_unseen", dict(p_sup=A), "S", ()),
    ("before_close_unseen", dict(p_opp=A), "C", ()),
    ("before_close_unseen", dict(p_ex=A), "E", ()),
    ("before_close_seen_first_look", dict(p_sup=1e-9), "N", ("signal_on_seen_data", "seen_data")),
    ("before_close_seen_first_look", dict(p_opp=1e-9), "N", ("signal_on_seen_data", "seen_data")),
    ("before_close_seen_first_look", dict(p_ex=1e-9), "E", ("seen_data",)),
    ("before_close_seen_first_look", dict(p_sup=1e-9, p_ex=1e-9), "E", ("signal_on_seen_data", "seen_data")),
    ("before_close_seen", dict(p_ex=1e-9), "N", ("seen_data",)),
    ("before_close_seen", dict(p_sup=1e-9), "N", ("signal_on_seen_data",)),
    ("after_close_same_vintage", dict(p_sup=1e-9, p_opp=1e-9, p_ex=1e-9), "N", ("registered_after_unblinding",)),
    ("after_close_same_vintage", dict(), "N", ("registered_after_unblinding",)),
    ("later_batch_fresh", dict(p_sup="a"), "S", ()),
    ("later_batch_fresh", dict(p_ex="a"), "E", ()),
    ("control", dict(p_sup=1e-9), "N", ("control",)),
    ("batch_open", dict(p_sup=1e-9), "N", ("batch_open",)),
]


@pytest.mark.parametrize("row,over,code,flags", ELIG_TABLE)
def test_eligibility_table(row, over, code, flags):
    el = ELIG[row]
    over = {k: (el.a_test if v == "a" else v) for k, v in over.items()}
    v = run(eligibility=el, **over)
    assert v.code == code, v.conditions
    for f in flags:
        assert f in v.flags
    assert v.eligibility_row == el.row
    assert S.disallowed(v.lines) == []


def test_later_batch_uses_its_own_smaller_threshold():
    el = ELIG["later_batch_fresh"]
    assert el.a_test == pytest.approx(0.008 / 4)
    assert run(eligibility=el, p_sup=el.a_test).code == "S"
    assert run(eligibility=el, p_sup=el.a_test * 1.001).code == "N"


# ------------------------------------------------------------------ words
WORDS = {
    (4, "S"): "Supported on this dataset",
    (4, "C"): "Contradicted",
    (4, "E"): "Effect excluded above 0.0031",
    (4, "N"): "Not supported, not excluded",
    (4, "U"): "Untestable on this data",
    (2, "S"): "Encoding supported on this dataset",
    (2, "C"): "Encoding contradicted",
    (2, "E"): "Encoding: steady effect excluded above 0.0031",
    (2, "N"): "Encoding not supported, not excluded",
    (2, "U"): "Encoding untestable on this data",
}
FORCE = {"S": dict(p_sup=A), "C": dict(p_opp=A), "E": dict(p_ex=A), "N": {},
         "U": dict(can_support=False, can_limit=False)}


@pytest.mark.parametrize("level,code", sorted(WORDS))
def test_exact_words_by_level(level, code):
    v = run(level=level, **FORCE[code])
    assert v.code == code
    assert v.words == WORDS[(level, code)]
    assert v.lines[0] == v.words
    if level < 4:
        assert v.lines[1] == ("This result is about the project's encoding of the rule. "
                              "It is not a result about the source text or about astrology.")
    else:
        assert "independent astrologer" in v.lines[1]
    assert "Tested as a single condition, without the cancellations and strength rules the tradition applies." in v.lines


@pytest.mark.parametrize("level", [0, 1, 2, 3, 5, 6])
def test_words_follow_level_threshold(level):
    v = run(level=level)
    assert ("ncoding" in v.words) == (level < 4)


def test_e_cites_x_strict_and_x95_is_per_test():
    v = run(p_ex=A)
    assert "With the family guarantee, a steady effect above 0.0031 is ruled out." in v.lines
    assert "Per-test value: a steady effect above 0.002 is ruled out at the 95% level." in v.lines
    assert "A steady effect at or above the project's threshold is ruled out, with the family guarantee." in v.lines
    assert not any("claimed size" in ln for ln in v.lines)
    assert any(ln.startswith("Ruled out: a steady effect of 0.002") for ln in v.lines)
    assert any(ln.startswith("Not addressed: an effect that appears in fewer than 22%") for ln in v.lines)


def test_unbounded_x_strict_says_no_family_level_bound():
    v = run(x_strict=lim(None, A))
    assert v.code == "N"
    assert "There is no family-level bound." in v.lines
    v = run(x_strict=lim(None, A), x95=lim(None))
    assert "Per-test value: no bound." in v.lines
    assert not any(ln.startswith("Ruled out") for ln in v.lines)
    # E with an unbounded X-strict prints the SESOI it excluded.
    v = run(p_ex=A, x_strict=lim(None, A))
    assert v.words == "Effect excluded above 0.0025"


def test_untestable_reason_sentence():
    v = run(level=2, can_support=False, can_limit=False, untestable_reason="season")
    assert "This dataset cannot test the project's encoding, because it cannot be separated from the season." in v.lines
    v = run(level=4, all_blocks_dropped=True)
    assert "This dataset cannot test this principle, because there is no clean control time." in v.lines


def test_reading_differs_title_and_columns():
    v = run(reading_differs=True, source_name="Brihat Samhita 32", p_sup=A)
    assert v.title == "Project hypothesis derived from Brihat Samhita 32"
    assert "Brihat" not in v.words
    assert v.columns == {"associated": True, "beyond_known_channels": True}
    v = run(p_sup=A, known_channel="festival buying")
    assert v.columns == {"associated": True, "beyond_known_channels": False}
    assert "Tested as an effect beyond what festival buying explains." in v.lines
    with pytest.raises(V.VerdictError):
        run(reading_differs=True)


def test_r2_insufficient_placebos_says_not_possible_not_failed():
    v = run(p_sup=A, robustness={"R1": True, "R2": False, "R3": True, "R4": True}, r2_status="insufficient_placebos")
    msg = ("Placebo-sky check not possible: fewer than 19 distinct placebo calendars on this grid; "
           "Supported is not available.")
    assert v.code == "N" and "signal_not_robust" in v.flags
    assert msg in v.lines and S.is_allowed(msg)
    assert not any("placebo-sky check failed" in ln for ln in v.lines)
    assert S.disallowed(v.lines) == []
    # an ordinary R2 failure keeps the old sentence
    w = run(p_sup=A, robustness={"R1": True, "R2": False, "R3": True, "R4": True}, r2_status="fail")
    assert "A signal was found, but the placebo-sky check failed." in w.lines


def test_flags_are_ordered_and_known():
    v = run(p_sup=A, robustness={}, tuned=True, support_underpowered=True, p_support_at_sesoi=0.5,
            source_published=None, recomputed_bars_changed=3)
    assert list(v.flags) == [f for f in V.FLAGS if f in v.flags]
    assert sum(ln.startswith("A signal was found, but the") for ln in v.lines) == 4
    assert "Support was hardly reachable: the chance of Supported at the project's threshold was 50%." in v.lines


def test_pure_and_byte_identical():
    a, b = run(p_sup=A).to_bytes(), run(p_sup=A).to_bytes()
    assert a == b


def test_bad_inputs_refused():
    with pytest.raises(V.VerdictError):
        run(p_sup=1.5)
    with pytest.raises(V.VerdictError):
        run(side="up")


def test_source_precedes():
    assert V.source_precedes("-0550", "1987-01-01")
    assert V.source_precedes("1986-12-31", dt.date(1987, 1, 1))
    assert not V.source_precedes("1987-01-01", "1987-01-01")
    assert not V.source_precedes(1987, "1987-06-01")
    assert not V.source_precedes("c. 1990", "1987-01-01")
    assert not V.source_precedes(None, "1987-01-01")


def test_recomputation_rule_g05():
    V.check_recomputation(0, False, None)
    V.check_recomputation(0, True, "second reviewer")
    with pytest.raises(V.RecomputationRefused):
        V.check_recomputation(1, False, "x")
    with pytest.raises(V.RecomputationRefused):
        V.check_recomputation(0, True, " ")


# ----------------------------------------------------- 200 random records
def test_render_200_random_records_allow_list_and_encoding():
    rng = random.Random(94)
    rows = list(ELIG)
    for _ in range(200):
        level = rng.randint(0, 6)
        el = ELIG[rng.choice(rows)]
        a = el.a_test or A
        pick = lambda: rng.choice([None, 1e-9, a, a * 1.01, 0.3, 1.0])
        inp = base(
            level=level, eligibility=el, side=rng.choice(["greater", "less", "two-sided"]),
            can_support=rng.random() < 0.7, can_limit=rng.random() < 0.8,
            all_blocks_dropped=rng.random() < 0.05,
            untestable_reason=rng.choice([None] + list(S.UNTESTABLE_REASONS)),
            direction_disputed=rng.random() < 0.2,
            p_sup=pick(), p_opp=pick(), p_ex=pick(),
            explore_same_sign=rng.choice([True, False, None]),
            robustness={k: rng.random() < 0.8 for k in ("R1", "R2", "R3", "R4")},
            source_published=rng.choice([None, "-0550", "2010", 1980, "1986-05-01"]),
            sesoi=rng.choice([None, 0.0025]), informative_at_sesoi=rng.choice([None, 4, 9, 20]),
            k_eff=rng.choice([None, 6.0, 12.0]), estimate_magnitude=rng.choice([None, 0.001, 0.01]),
            x95=rng.choice([None, lim(None), lim(0.002)]), x_strict=rng.choice([None, lim(None, a), lim(0.004, a)]),
            n_blocks=rng.choice([None, 8, 12, 20]),
            support_underpowered=rng.random() < 0.5, p_support_at_sesoi=rng.choice([None, 0.3, 0.95]),
            known_channel=rng.choice([None, "festival buying", "Tides!"]),
            reading_differs=rng.random() < 0.2, source_name="Brihat Samhita",
            project_extension=rng.random() < 0.2, tuned=rng.random() < 0.1,
            control_not_detected=rng.random() < 0.1,
            recomputed_bars_changed=rng.choice([None, 0, 7]),
            attested_after=rng.choice([None, "2027-03-01"]),
        )
        v = V.verdict(inp)
        assert S.disallowed(v.lines) == [], v.lines
        if v.title:
            assert S.is_allowed(v.title)
        if level < 4:
            assert "encoding" in v.words.lower()
            assert any("project's encoding" in ln for ln in v.lines)
        # Eligibility never raises a verdict.
        if v.code in ("S", "C", "E"):
            assert el.allows(v.code)


# -------------------------------------------------------------- sentences
def test_allow_list_refuses_paraphrases_and_bad_slots():
    for bad in ("The principle was debunked.", "Astrology fails.", "Proven on this dataset",
                "Supported on this dataset!", "Effect excluded above lots",
                "Tested as an effect beyond what Festival Buying explains.",
                "Effect excluded above 2 for gold"):
        assert not S.is_allowed(bad), bad
    with pytest.raises(S.SentenceError):
        S.render("verdict.l4.E", x="large")
    with pytest.raises(S.SentenceError):
        S.render("no.such.sentence")
    with pytest.raises(S.SentenceError):
        S.render("explain.l4.U", reason="astrology is false")
    assert S.match("Encoding contradicted") == "verdict.enc.C"
    assert S.disallowed(["", "Contradicted", "debunked"]) == ["debunked"]


def test_every_verdict_word_below_l4_says_encoding():
    for key, tpl in S.TEMPLATES.items():
        if key.startswith("verdict.enc."):
            assert "ncoding" in tpl
    for f in V.FLAGS:
        assert f in S.FLAG_SENTENCES


def test_exclusion_card_lines_are_allowed():
    from vedic_astrology_core.stats.exclusion import card_lines
    for k in (8, 12, 20):
        for x in (0.00123, 1.5, 2.0, 1234.0):
            for ln in card_lines(lim(x), k):
                assert S.is_allowed(ln), ln


# ------------------------------------------------------------------- gate
N_BARS = 2400
DATES = pd.date_range("1990-01-01", periods=N_BARS, freq="D")
CONFIRM = np.arange(N_BARS) >= 1200


def periodic(active, gap, start=7, n=N_BARS):
    c = np.zeros(n, dtype=bool)
    for s in range(start, n, active + gap):
        c[s:s + active] = True
    return c


def spec(**kw):
    d = dict(test_id="gold.t1@v1/primary/ret_dem", side="greater", outcome_type="continuous", a_test=A,
             merge_gap=1, sesoi=0.5, noise_sd=1.0, level=2, power_reps=60, plan_seed=7)
    d.update(kw)
    return G.GateSpec(**d)


def test_gate_reads_no_outcome():
    import inspect
    sig = inspect.signature(G.run_gate)
    params = list(sig.parameters)
    # `available` is the dataset's declared missing-bar mask (grid inventory, no value read).
    assert params == ["calendar", "dates", "confirm", "spec", "available"]
    assert sig.parameters["available"].kind is inspect.Parameter.KEYWORD_ONLY
    assert not any("outcome" in f for f in G.GateSpec.__dataclass_fields__ if f != "outcome_type")


def test_gate_k_eff_attainable_p_and_power():
    g = G.run_gate(periodic(8, 32), DATES, CONFIRM, spec())
    assert g.can_support and g.can_limit and not g.untestable
    assert g.confirm["k_eff"] >= 8 and g.full["k_eff"] >= g.confirm["k_eff"]
    assert g.confirm["alternative"] == "greater"
    assert g.blocks_needed_support == 9
    assert g.predicted_informative == g.full["n_used"]
    assert g.p_support_at_sesoi is not None and g.p_support_at_sesoi >= 0.8
    assert not g.support_underpowered
    # A tiny SESOI: support is hardly reachable (A-07, W4).
    weak = G.run_gate(periodic(8, 32), DATES, CONFIRM, spec(sesoi=0.02))
    assert weak.can_support and weak.support_underpowered and weak.p_support_at_sesoi < 0.8
    # No noise model: P(S) unknown, flag set.
    unk = G.run_gate(periodic(8, 32), DATES, CONFIRM, spec(noise_sd=None))
    assert unk.p_support_at_sesoi is None and unk.support_underpowered


def test_gate_hash_is_deterministic_and_matches_bytes():
    a = G.run_gate(periodic(8, 32), DATES, CONFIRM, spec())
    b = G.run_gate(periodic(8, 32), DATES, CONFIRM, spec())
    assert a.to_bytes() == b.to_bytes() and a.gate_hash == b.gate_hash


def test_gate_g5_at_a_test_and_limit_only():
    # 8 episodes in the confirm half: K_eff 8 but 2^-8 > a_test, so it can only limit.
    c = np.zeros(N_BARS, dtype=bool)
    for s in range(30, 1200, 100):
        c[s:s + 10] = True
    for s in range(1230, N_BARS, 150):
        c[s:s + 10] = True
    g = G.run_gate(c, DATES, CONFIRM, spec())
    assert g.confirm["n_used"] == 8
    assert not g.can_support and "p_not_attainable" in g.support_failed
    assert g.can_limit and g.category == "limit_only"
    assert g.p_support_at_sesoi == 0.0 and g.support_underpowered


def test_gate_short_gap_calendar_is_untestable():
    g = G.run_gate(periodic(20, 5), DATES, CONFIRM, spec())
    assert g.untestable and not g.can_support and not g.can_limit
    assert g.untestable_reason == "no_clean_control"
    assert g.full["drop_counts"]["unbalanced"] == g.full["n_episodes"]


def test_gate_common_failures():
    for kw, reason in ((dict(encoded=False), "not_encoded"), (dict(level=1), "not_operationalised"),
                       (dict(data_grade="C"), "data_quality"), (dict(national_chart_ok=False), "chart_time")):
        g = G.run_gate(periodic(8, 32), DATES, CONFIRM, spec(**kw))
        assert g.untestable and g.untestable_reason == reason


def test_gate_events_predicted_information_and_expected_counts():
    rare = G.run_gate(periodic(8, 32), DATES, CONFIRM,
                      spec(outcome_type="events", sesoi=2.0, base_rate=0.002, noise_sd=None))
    assert rare.predicted_informative < 5
    assert "too_little_information" in rare.limit_failed and "too_few_events" in rare.support_failed
    assert rare.untestable
    common = G.run_gate(periodic(8, 32), DATES, CONFIRM,
                        spec(outcome_type="events", sesoi=2.0, base_rate=0.5, noise_sd=None))
    assert common.can_limit and common.expected_events["full_active"] >= 5
    assert common.predicted_informative > 20
    with pytest.raises(G.GateError):
        spec(outcome_type="events", base_rate=None, sesoi=2.0).check()


def test_gate_no_sesoi_cannot_limit():
    g = G.run_gate(periodic(8, 32), DATES, CONFIRM, spec(sesoi=None))
    assert "no_sesoi" in g.limit_failed and g.can_support and not g.can_limit
    assert g.p_support_at_sesoi is None and g.support_underpowered


def test_gate_sun_in_sign_is_untestable_with_season_reason():
    dates = pd.date_range("1968-01-01", "1998-12-31", freq="D")
    c = (dates.day_of_year >= 105) & (dates.day_of_year < 136)  # one sign of the Sun, every year
    conf = dates >= pd.Timestamp("1987-01-01")
    g = G.run_gate(np.asarray(c), dates, np.asarray(conf), spec(merge_gap=1))
    assert g.season["season_linked"]
    assert g.untestable and g.untestable_reason == "season"
    v = run(level=2, can_support=g.can_support, can_limit=g.can_limit, all_blocks_dropped=g.all_blocks_dropped,
            untestable_reason=g.untestable_reason)
    assert v.code == "U"
    assert "This dataset cannot test the project's encoding, because it cannot be separated from the season." in v.lines


def test_supportability_table_matches_gate():
    gates = [
        G.run_gate(periodic(8, 32), DATES, CONFIRM, spec(test_id="a")),
        G.run_gate(periodic(20, 5), DATES, CONFIRM, spec(test_id="b")),
    ]
    c = np.zeros(N_BARS, dtype=bool)
    for s in list(range(30, 1200, 100)) + list(range(1230, N_BARS, 150)):
        c[s:s + 10] = True
    gates.append(G.run_gate(c, DATES, CONFIRM, spec(test_id="c")))
    t = G.supportability_table(gates)
    assert t["counts"] == {"support": 1, "limit_only": 1, "untestable": 1}
    assert t["a_test"] == A
    assert [r["category"] for r in t["rows"]] == [g.category for g in gates]


def test_gate_and_primary_test_agree_on_side_and_blocks():
    from vedic_astrology_core.stats import blocks as B
    from vedic_astrology_core.stats import season as Z
    c = periodic(8, 32)
    g = G.run_gate(c, DATES, CONFIRM, spec())
    # The gate passes the plan seed as side_seed (A2); the test builds the same design.
    sd = Z.control_design(c, DATES, merge_gap=1, available=CONFIRM, side_seed=7)
    y = np.random.default_rng(1).normal(size=N_BARS)
    res = B.primary_test(sd.blocks, y, alternative="greater", outcome_type="continuous",
                         rng=fam.stream_rng(7, "t", "signflip"))
    gs = res.gate_summary()
    for k in ("design_id", "alternative", "n_used", "n_dropped", "k_eff", "p_min"):
        assert gs[k] == g.confirm[k]


def test_gate_uses_the_plan_seed_as_side_seed_a2():
    from vedic_astrology_core.stats import blocks as B
    from vedic_astrology_core.stats import season as Z
    c = periodic(1, 9)  # single-day episodes: A1 drops every block, A2 keeps them
    a1 = Z.control_design(c, DATES, merge_gap=0)
    assert a1.blocks.n_used == 0
    g = G.run_gate(c, DATES, CONFIRM, spec(merge_gap=0))
    assert g.full["n_used"] == g.full["n_episodes"] and g.can_support
    sd = Z.control_design(c, DATES, merge_gap=0, available=CONFIRM, side_seed=7)
    y = np.random.default_rng(2).normal(size=N_BARS)
    res = B.primary_test(sd.blocks, y, alternative="greater", outcome_type="continuous",
                         rng=fam.stream_rng(7, "t", "signflip"))
    for k in ("design_id", "alternative", "n_used", "n_dropped", "k_eff", "p_min"):
        assert res.gate_summary()[k] == g.confirm[k]  # S-15 with A2 on
    # The seed decides the starting side; another seed, another design id.
    other = G.run_gate(c, DATES, CONFIRM, spec(merge_gap=0, plan_seed=8))
    assert other.full["n_used"] == g.full["n_used"]
    if B.start_side(8) != B.start_side(7):
        assert other.full["design_id"] != g.full["design_id"]


def test_gate_takes_the_missing_bar_mask():
    from vedic_astrology_core.stats import blocks as B
    from vedic_astrology_core.stats import season as Z
    c = periodic(8, 32)
    avail = np.ones(N_BARS, dtype=bool)
    avail[1500:1530] = False  # a gap in the source, known from its inventory
    g = G.run_gate(c, DATES, CONFIRM, spec(), available=avail)
    plain = G.run_gate(c, DATES, CONFIRM, spec())
    assert g.full["design_id"] != plain.full["design_id"]
    sd = Z.control_design(c, DATES, merge_gap=1, available=CONFIRM & avail, side_seed=7)
    y = np.random.default_rng(3).normal(size=N_BARS)
    y[~avail] = np.nan
    res = B.primary_test(sd.blocks, y, alternative="greater", outcome_type="continuous",
                         rng=fam.stream_rng(7, "t", "signflip"))
    assert res.gate_summary()["design_id"] == g.confirm["design_id"]
    # An all-true mask is the same design as no mask.
    assert G.run_gate(c, DATES, CONFIRM, spec(), available=np.ones(N_BARS, bool)).gate_hash == plain.gate_hash
    with pytest.raises(G.GateError):
        G.run_gate(c, DATES, CONFIRM, spec(), available=np.ones(N_BARS - 1, bool))


# ------------------------------------------------------------- imports
def test_validity_does_not_import_deprecated_functions():
    root = pathlib.Path(G.__file__).parent
    for name in ("gate.py", "verdict.py", "robustness.py", "sentences.py"):
        tree = ast.parse((root / name).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                names = {a.name for a in node.names}
                assert not names & {"episode_equivalence", "upper_limit_episodes"}
                assert not (node.module or "").endswith("equivalence")
            if isinstance(node, ast.Import):
                assert not any(a.name.endswith("equivalence") for a in node.names)
