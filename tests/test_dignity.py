"""
Unit tests for dignity module.

Tests planetary dignity scoring, exaltation/debilitation matrices,
friendship matrices, and scoring modifiers.
"""

import unittest
from unittest.mock import Mock

from vedic_astrology_core.config.constants import Planet
from vedic_astrology_core.dignity import DignityScorer
from vedic_astrology_core.dignity.exaltation_matrix import (
    DEBILITATION_TABLE,
    EXALTATION_TABLE,
    MOOLATRIKONA_TABLE,
    get_debilitation_sign,
    get_dignity_type,
    get_exaltation_sign,
    is_in_exaltation,
    is_in_moolatrikona,
    is_in_own_sign,
)
from vedic_astrology_core.dignity.friendship_matrix import (
    FriendshipType,
    get_natural_friendship,
)
from vedic_astrology_core.dignity.modifiers import (
    apply_combust_penalty,
    apply_retrograde_bonus,
)


class TestExaltationMatrix(unittest.TestCase):
    """Test exaltation and debilitation matrix functions."""

    def test_exaltation_signs(self):
        """Test exaltation sign retrieval."""
        # Test known exaltation signs
        sign_idx, degrees, sign_name = get_exaltation_sign(Planet.SUN)
        self.assertEqual(sign_idx, 0)  # Aries
        self.assertEqual(degrees, 10.0)
        self.assertEqual(sign_name, "Aries")

        sign_idx, degrees, sign_name = get_exaltation_sign(Planet.MOON)
        self.assertEqual(sign_idx, 1)  # Taurus
        self.assertEqual(degrees, 3.0)
        self.assertEqual(sign_name, "Taurus")

    def test_debilitation_signs(self):
        """Test debilitation sign retrieval."""
        # Test known debilitation signs
        sign_idx, degrees, sign_name = get_debilitation_sign(Planet.SUN)
        self.assertEqual(sign_idx, 6)  # Libra
        self.assertEqual(degrees, 10.0)
        self.assertEqual(sign_name, "Libra")

        sign_idx, degrees, sign_name = get_debilitation_sign(Planet.MOON)
        self.assertEqual(sign_idx, 7)  # Scorpio
        self.assertEqual(degrees, 3.0)
        self.assertEqual(sign_name, "Scorpio")

    def test_vedic_exaltation_mapping(self):
        """Test that Vedic planets (Rahu/Ketu) have exaltation defined."""
        # Rahu and Ketu should have exaltation signs defined
        # (even if they don't have traditional exaltation)
        try:
            get_exaltation_sign(Planet.RAHU)
            get_exaltation_sign(Planet.KETU)
        except ValueError:
            self.fail("Rahu and Ketu should have exaltation signs defined")

    def test_exaltation_detection(self):
        """Test exaltation detection logic."""
        # Sun in Aries 10° should be exalted
        sun_exalted_long = 0 * 30 + 10  # Aries 10°
        self.assertTrue(is_in_exaltation(sun_exalted_long, Planet.SUN))

        # Sun in Libra 10° should be debilitated, not exalted
        sun_debilitated_long = 6 * 30 + 10  # Libra 10°
        self.assertFalse(is_in_exaltation(sun_debilitated_long, Planet.SUN))

        # Uccha is the whole sign: Aries 0.5 and 29.5 are both exalted.
        self.assertTrue(is_in_exaltation(0.5, Planet.SUN))
        self.assertTrue(is_in_exaltation(25.0, Planet.SUN))
        self.assertTrue(is_in_exaltation(29.5, Planet.SUN))
        self.assertFalse(is_in_exaltation(30.5, Planet.SUN))  # Taurus

    def test_moolatrikona_detection(self):
        """Test Moolatrikona detection."""
        # Sun in Leo 15° should be in Moolatrikona (Leo 0-20°)
        sun_moola_long = 4 * 30 + 15  # Leo 15°
        self.assertTrue(is_in_moolatrikona(sun_moola_long, Planet.SUN))

        # Sun in Leo 25° should not be in Moolatrikona (outside 0-20° range)
        sun_not_moola_long = 4 * 30 + 25  # Leo 25°
        self.assertFalse(is_in_moolatrikona(sun_not_moola_long, Planet.SUN))

    def test_own_sign_detection(self):
        """Test own sign detection."""
        # Mars in Aries should be in own sign
        mars_own_long = 0 * 30 + 15  # Aries 15°
        self.assertTrue(is_in_own_sign(mars_own_long, Planet.MARS))

        # Mars in Scorpio should be in own sign
        mars_own_long2 = 7 * 30 + 15  # Scorpio 15°
        self.assertTrue(is_in_own_sign(mars_own_long2, Planet.MARS))

        # Mars in Taurus should not be in own sign
        mars_not_own_long = 1 * 30 + 15  # Taurus 15°
        self.assertFalse(is_in_own_sign(mars_not_own_long, Planet.MARS))


class TestFriendshipMatrix(unittest.TestCase):
    """Test planetary friendship functions."""

    def test_natural_friendship_sun(self):
        """Test Sun's natural friendships."""
        # Sun should be friend with Moon, Mars, Jupiter
        self.assertEqual(
            get_natural_friendship(Planet.SUN, Planet.MOON),
            FriendshipType.NATURAL_FRIEND,
        )
        self.assertEqual(
            get_natural_friendship(Planet.SUN, Planet.MARS),
            FriendshipType.NATURAL_FRIEND,
        )
        self.assertEqual(
            get_natural_friendship(Planet.SUN, Planet.JUPITER),
            FriendshipType.NATURAL_FRIEND,
        )

        # Sun should be enemy with Venus, Saturn
        self.assertEqual(
            get_natural_friendship(Planet.SUN, Planet.VENUS),
            FriendshipType.NATURAL_ENEMY,
        )
        self.assertEqual(
            get_natural_friendship(Planet.SUN, Planet.SATURN),
            FriendshipType.NATURAL_ENEMY,
        )

        # Sun should be neutral with Mercury
        self.assertEqual(
            get_natural_friendship(Planet.SUN, Planet.MERCURY),
            FriendshipType.NATURAL_NEUTRAL,
        )

    def test_rahu_ketu_friendship(self):
        """Test Rahu and Ketu friendship (natural enemies)."""
        self.assertEqual(
            get_natural_friendship(Planet.RAHU, Planet.KETU),
            FriendshipType.NATURAL_ENEMY,
        )
        self.assertEqual(
            get_natural_friendship(Planet.KETU, Planet.RAHU),
            FriendshipType.NATURAL_ENEMY,
        )

    def test_natural_friendship_matches_bphs(self):
        """Naisargika maitri equals BPHS Ch. 3 (it is not symmetric)."""
        bphs = {
            Planet.SUN: ("MOON MARS JUPITER", "MERCURY", "VENUS SATURN"),
            Planet.MOON: ("SUN MERCURY", "MARS JUPITER VENUS SATURN", ""),
            Planet.MARS: ("SUN MOON JUPITER", "VENUS SATURN", "MERCURY"),
            Planet.MERCURY: ("SUN VENUS", "MARS JUPITER SATURN", "MOON"),
            Planet.JUPITER: ("SUN MOON MARS", "SATURN", "MERCURY VENUS"),
            Planet.VENUS: ("MERCURY SATURN", "MARS JUPITER", "SUN MOON"),
            Planet.SATURN: ("MERCURY VENUS", "JUPITER", "SUN MOON MARS"),
        }
        kinds = (
            FriendshipType.NATURAL_FRIEND,
            FriendshipType.NATURAL_NEUTRAL,
            FriendshipType.NATURAL_ENEMY,
        )
        for planet, groups in bphs.items():
            for kind, names in zip(kinds, groups):
                for name in names.split():
                    with self.subTest(planet=planet, other=name):
                        self.assertEqual(
                            get_natural_friendship(planet, Planet[name]), kind
                        )
        # Asymmetric pair: the Moon is neutral to Mars, Mars a friend to the Moon.
        self.assertEqual(
            get_natural_friendship(Planet.MOON, Planet.MERCURY),
            FriendshipType.NATURAL_FRIEND,
        )
        self.assertEqual(
            get_natural_friendship(Planet.MERCURY, Planet.MOON),
            FriendshipType.NATURAL_ENEMY,
        )


class TestDignityScorer(unittest.TestCase):
    """Test dignity scoring functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.scorer = DignityScorer()

    def test_exaltation_scoring(self):
        """Test scoring for exalted planets."""
        # Mock chart object
        mock_chart = Mock()

        # Sun in Aries 10° (exact exaltation)
        sun_longitude = 0 * 30 + 10  # Aries 10°
        score = self.scorer.calculate_base_score(
            Planet.SUN, 0, sun_longitude, mock_chart
        )
        self.assertEqual(score, 100.0)  # Exaltation score

    def test_debilitation_scoring(self):
        """Test scoring for debilitated planets."""
        mock_chart = Mock()

        # Sun in Libra 10° (exact debilitation)
        sun_longitude = 6 * 30 + 10  # Libra 10°
        score = self.scorer.calculate_base_score(
            Planet.SUN, 6, sun_longitude, mock_chart
        )
        self.assertEqual(score, 5.0)  # Debilitation score

    def test_moolatrikona_scoring(self):
        """Test scoring for planets in Moolatrikona."""
        mock_chart = Mock()

        # Sun in Leo 15° (Moolatrikona range: Leo 0-20°)
        sun_longitude = 4 * 30 + 15  # Leo 15°
        score = self.scorer.calculate_base_score(
            Planet.SUN, 4, sun_longitude, mock_chart
        )
        self.assertEqual(score, 90.0)  # Moolatrikona score

    def test_own_sign_scoring(self):
        """Test scoring for planets in own signs."""
        mock_chart = Mock()

        # Mars in Aries 20° (own sign, outside Moolatrikona)
        mars_longitude = 0 * 30 + 20  # Aries 20°
        score = self.scorer.calculate_base_score(
            Planet.MARS, 0, mars_longitude, mock_chart
        )
        self.assertEqual(score, 75.0)  # Own sign score

    def test_neutral_sign_scoring(self):
        """Test scoring for planets in neutral signs."""
        mock_chart = Mock()
        mock_chart.planets = {}

        # Sun in Gemini (neither exalted, debilitated, own sign, nor Moolatrikona)
        sun_longitude = 2 * 30 + 15  # Gemini 15°
        score = self.scorer.calculate_base_score(
            Planet.SUN, 2, sun_longitude, mock_chart
        )
        self.assertTrue(40 <= score <= 65)  # Should be in friend/neutral range

    def test_dignity_status_conversion(self):
        """Test conversion of scores to dignity status."""
        # Test various score ranges
        self.assertEqual(self.scorer.get_dignity_status(95), "Exalted/Excellent")
        self.assertEqual(self.scorer.get_dignity_status(80), "Very Strong")
        self.assertEqual(self.scorer.get_dignity_status(60), "Strong")
        self.assertEqual(self.scorer.get_dignity_status(45), "Moderate")
        self.assertEqual(self.scorer.get_dignity_status(30), "Weak")
        self.assertEqual(self.scorer.get_dignity_status(10), "Very Weak")
        self.assertEqual(self.scorer.get_dignity_status(2), "Debilitated/Critical")


class TestModifiers(unittest.TestCase):
    """Test dignity score modifiers."""

    def test_retrograde_bonus(self):
        """Test retrograde bonus application."""
        # Normal planet (no retrograde bonus)
        score = apply_retrograde_bonus(60.0, False, False)
        self.assertEqual(score, 60.0)

        # Retrograde non-debilitated planet (normal bonus)
        score = apply_retrograde_bonus(60.0, True, False)
        self.assertEqual(score, 60.0 + 15)  # +15 bonus

        # Retrograde debilitated planet (Neecha Bhanga)
        score = apply_retrograde_bonus(10.0, True, True)
        self.assertEqual(score, 10.0 + 50)  # +50 bonus

    def test_combust_penalty(self):
        """Test combustion penalty application."""
        # Non-combust planet (no penalty)
        score = apply_combust_penalty(80.0, False)
        self.assertEqual(score, 80.0)

        # Combust planet (penalty applied)
        score = apply_combust_penalty(80.0, True)
        self.assertEqual(score, 80.0 - 20)  # -20 penalty

        # Combust with exact degree (major combustion)
        score = apply_combust_penalty(80.0, True, 2.0)  # Within 3°
        self.assertEqual(score, 80.0 - 40)  # -40 major penalty

    def test_score_bounds(self):
        """Test that scores stay within 0-100 bounds."""
        # Test lower bound
        score = apply_retrograde_bonus(5.0, True, True)  # 5 + 50 = 55
        self.assertEqual(score, 55.0)

        # Test upper bound with multiple bonuses
        score = apply_retrograde_bonus(
            95.0, True, False
        )  # 95 + 15 = 110 → capped at 100
        self.assertEqual(score, 100.0)

        # Test lower bound with penalties
        score = apply_combust_penalty(10.0, True, 1.0)  # 10 - 40 = -30 → floored at 0
        self.assertEqual(score, 0.0)


class TestMars1984Dignity(unittest.TestCase):
    """Test dignity scoring for the Mars 1984 case."""

    def test_mars_in_scorpio_dignity(self):
        """Test Mars dignity when in Scorpio (own sign)."""
        scorer = DignityScorer()
        mock_chart = Mock()

        # Mars in Scorpio (own sign)
        mars_longitude = 7 * 30 + 15  # Scorpio 15°
        score = scorer.calculate_base_score(Planet.MARS, 7, mars_longitude, mock_chart)

        # Should be own sign score (75)
        self.assertEqual(score, 75.0)

    def test_mars_in_cancer_dignity(self):
        """Test Mars dignity when in Cancer (debilitation)."""
        scorer = DignityScorer()
        mock_chart = Mock()

        # Mars in Cancer (debilitated)
        mars_longitude = 3 * 30 + 28  # Cancer 28° (near debilitation at 28°)
        score = scorer.calculate_base_score(Planet.MARS, 3, mars_longitude, mock_chart)

        # Should be debilitation score (5)
        self.assertEqual(score, 5.0)


class TestBphsDignityTables(unittest.TestCase):
    """Pin the dignity tables to BPHS ch. 3 (Santhanam 1984).

    BPHS 3.49-50: "The deepest exaltation degrees are respectively 10, 3,
    28, 15, 5, 27 and 20" in Aries, Taurus, Capricorn, Virgo, Cancer, Pisces
    and Libra. BPHS 3.51-54: Sun Leo first 20 degrees; Moon Taurus after the
    first 3 degrees; Mars Aries first 12 degrees; Mercury Virgo the 5 degrees
    after the first 15; Jupiter the first third of Sagittarius; Venus the
    first half of Libra; Saturn Aquarius as the Sun in Leo. Ranges are
    half-open: "the first 20 degrees" ends before 20.
    """

    # BPHS 3.51-54 (Santhanam 1984): (sign index, start deg, end deg).
    MOOLATRIKONA = {
        Planet.SUN: (4, 0.0, 20.0),
        Planet.MOON: (1, 3.0, 30.0),
        Planet.MARS: (0, 0.0, 12.0),
        Planet.MERCURY: (5, 15.0, 20.0),
        Planet.JUPITER: (8, 0.0, 10.0),
        Planet.VENUS: (6, 0.0, 15.0),
        Planet.SATURN: (10, 0.0, 20.0),
    }

    # BPHS 3.49-50 (Santhanam 1984): (sign index, deep-exaltation degree).
    DEEP_EXALTATION = {
        Planet.SUN: (0, 10.0),
        Planet.MOON: (1, 3.0),
        Planet.MARS: (9, 28.0),
        Planet.MERCURY: (5, 15.0),
        Planet.JUPITER: (3, 5.0),
        Planet.VENUS: (11, 27.0),
        Planet.SATURN: (6, 20.0),
    }

    def test_moolatrikona_table_matches_bphs_3_51_54(self):
        """Moolatrikona table equals BPHS 3.51-54."""
        for planet, (sign, start, end) in self.MOOLATRIKONA.items():
            with self.subTest(planet=planet.name):
                self.assertEqual(MOOLATRIKONA_TABLE[planet], (sign, start, sign, end))

    def test_moolatrikona_ranges_are_half_open(self):
        """The start degree is inside and the end degree is outside."""
        for planet, (sign, start, end) in self.MOOLATRIKONA.items():
            with self.subTest(planet=planet.name):
                base = sign * 30.0
                self.assertTrue(is_in_moolatrikona(base + start, planet))
                self.assertTrue(is_in_moolatrikona(base + end - 0.01, planet))
                self.assertFalse(is_in_moolatrikona(base + end, planet))
                if start > 0:
                    self.assertFalse(is_in_moolatrikona(base + start - 0.01, planet))

    def test_mars_at_aries_15_is_own_sign_not_moolatrikona(self):
        """Mars at Aries 15 is own sign (moolatrikona ends at 12)."""
        self.assertFalse(is_in_moolatrikona(15.0, Planet.MARS))
        self.assertEqual(get_dignity_type(15.0, Planet.MARS), "Own Sign")

    def test_deep_exaltation_matches_bphs_3_49_50(self):
        """Deep exaltation and fall degrees equal BPHS 3.49-50."""
        for planet, (sign, deg) in self.DEEP_EXALTATION.items():
            with self.subTest(planet=planet.name):
                self.assertEqual(EXALTATION_TABLE[planet], (sign, deg))
                self.assertEqual(DEBILITATION_TABLE[planet], ((sign + 6) % 12, deg))


if __name__ == "__main__":
    unittest.main()
