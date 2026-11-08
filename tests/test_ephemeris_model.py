"""The engine's ephemeris model is read once from a planet and never changes."""

import pytest
import swisseph as swe

from vedic_astrology_core.astrology.ephemeris import EphemerisEngine


@pytest.fixture
def engine_without_files(tmp_path, monkeypatch):
    """Build an engine whose ephemeris path holds no ``.se1`` files."""
    monkeypatch.delenv("SE_EPHE_PATH", raising=False)
    engine = EphemerisEngine(ephe_path=str(tmp_path))
    yield engine
    swe.set_ephe_path(None)


def test_model_is_moshier_without_se1_files(engine_without_files):
    """Without data files Swiss Ephemeris falls back to Moshier."""
    assert engine_without_files.ephemeris_model == "moshier"


def test_node_call_does_not_overwrite_the_model(engine_without_files):
    """The mean-node call ends get_all_planet_positions and reports SWIEPH."""
    engine_without_files.get_all_planet_positions(2443000.5)
    assert engine_without_files.last_retflag & swe.FLG_SWIEPH
    assert engine_without_files.ephemeris_model == "moshier"
    info = engine_without_files.get_ephemeris_info()
    assert info["ephemeris_model"] == "moshier"


def test_model_is_read_only(engine_without_files):
    """The model cannot be reassigned after creation."""
    with pytest.raises(AttributeError):
        engine_without_files.ephemeris_model = "swieph"
