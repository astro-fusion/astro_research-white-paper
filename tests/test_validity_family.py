"""ADR-008 WP-88: closed batches, fixed thresholds, eligibility and seeds.

Cases F1 to F7 of ADR-008 section 3.6 (F8 runs through the whole pipeline in
the certificate suite, WP-98), the rules of section 3.2, section 3.4 and 3.5,
the lineage id with calendar hash and the use: parent pin (G-04).
"""

from __future__ import annotations

import hashlib
import json
import math

import numpy as np
import pytest

from vedic_astrology_core.validity import family as fam
from vedic_astrology_core.validity.calibration import clopper_pearson_upper

BUNDLE = "b" * 64
V1 = {"id": "gold_monthly_v1", "confirm_period": {"start": "1987-01", "end": "1998-12"}, "seen": False}
V1_SEEN = {"id": "eq_v1", "confirm_period": {"start": "2011-01-01", "end": "2025-12-31"}, "seen": True}
V2 = {"id": "gold_monthly_v2", "confirm_period": {"start": "1999-01", "end": "2005-12"}, "seen": False}


def cal(i) -> str:
    return hashlib.sha256(f"calendar-{i}".encode()).hexdigest()


def new_lock(n=43, path=None, domain="gold"):
    lock = fam.FamilyLock(path, domain)
    ids = [lock.register(rule_id=f"gold.rule{i}", version=1, outcome="ret_lbma_usd", calendar_hash=cal(i))["test_id"]
           for i in range(n)]
    return lock, ids


def run(lock, ids, pvals, vintage):
    """Toy run: threshold record, eligibility and verdict per test (canonical bytes)."""
    out = {}
    for t in ids:
        el = lock.eligibility(t, vintage)
        p = float(pvals[t])
        cand = "S" if el.a_test is not None and fam.passes(p, el.a_test) else "N"
        verdict, flags = fam.limit_verdict(cand, el)
        rec = dict(lock.test_record(t), p_support=p, verdict=verdict, flags=list(flags))
        out[t] = fam.canonical_bytes(rec)
    return out


def results_file(records, ids):
    return fam.canonical_bytes([json.loads(records[t]) for t in ids])


# ------------------------------------------------------------------ F5
def test_f5_alpha_table_sums_to_at_most_005_and_a_test_is_exact():
    table = fam.alpha_table(50)
    assert table[:3] == [0.04, 0.008, 0.0016]
    assert math.fsum(table) <= 0.05 and sum(table) <= 0.05
    assert all(a > b for a, b in zip(table, table[1:]))
    lock, ids = new_lock(43)
    close = lock.close_batch(vintage=V1, seal_bundle_sha256=BUNDLE)
    assert close["n_b"] == 43 and close["alpha_b"] == 0.04
    assert close["a_test"] == 0.04 / 43  # to the last bit
    assert lock.test_record(ids[0])["a_test"] == fam.alpha_for_batch(1) / 43
    for b, n in [(2, 1), (3, 7), (7, 60)]:
        assert fam.a_test_for(fam.alpha_for_batch(b), n) == table[b - 1] / n


def test_alpha_schedule_must_respect_005_and_stays_fixed():
    with pytest.raises(fam.FamilyError):
        fam.alpha_for_batch(1, first=0.05, ratio=0.2)  # 0.0625 in total
    with pytest.raises(fam.FamilyError):
        fam.alpha_for_batch(0)
    lock, _ = new_lock(3)
    lock.close_batch(vintage=V1, seal_bundle_sha256=BUNDLE)
    lock.register(rule_id="gold.new", version=1, outcome="ret_lbma_usd", calendar_hash=cal("new"))
    with pytest.raises(fam.FamilyError, match="schedule"):
        lock.close_batch(vintage=V2, seal_bundle_sha256=BUNDLE, alpha_first="0.025", alpha_ratio="0.5")
    close2 = lock.close_batch(vintage=V2, seal_bundle_sha256=BUNDLE)
    assert close2["alpha_b"] == 0.008 and close2["a_test"] == 0.008


def test_passes_boundary_counts_as_passing():
    assert fam.passes(0.001, 0.001)
    assert not fam.passes(0.0010000001, 0.001)
    with pytest.raises(fam.FamilyError):
        fam.passes(1.5, 0.01)


# ------------------------------------------------------------------ F1
def test_f1_other_p_values_never_move_a_verdict_or_record():
    lock, ids = new_lock(43)
    lock.close_batch(vintage=V1, seal_bundle_sha256=BUNDLE)
    rng = np.random.default_rng(1)
    base_p = {t: float(p) for t, p in zip(ids, rng.random(43))}
    # put a few near the threshold, including exactly at it
    a = 0.04 / 43
    base_p[ids[0]], base_p[ids[1]], base_p[ids[2]] = a, a * 1.0001, a * 0.5
    base = run(lock, ids, base_p, V1)
    assert json.loads(base[ids[0]])["verdict"] == "S"
    assert json.loads(base[ids[1]])["verdict"] == "N"
    for j in ids:
        changed = dict(base_p, **{j: 1e-9})
        again = run(lock, ids, changed, V1)
        for t in ids:
            if t != j:
                assert again[t] == base[t]


# ------------------------------------------------------------------ F2
def test_f2_adding_tests_leaves_batch_one_byte_identical(tmp_path):
    path = tmp_path / "family.lock.jsonl"
    lock, ids = new_lock(43, path=path)
    lock.close_batch(vintage=V1, seal_bundle_sha256=BUNDLE)
    rng = np.random.default_rng(2)
    pv = {t: float(p) for t, p in zip(ids, rng.random(43))}
    first = results_file(run(lock, ids, pv, V1), ids)
    lock.record_batch_results(1, first)

    new = [lock.register(rule_id=f"gold.late{k}", version=1, outcome="ret_lbma_usd",
                         calendar_hash=cal(f"late{k}"))["test_id"] for k in range(5)]
    lock = fam.FamilyLock(path, "gold")  # reopen from disk
    again = results_file(run(lock, ids, pv, V1), ids)
    assert again == first
    lock.verify_batch_results(1, again)
    assert lock.record_batch_results(1, again)["results_sha256"] == hashlib.sha256(first).hexdigest()
    with pytest.raises(fam.ClosedBatchChangedError):
        lock.verify_batch_results(1, first.replace(b'"verdict":"N"', b'"verdict":"S"', 1))
    with pytest.raises(fam.ClosedBatchChangedError):
        lock.record_batch_results(1, first + b" ")

    for t in new:
        assert lock.test(t)["batch"] == 2
        el = lock.eligibility(t, V1)
        assert el.flags == ("registered_after_unblinding",) and el.numbers == "descriptive"
        assert fam.limit_verdict("S", el) == ("N", ("registered_after_unblinding",))
        assert fam.limit_verdict("E", el)[0] == "N"
    assert lock.batch_tests(1) == ids and lock.batch_tests(2) == new


# ------------------------------------------------------------- F3, F4
def test_f3_clone_attack_on_the_same_vintage():
    r = fam.clone_attack_case(2000, fresh=False, seed=3)
    assert r["copies_false_s_old_vintage"] == 0
    assert r["copies_refused"] == 2000 * 8  # 5 renamed + 3 variants over the cap
    assert clopper_pearson_upper(r["families_any_false_s"], r["families"]) <= 0.06


def test_f4_clone_attack_with_a_fresh_vintage():
    r = fam.clone_attack_case(2000, fresh=True, seed=4)
    assert r["copies_false_s_old_vintage"] == 0
    assert clopper_pearson_upper(r["families_any_false_s"], r["families"]) <= 0.06


def test_renamed_copy_is_refused_and_variants_are_capped():
    lock, ids = new_lock(2)
    with pytest.raises(fam.DuplicateCalendarError):
        lock.register(rule_id="gold.renamed", version=1, outcome="ret_lbma_usd", calendar_hash=cal(0))
    # same calendar, other outcome is another test
    lock.register(rule_id="gold.rule0", version=1, outcome="absret_lbma_usd", calendar_hash=cal(0))
    for k in range(3):
        lock.register(rule_id="gold.rule0", version=1, outcome="ret_lbma_usd", variant=f"orb{k}",
                      calendar_hash=cal(f"v{k}"))
    with pytest.raises(fam.TooManyVariantsError):
        lock.register(rule_id="gold.rule0", version=1, outcome="ret_lbma_usd", variant="orb9",
                      calendar_hash=cal("v9"))
    # a variant already counted may take another outcome
    lock.register(rule_id="gold.rule0", version=1, outcome="absret_lbma_usd", variant="orb0",
                  calendar_hash=cal("v0"))
    with pytest.raises(fam.DuplicateTestError):
        lock.register(rule_id="gold.rule1", version=1, outcome="ret_lbma_usd", calendar_hash=cal("x"))
    # every variant takes its own share of alpha
    close = lock.close_batch(vintage=V1, seal_bundle_sha256=BUNDLE)
    assert close["n_b"] == 7 and close["a_test"] == 0.04 / 7


# ------------------------------------------------------------------ F6
def _toy_signflip_p(plan_seed, test_id, d):
    rng = fam.stream_rng(plan_seed, test_id, "signflip")
    signs = rng.choice((-1.0, 1.0), size=(999, d.size))
    t_obs = d.mean()
    return (1 + int(np.sum((signs * d).mean(axis=1) >= t_obs))) / 1000


def test_f6_seeds_adding_a_test_changes_no_other_number():
    data = {t: np.random.default_rng(i).normal(size=12) for i, t in enumerate("ABC")}
    one = {t: _toy_signflip_p(7, t, data[t]) for t in ["A", "B"]}
    two = {t: _toy_signflip_p(7, t, data[t]) for t in ["C", "B", "A"]}
    assert all(repr(one[t]) == repr(two[t]) for t in "AB")
    expect = int.from_bytes(hashlib.sha256(b"7|A|signflip").digest()[:8], "big")
    assert fam.stream_seed(7, "A", "signflip") == expect
    seeds = {fam.stream_seed("plan", "A", p) for p in fam.SEED_PURPOSES}
    assert len(seeds) == 4
    assert fam.stream_seed("plan", "A", "signflip") != fam.stream_seed("plan", "B", "signflip")
    with pytest.raises(fam.FamilyError):
        fam.stream_seed(7, "A", "shared")


# ------------------------------------------------------------------ F7
def test_f7_eligibility_table_every_row():
    lock = fam.FamilyLock(None, "earthquake")
    old = lock.register(rule_id="eq.old", version=1, outcome="rate", calendar_hash=cal("old"))["test_id"]
    newcal = lock.register(rule_id="eq.new", version=1, outcome="rate", calendar_hash=cal("new"))["test_id"]
    ctrl = lock.register(rule_id="eq.tidal", version=1, outcome="rate", calendar_hash=cal("tide"),
                         control=True)["test_id"]
    lock.close_batch(vintage=V1_SEEN, seal_bundle_sha256=BUNDLE)
    late = lock.register(rule_id="eq.late", version=1, outcome="rate", calendar_hash=cal("late"))["test_id"]
    first_look = {cal("old")}
    a1 = 0.04 / 2

    # Seen, calendar older than the first look: S, C no; E yes with seen_data
    el = lock.eligibility(old, V1_SEEN, first_look_calendars=first_look)
    assert (el.allow_s, el.allow_c, el.allow_e, el.numbers, el.a_test) == (False, False, True, "confirmatory_e_only", a1)
    assert fam.limit_verdict("S", el) == ("N", ("seen_data", "signal_on_seen_data"))
    assert fam.limit_verdict("C", el) == ("N", ("seen_data", "signal_on_seen_data"))
    assert fam.limit_verdict("E", el) == ("E", ("seen_data",))
    assert fam.limit_verdict("N", el) == ("N", ("seen_data",))
    # Seen, calendar not committed before the first look: nothing
    el = lock.eligibility(newcal, V1_SEEN, first_look_calendars=first_look)
    assert (el.allow_s, el.allow_c, el.allow_e, el.numbers) == (False, False, False, "descriptive")
    assert fam.limit_verdict("S", el) == ("N", ("signal_on_seen_data",))
    assert fam.limit_verdict("E", el) == ("N", ("seen_data",))
    # Registered after the close, same vintage
    el = lock.eligibility(late, V1_SEEN, first_look_calendars={cal("late")})
    assert (el.allow_s, el.allow_c, el.allow_e, el.numbers) == (False, False, False, "descriptive")
    for v in "SCE":
        assert fam.limit_verdict(v, el) == ("N", ("registered_after_unblinding",))
    # Later batch, fresh vintage: yes at that batch's threshold
    fresh = {"id": "eq_v2", "confirm_period": {"start": "2026-01-01", "end": "2030-12-31"}, "seen": False}
    el = lock.eligibility(late, fresh)
    assert el.row == "batch_open" and fam.limit_verdict("S", el) == ("N", ("batch_open",))
    lock.close_batch(vintage=fresh, seal_bundle_sha256=BUNDLE)
    el = lock.eligibility(late, fresh)
    assert (el.allow_s, el.allow_c, el.allow_e, el.numbers, el.a_test) == (True, True, True, "confirmatory", 0.008)
    assert fam.limit_verdict("S", el) == ("S", ()) and fam.limit_verdict("C", el) == ("C", ())
    # Batch-1 tests are not confirmed on batch 2's vintage
    assert lock.eligibility(old, fresh).row == "not_batch_vintage"
    # Before close, unseen
    lock2, ids2 = new_lock(4)
    lock2.close_batch(vintage=V1, seal_bundle_sha256=BUNDLE)
    el = lock2.eligibility(ids2[0], V1)
    assert (el.row, el.allow_s, el.allow_c, el.allow_e, el.numbers) == ("before_close_unseen", True, True, True,
                                                                           "confirmatory")
    assert fam.limit_verdict("E", el) == ("E", ())
    # Controls: outside every batch, never S, C or E
    el = lock.eligibility(ctrl, V1_SEEN)
    assert el.numbers == "control" and fam.limit_verdict("S", el) == ("N", ("control",))
    assert ctrl not in lock.batch_tests(1)
    # U and N pass through
    assert fam.limit_verdict("U", el)[0] == "U"
    with pytest.raises(fam.FamilyError):
        fam.limit_verdict("supported", el)


def test_vintage_given_at_check_must_match_the_one_recorded_at_close():
    lock, ids = new_lock(2)
    lock.close_batch(vintage=V1, seal_bundle_sha256=BUNDLE)
    with pytest.raises(fam.FamilyError, match="differs"):
        lock.eligibility(ids[0], dict(V1, seen=True))


# ----------------------------------------------------- rules 5 and 10
def test_rule5_later_batch_needs_fresh_data():
    lock, _ = new_lock(2)
    lock.close_batch(vintage=V1, seal_bundle_sha256=BUNDLE)
    lock.register(rule_id="gold.b2", version=1, outcome="ret_lbma_usd", calendar_hash=cal("b2"))
    with pytest.raises(fam.StaleVintageError):
        lock.close_batch(vintage=V1, seal_bundle_sha256=BUNDLE)
    overlap = {"id": "v_overlap", "confirm_period": {"start": "1998-06", "end": "2004-12"}, "seen": False}
    with pytest.raises(fam.StaleVintageError):
        lock.close_batch(vintage=overlap, seal_bundle_sha256=BUNDLE)
    unopened = dict(overlap, id="other_dataset", never_opened=True)
    assert lock.close_batch(vintage=unopened, seal_bundle_sha256=BUNDLE)["batch"] == 2
    with pytest.raises(fam.FamilyError):
        lock.close_batch(vintage=V2, seal_bundle_sha256=BUNDLE)  # batch 3 is empty
    with pytest.raises(fam.FamilyError):
        fam.FamilyLock(None, "x").close_batch(vintage={"id": "v", "confirm_period": V1["confirm_period"]},
                                              seal_bundle_sha256=BUNDLE)  # no 'seen'


def test_rule10_replication_is_a_new_test_in_a_later_batch():
    lock, ids = new_lock(3)
    with pytest.raises(fam.FamilyError):
        lock.register(rule_id="gold.rule0", version=2, outcome="ret_lbma_usd", calendar_hash=cal(0),
                      replication_of=ids[0])  # original's batch still open
    lock.close_batch(vintage=V1, seal_bundle_sha256=BUNDLE)
    before = fam.canonical_bytes(lock.test_record(ids[0]))
    with pytest.raises(fam.DuplicateCalendarError):
        lock.register(rule_id="gold.rule0", version=2, outcome="ret_lbma_usd", calendar_hash=cal(0))
    rep = lock.register(rule_id="gold.rule0", version=2, outcome="ret_lbma_usd", calendar_hash=cal(0),
                        replication_of=ids[0])
    assert rep["batch"] == 2
    assert fam.canonical_bytes(lock.test_record(ids[0])) == before
    lock.close_batch(vintage=V2, seal_bundle_sha256=BUNDLE)
    assert lock.eligibility(rep["test_id"], V2).a_test == 0.008


def test_rule9_controls_take_no_share_of_alpha():
    lock, ids = new_lock(4)
    lock.register(rule_id="gold.placebo", version=1, outcome="ret_lbma_usd", calendar_hash=cal(0), control=True)
    close = lock.close_batch(vintage=V1, seal_bundle_sha256=BUNDLE)
    assert close["n_b"] == 4 and close["test_ids"] == ids
    assert lock.test_record("gold.placebo@1/primary/ret_lbma_usd")["a_test"] is None


# --------------------------------------------------------- lineage, G-04
def test_calendar_hash_and_lineage_id():
    a = np.array([0, 1, 1, 0, 1])
    assert fam.calendar_hash(a) == fam.calendar_hash(a.astype(bool)) == hashlib.sha256(bytes([0, 1, 1, 0, 1])).hexdigest()
    assert fam.calendar_hash(a) != fam.calendar_hash(np.r_[a, 0])
    with pytest.raises(fam.FamilyError):
        fam.calendar_hash([0, 2, 1])
    h = fam.calendar_hash(a)
    assert fam.lineage_id("gold.x", h) == hashlib.sha256(f"gold.x|{h}".encode()).hexdigest()
    lock = fam.FamilyLock(None, "gold")
    e = lock.register(rule_id="gold.x", version=1, outcome="ret_lbma_usd", calendar_hash=h)
    assert e["lineage_id"] == fam.lineage_id("gold.x", h)


def test_use_parent_pinned_by_hash_and_parent_edit_needs_new_child_version():
    parent_v1 = ("gold.parent", 1, "1" * 64)
    lock = fam.FamilyLock(None, "gold")
    with pytest.raises(fam.UnpinnedUseError):
        lock.register(rule_id="gold.child", version=1, outcome="ret_lbma_usd", calendar_hash=cal("c"),
                      use_parents=[{"id": "gold.parent", "version": None, "sha256": "1" * 64}])
    with pytest.raises(fam.UnpinnedUseError):
        lock.register(rule_id="gold.child", version=1, outcome="ret_lbma_usd", calendar_hash=cal("c"),
                      use_parents=[("gold.parent", 1, "not-a-hash")])
    e = lock.register(rule_id="gold.child", version=1, outcome="ret_lbma_usd", calendar_hash=cal("c"),
                      use_parents=[parent_v1])
    assert e["use_parents"] == [{"id": "gold.parent", "version": 1, "sha256": "1" * 64}]
    lock.check_against_rules([{"test_id": e["test_id"], "calendar_hash": cal("c"), "use_parents": [parent_v1]}])
    edited = ("gold.parent", 1, "2" * 64)
    with pytest.raises(fam.LockMismatchError, match="re-version"):
        lock.check_against_rules([{"test_id": e["test_id"], "calendar_hash": cal("c"), "use_parents": [edited]}])
    with pytest.raises(fam.LockMismatchError, match="calendar changed"):
        lock.check_against_rules([{"test_id": e["test_id"], "calendar_hash": cal("d"), "use_parents": [parent_v1]}])
    with pytest.raises(fam.LockMismatchError, match="not registered"):
        lock.check_against_rules([{"test_id": "gold.child@2/primary/ret_lbma_usd", "calendar_hash": cal("d"),
                                   "use_parents": [("gold.parent", 2, "2" * 64)]}])
    e2 = lock.register(rule_id="gold.child", version=2, outcome="ret_lbma_usd", calendar_hash=cal("d"),
                       use_parents=[("gold.parent", 2, "2" * 64)])
    lock.check_against_rules([{"test_id": e2["test_id"], "calendar_hash": cal("d"),
                               "use_parents": [("gold.parent", 2, "2" * 64)]}])


# ------------------------------------------------------- lock file chain
def test_lock_is_hash_chained_and_tampering_is_detected(tmp_path):
    path = tmp_path / "family.lock.jsonl"
    lock, ids = new_lock(5, path=path)
    lock.close_batch(vintage=V1, seal_bundle_sha256=BUNDLE)
    head = lock.verify()
    reopened = fam.FamilyLock(path, "gold")
    assert reopened.head() == head and reopened.test_ids() == ids
    assert reopened.batch_close_entry(1)["a_test"] == 0.04 / 5
    lines = path.read_text().splitlines()
    for j in range(1, len(lines)):
        assert json.loads(lines[j])["prev_sha256"] == hashlib.sha256(lines[j - 1].encode()).hexdigest()

    with pytest.raises(fam.FamilyLockError):
        fam.FamilyLock(path, "silver")
    # drop a line
    (tmp_path / "drop.jsonl").write_text("\n".join(lines[:2] + lines[3:]) + "\n")
    with pytest.raises(fam.FamilyLockError):
        fam.FamilyLock(tmp_path / "drop.jsonl", "gold")
    # edit a stored threshold and re-chain everything after it
    entries = [json.loads(ln) for ln in lines]
    entries[-1]["a_test"] = 0.04
    (tmp_path / "edit.jsonl").write_text(
        "\n".join(lines[:-1] + [fam.canonical_bytes(entries[-1]).decode()]) + "\n")
    with pytest.raises(fam.FamilyLockError):
        fam.FamilyLock(tmp_path / "edit.jsonl", "gold")
    # someone else appended behind our back
    other = fam.FamilyLock(path, "gold")
    other.register(rule_id="gold.other", version=1, outcome="ret_lbma_usd", calendar_hash=cal("other"))
    with pytest.raises(fam.FamilyLockError, match="changed"):
        lock.register(rule_id="gold.mine", version=1, outcome="ret_lbma_usd", calendar_hash=cal("mine"))


def test_batch_close_line_cannot_be_forged():
    lock, ids = new_lock(3)
    close = lock.close_batch(vintage=V1, seal_bundle_sha256=BUNDLE)
    lines = list(lock._lines)
    forged = dict(json.loads(lines[-1]), n_b=60, a_test=0.04 / 60)
    copy = fam.FamilyLock(None, "gold")
    for ln in lines[:-1]:
        copy._ingest(ln)
    with pytest.raises(fam.FamilyLockError):
        copy._ingest(fam.canonical_bytes(forged).decode())
    assert close["a_test"] == 0.04 / 3


# --------------------------------------------------- supportability, S-10
def test_supportability_table_matches_hand_counts():
    assert [fam.min_blocks_for_support(0.04 / n, "greater") for n in (20, 40, 60)] == [9, 10, 11]
    assert fam.min_blocks_for_support(0.04 / 20, "two_sided") == 10
    assert fam.min_informative_for_limit(0.05) == 5 and fam.min_informative_for_limit(0.001) == 10
    with pytest.raises(fam.FamilyError):
        fam.min_blocks_for_support(0.002, "either_default")
    tests = [
        {"test_id": "a", "side": "greater", "k_eff": 12, "blocks_used": 11, "informative_at_sesoi": 11},
        {"test_id": "b", "side": "greater", "k_eff": 12, "blocks_used": 10, "informative_at_sesoi": 11},
        {"test_id": "c", "side": "two_sided", "k_eff": 12, "blocks_used": 11, "informative_at_sesoi": 11},
        {"test_id": "d", "side": "less", "k_eff": 7.9, "blocks_used": 20, "informative_at_sesoi": 20},
        {"test_id": "e", "side": "greater", "k_eff": 9, "blocks_used": 9, "informative_at_sesoi": None},
        {"test_id": "f", "side": "greater", "k_eff": 9, "blocks_used": 9, "informative_at_sesoi": 11},
        {"test_id": "g", "side": "greater", "k_eff": 9, "blocks_used": 9, "informative_at_sesoi": 10},
    ]
    t = fam.supportability_table(tests, 0.04 / 60)
    cats = {r["test_id"]: r["category"] for r in t["rows"]}
    assert cats == {"a": "support", "b": "limit_only", "c": "limit_only", "d": "untestable",
                    "e": "untestable", "f": "limit_only", "g": "untestable"}
    assert t["counts"] == {"support": 1, "limit_only": 3, "untestable": 3}
    assert t["rows"][0]["informative_needed_limit"] == 11  # ceil(log2(1500))


def test_family_wise_statement_is_per_domain():
    s = fam.FAMILY_WISE_STATEMENT.format(d=4)
    assert s.startswith("Chance of at least one false Supported in a domain: at most 5% over all time.")
    assert "4 x 3 x 5%" in s
