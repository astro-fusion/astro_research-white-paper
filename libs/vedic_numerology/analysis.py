"""
High-level numerology+astrology integration class used across the repo.
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any, Dict, Optional, Union

from vedic_astrology_core import VedicAstrologyChart
from vedic_astrology_core.config.constants import PLANET_NAMES, Planet

from .numerology import calculate_bhagyanka, calculate_mulanka


class VedicNumerologyAstrology:
    """
    Combines Vedic numerology (Mulanka/Bhagyanka) with astrological dignity scoring.

    This provides a stable API for:
      - Streamlit app (`app.py`)
      - docs examples
      - tests (`tests/test_integration.py`)
    """

    def __init__(
        self,
        birth_date: Union[str, date],
        birth_time: Optional[Union[str, time]] = None,
        latitude: float = 28.6139,
        longitude: float = 77.1025,
        timezone: str = "Asia/Kolkata",
        ayanamsa_system: str = "lahiri",
    ) -> None:
        self._birth_date = self._parse_birth_date(birth_date)
        self._birth_time = self._parse_birth_time(birth_time) if birth_time else None
        self.latitude = latitude
        self.longitude = longitude
        self.timezone = timezone
        self.ayanamsa_system = ayanamsa_system

        self._astro = VedicAstrologyChart(
            birth_date=self._birth_date,
            birth_time=self._birth_time,
            latitude=self.latitude,
            longitude=self.longitude,
            timezone=self.timezone,
            ayanamsa_system=self.ayanamsa_system.upper(),
        )

    @property
    def birth_datetime(self) -> datetime:
        """Get the combined birth date and time."""
        if self._birth_time:
            return datetime.combine(self._birth_date, self._birth_time)
        return datetime.combine(self._birth_date, time.min)

    def _parse_birth_date(self, d: Union[str, date]) -> date:
        if isinstance(d, str):
            return datetime.strptime(d, "%Y-%m-%d").date()
        if isinstance(d, date):
            return d
        raise TypeError(f"birth_date must be str or date, got {type(d)}")

    def _parse_birth_time(self, t: Union[str, time]) -> time:
        if isinstance(t, str):
            try:
                return datetime.strptime(t, "%H:%M:%S").time()
            except ValueError:
                return datetime.strptime(t, "%H:%M").time()
        if isinstance(t, time):
            return t
        raise TypeError(f"birth_time must be str or time, got {type(t)}")

    def calculate_mulanka(self) -> Dict[str, Any]:
        number, planet = calculate_mulanka(
            self._birth_date, self._birth_time, self.latitude, self.longitude
        )
        return {"number": number, "planet": planet}

    def calculate_bhagyanka(self) -> Dict[str, Any]:
        number, planet = calculate_bhagyanka(self._birth_date)
        return {"number": number, "planet": planet}

    def score_dignity(self, planet: Union[Planet, str]) -> Dict[str, Any]:
        return self._astro.score_dignity(planet)

    def analyze_support_contradiction(self) -> Dict[str, Any]:
        mulanka = self.calculate_mulanka()
        bhagyanka = self.calculate_bhagyanka()

        mul_score = self.score_dignity(mulanka["planet"])
        bha_score = self.score_dignity(bhagyanka["planet"])

        def _support_level(score: float) -> str:
            if score >= 75:
                return "Excellent"
            if score >= 50:
                return "Good"
            if score >= 40:
                return "Neutral"
            if score >= 25:
                return "Weak"
            return "Poor"

        mul_level = _support_level(float(mul_score["score"]))
        bha_level = _support_level(float(bha_score["score"]))
        avg = (float(mul_score["score"]) + float(bha_score["score"])) / 2.0
        overall = _support_level(avg)

        return {
            "mulanka": {
                "planet": mulanka["planet"],
                "score": float(mul_score["score"]),
                "support_level": mul_level,
                "dignity_type": mul_score.get("dignity_type"),
                "details": mul_score,
            },
            "bhagyanka": {
                "planet": bhagyanka["planet"],
                "score": float(bha_score["score"]),
                "support_level": bha_level,
                "dignity_type": bha_score.get("dignity_type"),
                "details": bha_score,
            },
            "overall": {
                "average_score": avg,
                "harmony_level": overall,
                "harmony_score": avg,
                "support_level": overall,
            },
        }

    def plot_dignity_analysis(
        self, planet: Union[Planet, str], use_plotly: bool = True
    ) -> Any:
        return self._astro.plot_dignity_analysis(planet=planet, use_plotly=use_plotly)

    def plot_temporal_support(
        self,
        start_date: Union[str, datetime],
        end_date: Union[str, datetime],
        planet: Union[Planet, str],
        use_plotly: bool = True,
    ) -> Any:
        if isinstance(start_date, str):
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        else:
            start_dt = start_date
        if isinstance(end_date, str):
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        else:
            end_dt = end_date
        return self._astro.plot_temporal_support(
            start_date=start_dt, end_date=end_dt, planet=planet, use_plotly=use_plotly
        )

    def plot_numerology_comparison(self, use_plotly: bool = True) -> Any:
        """
        Plot numerology vs astrology strength over time for the Mulanka planet
        for the next year starting today.
        """
        from datetime import date as _date

        from vedic_astrology_core.time_series import compute_combined_series
        from vedic_numerology.visualization import plot_numerology_comparison

        today = _date.today()
        end = today.replace(year=today.year + 1)
        df = compute_combined_series(today, end, step_days=1)

        mulanka_planet = self.calculate_mulanka()["planet"]
        return plot_numerology_comparison(
            df, planet=mulanka_planet, use_plotly=use_plotly
        )

    def generate_report(self) -> str:
        mul = self.calculate_mulanka()
        bha = self.calculate_bhagyanka()
        support = self.analyze_support_contradiction()

        lines = []
        lines.append("=" * 70)
        lines.append("VEDIC NUMEROLOGY-ASTROLOGY ANALYSIS REPORT")
        lines.append("=" * 70)
        lines.append("")
        lines.append("BIRTH DATA:")
        lines.append(f"  Date: {self._birth_date.isoformat()}")
        if self._birth_time is not None:
            lines.append(f"  Time: {self._birth_time.isoformat()}")
        lines.append(f"  Location: {self.latitude:.4f}, {self.longitude:.4f}")
        lines.append(f"  Ayanamsa: {self.ayanamsa_system}")
        lines.append("")
        lines.append("NUMEROLOGY CALCULATIONS:")
        lines.append(
            f"  Mulanka (Birth Number): {mul['number']} ({PLANET_NAMES[mul['planet']]})"
        )
        lines.append(
            f"  Bhagyanka (Destiny Number): {bha['number']} ({PLANET_NAMES[bha['planet']]})"
        )
        lines.append("")
        lines.append("PLANETARY SUPPORT ANALYSIS:")
        lines.append(
            f"  Mulanka planet dignity: {support['mulanka']['score']:.1f}/100 ({support['mulanka']['support_level']})"
        )
        lines.append(
            f"  Bhagyanka planet dignity: {support['bhagyanka']['score']:.1f}/100 ({support['bhagyanka']['support_level']})"
        )
        lines.append(
            f"  Overall: {support['overall']['average_score']:.1f}/100 ({support['overall']['harmony_level']})"
        )
        lines.append("")
        lines.append("=" * 70)
        return "\n".join(lines)


def analyze_birth_chart(
    birth_date: Union[str, date],
    birth_time: Optional[Union[str, time]] = None,
    latitude: float = 28.6139,
    longitude: float = 77.1025,
    timezone: str = "Asia/Kolkata",
    ayanamsa_system: str = "lahiri",
) -> VedicNumerologyAstrology:
    return VedicNumerologyAstrology(
        birth_date=birth_date,
        birth_time=birth_time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        ayanamsa_system=ayanamsa_system,
    )
