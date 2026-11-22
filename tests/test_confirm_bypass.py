"""Bypass tests for the confirm gate (ADR-008 4.3, P1 to P9; WP-89).

Every test runs on a temporary git repository with a local bare remote, so no
network is used. The OpenTimestamps client is replaced by a fake: the real
one is never called (owner decision H19 pending).
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from vedic_astrology_core.domains.base import DatasetSpec, DomainAdapter, GateHashError, Periods, write_gate
from vedic_astrology_core.stats.seal import ConfirmAlreadyRunError, DirtyTreeError, LedgerTamperedError
from vedic_astrology_core.validity import calibration, sealbundle as sb
from vedic_astrology_core.validity.family import DuplicateCalendarError, FamilyLock, calendar_hash

DOMAIN = "testdomain"
VINTAGE = {"id": "v1", "confirm_period": {"start": "2000-01-11", "end": "2000-01-20"}, "seen": False}
HEX = re.compile(r"^[0-9a-f]{64}$")
CAL_A = calendar_hash(np.array([1, 0, 0, 1, 0, 1, 0, 0, 1, 0]))
CAL_B = calendar_hash(np.array([0, 1, 1, 0, 0, 0, 1, 0, 0, 1]))


def git(cwd: Path, *args: str) -> str:
    out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    return out.stdout.strip()


def commit_all(repo: Path, msg: str = "change") -> None:
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg)


class FakeOts:
    """Stands in for OpenTimestamps; records exactly what would leave the machine."""

    def __init__(self) -> None:
        self.calls = []
        self.mode = "complete"
        self.block_height = 870_000

    def __call__(self, action, digest, proof=None):
        self.calls.append((action, digest, proof))
        if action == "stamp":
            return b"FAKE-OTS|" + digest.encode()
        attested = proof.split(b"|", 1)[1].decode() if proof and b"|" in proof else ""
        if self.mode == "pending":
            return sb.OtsResult("pending", attested, None)
        if self.mode == "wrong":
            return sb.OtsResult("complete", "0" * 64, self.block_height)
        if self.mode == "no_height":
            return {"status": "complete", "digest": attested, "block_height": None}
        return sb.OtsResult("complete", attested, self.block_height)


@pytest.fixture
def ots(monkeypatch):
    fake = FakeOts()
    monkeypatch.setattr(sb, "ots_client", fake)
    return fake


def _register(lock_path: Path, rule_prefix: str = "rule") -> FamilyLock:
    lock = FamilyLock(lock_path, DOMAIN)
    lock.register(rule_id=f"{rule_prefix}.a", version=1, outcome="returns", calendar_hash=CAL_A)
    lock.register(rule_id=f"{rule_prefix}.b", version=1, outcome="returns", calendar_hash=CAL_B)
    return lock


def _study(repo: Path, folder: str, rule_prefix: str = "rule") -> sb.SealSources:
    """Plan, rules, family lock and gates of one study folder (outcome-free)."""
    d = repo / "studies" / folder
    (d / "rules").mkdir(parents=True, exist_ok=True)
    (d / "plan.yaml").write_text("domain: testdomain\nsesoi: 0.10\nsplit: [2000-01-10, 2000-01-11]\n")
    for name in ("a", "b"):
        (d / "rules" / f"{name}.yaml").write_text(f"id: {rule_prefix}.{name}\nversion: 1\n")
    lock = _register(d / "family_lock.jsonl", rule_prefix)
    gates = {}
    for i, tid in enumerate(lock.batch_tests(1)):
        rec = write_gate(d / "gates" / f"{i}.json", {"test_id": tid, "k_eff": 9, "blocks": 10})
        gates[tid] = rec.path
    return sb.SealSources(
        domain=DOMAIN,
        plan=d / "plan.yaml",
        family_lock=d / "family_lock.jsonl",
        gates=gates,
        rule_files=[d / "rules" / "a.yaml", d / "rules" / "b.yaml"],
        datasets=[repo / "data" / "snap.csv"],
        environment_lock=repo / "ops" / "requirements.lock.txt",
        ephemeris_files=[repo / "ephe" / "sepl_18.se1"],
        certificate=repo / calibration.DEFAULT_CERTIFICATE_PATH,
        vintage=VINTAGE,
    )


@pytest.fixture
def repo(tmp_path):
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    git(r, "config", "user.email", "t@example.invalid")
    git(r, "config", "user.name", "t")
    git(r, "config", "commit.gpgsign", "false")
    git(r, "remote", "add", "origin", str(remote))
    for rel, text in {
        "data/snap.csv": "date,value\n2000-01-01,1\n",
        "ops/requirements.lock.txt": "numpy==1.0\n",
        "ephe/sepl_18.se1": "ephemeris bytes",
        "libs/vedic_astrology_core/stats/method.py": "X = 1\n",
    }.items():
        (r / rel).parent.mkdir(parents=True, exist_ok=True)
        (r / rel).write_text(text)
    calibration.write_certificate(r / calibration.DEFAULT_CERTIFICATE_PATH, [], r, seed=1)
    commit_all(r, "init")
    git(r, "push", "-q", "origin", "HEAD:refs/heads/main")
    return r


@pytest.fixture
def sealed(repo, ots):
    src = _study(repo, "x")
    commit_all(repo, "register batch 1")
    info = sb.seal_domain(repo, src)
    return repo, src, info


def _confirm(repo, info, **kw):
    return sb.issue_confirm_handle(repo, repo / info["bundle"], **kw)


# ----------------------------------------------------------------- the path


def test_seal_then_confirm_issues_a_handle(sealed, ots):
    repo, src, info = sealed
    bundle = json.loads((repo / info["bundle"]).read_text())
    assert info["bundle_sha256"] == hashlib.sha256((repo / info["bundle"]).read_bytes()).hexdigest()
    assert {"commit", "plan", "family_lock", "confirm_ledger", "tests", "rule_files", "datasets",
            "environment_lock", "ephemeris", "certificate"} <= set(bundle)
    assert all(HEX.match(t["calendar_hash"]) and HEX.match(t["gate"]["sha256"]) for t in bundle["tests"])
    lock = FamilyLock(repo / "studies/x/family_lock.jsonl", DOMAIN)
    assert lock.batch_close_entry(1)["seal_bundle_sha256"] == info["bundle_sha256"]
    assert git(repo, "status", "--porcelain") == ""
    h = _confirm(repo, info)
    assert sb.handle_is_valid(h, DOMAIN)
    assert h.footer()["bitcoin_block_height"] == 870_000
    assert h.footer()["ots_proof"].endswith(".json.ots")
    entries = [json.loads(ln) for ln in (repo / sb.DEFAULT_LEDGER).read_text().splitlines()]
    assert len(entries) == 2 and all(e["kind"] == "confirm" for e in entries)
    assert git(repo, "log", "-1", "--format=%H") == h.ledger_commit
    assert git(repo, "status", "--porcelain") == ""


def test_only_the_bundle_hash_leaves_the_machine(sealed, ots):
    repo, _, info = sealed
    _confirm(repo, info)
    assert [c[0] for c in ots.calls] == ["stamp", "verify"]
    for action, digest, proof in ots.calls:
        assert digest == info["bundle_sha256"] and HEX.match(digest)
        assert proof is None or proof == b"FAKE-OTS|" + digest.encode()  # its own proof back


def test_default_client_is_not_wired(sealed, monkeypatch):
    repo, _, info = sealed
    monkeypatch.undo()  # the real ots_client: refuses, sends nothing
    with pytest.raises(sb.OtsNotConfiguredError):
        _confirm(repo, info)
    assert not (repo / sb.DEFAULT_LEDGER).exists()


# ------------------------------------------------------------------- P1-P9


def test_p1_copied_study_cannot_confirm_again(sealed, ots):
    repo, _, info = sealed
    _confirm(repo, info)
    copy = _study(repo, "x_copy")  # same rules, calendars and data in a new folder
    commit_all(repo, "copy the study")
    info2 = sb.seal_domain(repo, copy, bundle_dir="studies/validity/seals_copy")
    with pytest.raises(ConfirmAlreadyRunError):
        _confirm(repo, info2)


def test_p2_no_handle_before_the_ledger_commit(sealed, ots, monkeypatch):
    repo, _, info = sealed
    before = dict(sb._ISSUED)
    real = sb._commit_paths

    def crash(top, rels, message):
        if any(r.endswith("confirm_ledger.jsonl") for r in rels):
            raise sb.SealBundleError("simulated crash before the ledger commit")
        return real(top, rels, message)

    monkeypatch.setattr(sb, "_commit_paths", crash)
    with pytest.raises(sb.SealBundleError, match="simulated crash"):
        _confirm(repo, info)
    assert sb._ISSUED == before  # nothing was issued, so nothing was read
    monkeypatch.setattr(sb, "_commit_paths", real)
    (repo / sb.DEFAULT_LEDGER).unlink()  # delete the uncommitted lines and start again
    assert sb.handle_is_valid(_confirm(repo, info))


def test_p2_removing_a_committed_line_is_detected(sealed, ots):
    repo, _, info = sealed
    _confirm(repo, info)
    led = repo / sb.DEFAULT_LEDGER
    led.write_text(led.read_text().splitlines()[0] + "\n")  # chain still valid: a prefix
    commit_all(repo, "drop a ledger line")
    with pytest.raises(LedgerTamperedError):
        _confirm(repo, info)


def test_p3_made_up_gate_hash_is_refused(sealed):
    repo, src, _ = sealed
    adapter = FakeAdapter()
    g = guarded_fake(adapter)
    with pytest.raises(GateHashError):
        g.outcomes("a" * 64)
    gate = next(iter(src.gates.values()))
    with pytest.raises(GateHashError):
        g.outcomes("b" * 64, gate_path=gate)
    real = hashlib.sha256(Path(gate).read_bytes()).hexdigest()
    assert g.outcomes(real, gate_path=gate) is not None


def test_p4_no_handle_rows_end_at_the_explore_end():
    adapter = FakeAdapter()
    g = sb.guarded(adapter)
    end = adapter.periods().explore[1]
    cat, info = g.catalogue()
    assert len(cat) == 10 and max(cat["time"].dt.date) <= end
    with pytest.raises(sb.ConfirmAccessError):
        g.catalogue(until="2000-01-15")
    flags = g.mainshock_flags()
    assert all(max(s.index) < 10 for s in flags.values())
    full, _ = adapter.catalogue()
    with pytest.raises(sb.ConfirmAccessError):
        g.mainshock_flags(full)
    gate = write_gate(adapter.tmp / "gate.json", {"g": 1})
    out = g.outcomes(gate)
    assert len(out["event_bins"]) == 10 and out["event_bins"].sum() == 10
    assert "confirm" not in out["counts"] and "n_rows" not in out
    assert "outcomes.counts.confirm" in g.withheld and "outcomes.n_rows" in g.withheld
    with pytest.raises(sb.ConfirmAccessError):
        g.outcomes(gate, until=date(2000, 1, 20))


def test_p4_a_forged_or_foreign_handle_opens_nothing(sealed, ots):
    repo, _, info = sealed
    h = _confirm(repo, info)
    forged = sb.ConfirmHandle(**{**h.__dict__, "token": "0" * 32})
    assert not sb.handle_is_valid(forged)
    adapter = FakeAdapter()
    with pytest.raises(sb.ConfirmAccessError):
        sb.guarded(adapter, forged)
    other = FakeAdapter(domain="otherdomain")
    with pytest.raises(sb.ConfirmAccessError):
        sb.guarded(other, h)
    opened = sb.guarded(adapter, h)
    cat, _ = opened.catalogue(until="2000-01-20")
    assert len(cat) == 20


def test_p5_provisional_run_reads_no_confirm_row(repo, ots):
    src = _study(repo, "x")
    commit_all(repo)
    info = sb.seal_domain(repo, src)
    (repo / "scratch.txt").write_text("dirty")
    adapter = FakeAdapter()
    with pytest.raises(sb.ProvisionalRunError):
        _confirm(repo, info, provisional=True)
    with pytest.raises(DirtyTreeError):
        _confirm(repo, info)
    g = sb.guarded(adapter)  # what a provisional pipeline gets: no handle
    seen = []  # spy: the date of every row the run receives
    cat, _ = g.catalogue()
    seen += list(cat["time"].dt.date)
    for flags in g.mainshock_flags().values():
        seen += list(adapter.catalogue()[0].loc[flags.index, "time"].dt.date)
    bins = g.outcomes(write_gate(adapter.tmp / "gate.json", {"g": 1}))["event_bins"]
    seen += list(adapter.grid()[: len(bins)].date)
    assert seen and max(seen) <= adapter.periods().explore[1]


def test_p6_renamed_rule_is_refused_at_registration(tmp_path):
    lock = _register(tmp_path / "lock.jsonl")
    with pytest.raises(DuplicateCalendarError):
        lock.register(rule_id="renamed.a", version=1, outcome="returns", calendar_hash=CAL_A)


def test_p7_plan_changed_after_batch_close_is_refused(sealed, ots):
    repo, _, info = sealed
    plan = repo / "studies/x/plan.yaml"
    plan.write_text(plan.read_text().replace("sesoi: 0.10", "sesoi: 0.05"))
    commit_all(repo, "amend SESOI")
    with pytest.raises(sb.BundleMismatchError, match="plan"):
        _confirm(repo, info)


@pytest.mark.parametrize("case", ["missing", "pending", "wrong", "no_height"])
def test_p8_missing_pending_or_wrong_proof_is_refused(sealed, ots, case):
    repo, _, info = sealed
    if case == "missing":
        (repo / info["ots"]).unlink()
        commit_all(repo, "remove proof")
    else:
        ots.mode = case
    with pytest.raises(sb.OtsProofError):
        _confirm(repo, info)
    assert not (repo / sb.DEFAULT_LEDGER).exists()


def test_p9_broken_hash_chain_is_refused(sealed, ots):
    repo, _, info = sealed
    led = repo / sb.DEFAULT_LEDGER
    first = {"kind": "note", "prev_sha256": None}
    second = {"kind": "note", "prev_sha256": "f" * 64}  # not the hash of the first line
    led.parent.mkdir(parents=True, exist_ok=True)
    led.write_text(json.dumps(first, sort_keys=True) + "\n" + json.dumps(second, sort_keys=True) + "\n")
    commit_all(repo, "ledger with a broken link")
    with pytest.raises(LedgerTamperedError, match="hash chain"):
        _confirm(repo, info)


def test_p9_verify_chain_accepts_an_intact_chain(sealed, ots):
    repo, _, info = sealed
    _confirm(repo, info)
    assert len(sb.verify_chain(repo / sb.DEFAULT_LEDGER)) == 2


# ----------------------------------------------------------- other refusals


def test_unpublished_batch_close_is_refused(sealed, ots):
    repo, _, info = sealed
    first = git(repo, "rev-list", "--max-parents=0", "HEAD")
    git(repo, "push", "-q", "-f", "origin", f"{first}:refs/heads/main")
    with pytest.raises(sb.NotPublishedError):
        _confirm(repo, info)


def test_changed_certified_code_refuses_the_handle(sealed, ots):
    repo, _, info = sealed
    (repo / "libs/vedic_astrology_core/stats/method.py").write_text("X = 2\n")
    commit_all(repo, "change the statistics after calibrating")
    with pytest.raises(sb.SealBundleError, match="certificate"):
        _confirm(repo, info)


def test_certificate_without_required_cases_refuses(repo, ots):
    src = _study(repo, "x")
    src = sb.SealSources(**{**src.__dict__, "outcome_types": ("flags",)})
    commit_all(repo)
    info = sb.seal_domain(repo, src)
    with pytest.raises(sb.SealBundleError, match="certificate"):
        _confirm(repo, info)


def test_edited_bundle_bytes_are_refused(sealed, ots):
    repo, _, info = sealed
    p = repo / info["bundle"]
    p.write_text(json.dumps(json.loads(p.read_text()), indent=1))
    commit_all(repo, "pretty-print the bundle")
    with pytest.raises(sb.BundleMismatchError):
        _confirm(repo, info)


def test_changed_dataset_or_gate_is_refused(sealed, ots):
    repo, src, info = sealed
    (repo / "data/snap.csv").write_text("date,value\n2000-01-01,2\n")
    Path(next(iter(src.gates.values()))).write_text('{"edited": true}\n')
    commit_all(repo, "swap data and gate")
    with pytest.raises(sb.BundleMismatchError, match="dataset.*gate|gate.*dataset"):
        _confirm(repo, info)


def test_seal_refuses_a_dirty_tree(repo, ots):
    src = _study(repo, "x")
    with pytest.raises(DirtyTreeError):
        sb.seal_domain(repo, src)
    assert ots.calls == []


def test_seal_refuses_while_legacy_readers_remain(repo, ots):
    src = _study(repo, "x")
    src = sb.SealSources(**{**src.__dict__, "domain": "earthquake"})
    legacy = repo / sb.LEGACY_CONFIRM_READERS["earthquake"][0]
    legacy.parent.mkdir(parents=True, exist_ok=True)
    legacy.write_text("slices = {'confirm': ...}\n")
    commit_all(repo)
    with pytest.raises(sb.LegacyReaderError):
        sb.seal_domain(repo, src)
    legacy.write_text(f"# {sb.ADAPTER_ONLY_MARKER}\n")
    commit_all(repo)
    assert sb.legacy_reader_problems(repo, "earthquake") == []


def test_a_batch_is_sealed_once(sealed, ots):
    repo, src, _ = sealed
    with pytest.raises(sb.SealBundleError):
        sb.seal_domain(repo, src)


# -------------------------------------------------------------- fake adapter


class FakeAdapter(DomainAdapter):
    """Daily grid 2000-01-01..20; explore to the 10th, confirm from the 11th. Spies on reads."""

    def __init__(self, domain: str = DOMAIN):
        super().__init__({}, {})
        self.domain = domain
        import tempfile

        self.tmp = Path(tempfile.mkdtemp())

    def dataset_spec(self):
        return DatasetSpec("fake", "0" * 64, "fake", ("2000-01-01", "2000-01-20"), 20)

    def grid(self):
        return pd.date_range("2000-01-01", periods=20, freq="D", tz="UTC")

    def calendar_context(self):
        return {}

    def periods(self):
        return Periods(explore=(date(2000, 1, 1), date(2000, 1, 10)),
                       confirm=(date(2000, 1, 11), date(2000, 1, 20)))

    def catalogue(self):
        cat = pd.DataFrame({"time": self.grid(), "mw": np.linspace(5, 7, 20)})
        return cat, {"n_all": 20, "source": "fake"}

    def mainshock_flags(self, cat=None):
        if cat is None:
            cat, _ = self.catalogue()
        return {"gk": pd.Series(True, index=cat.index), "raw": pd.Series(True, index=cat.index)}

    def _outcomes(self):
        return {"event_bins": np.ones(20), "counts": {"explore": 10, "confirm": 10}, "n_rows": 20,
                "declustering": "gk"}

    def _controls(self):
        return {}


def guarded_fake(adapter):
    return sb.guarded(adapter)
