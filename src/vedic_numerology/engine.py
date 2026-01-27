"""
Numerology Engine for Research Pipeline.

This module provides the rigorous numerological calculations required for the
Astro-Seismic correlation study, including:
- Universal Day Number (UDN)
- Master Number support (11, 22, 33)
- Universal Year calculation
- Lifecycle Period cycles (Base-9)

Reference:
- Pythagorean Numerology System
- Research Pipeline Doc Section 2.2.1
"""

from __future__ import annotations
from datetime import date
from typing import Dict, Union


class NumerologyEngine:
    """
    Core engine for calculating research-grade numerological features.

    Distinguishes between "Standard Reduction" (1-9) and "Master Number Preservation"
    (11, 22, 33) as required by the hypothesis that Master Numbers represent
    different energy signatures.
    """

    MASTER_NUMBERS = {11, 22, 33}

    @staticmethod
    def _reduce(number: int, preserve_master: bool = True) -> int:
        """
        Reduce a number to a single digit or keep Master Numbers.

        Args:
            number: The integer to reduce
            preserve_master: If True, returns 11, 22, 33 as is.
                             If False, reduces 11->2, 22->4, 33->6.

        Returns:
            Reduced number.
        """
        if number == 0:
            return 0

        current = number
        while current > 9:
            # Check for master numbers immediately if preserving
            if preserve_master and current in NumerologyEngine.MASTER_NUMBERS:
                return current

            # Sum digits
            current = sum(int(d) for d in str(current))

        return current

    def calculate_universal_day_number(
        self, target_date: date, preserve_master: bool = True
    ) -> int:
        """
        Calculate the Universal Day Number (UDN).

        Formula: Reduce(Year + Month + Day)
        This is the primary independent variable for the seismic correlation.

        Args:
            target_date: The date to analyze
            preserve_master: Whether to keep 11, 22, 33 distinct

        Returns:
            Numerological value of the day.
        """
        # Method: Add components first, then reduce.
        # Note: There are different schools (reduce each, then add vs add all then reduce).
        # Research Doc 2.2.1 example: March 14, 1997 -> 3 + 1+4 + 1+9+9+7 = 3 + 5 + 26 -> 34 -> 7
        # Which is effectively sum of digits of the full date string.

        # We will follow the method: Sum of (Year + Month + Day)
        # 1997 + 3 + 14 = 2014 -> 2+0+1+4 = 7.
        # This is mathematically equivalent to summing all digits modulo 9 (except for the master number stops).

        total_sum = target_date.year + target_date.month + target_date.day
        return self._reduce(total_sum, preserve_master=preserve_master)

    def calculate_universal_year_number(
        self, year: int, preserve_master: bool = True
    ) -> int:
        """
        Calculate the Universal Year Number.

        Args:
            year: The year (e.g. 2026)
            preserve_master: Whether to keep 11, 22, 33

        Returns:
            Reduced year number.
        """
        return self._reduce(year, preserve_master=preserve_master)

    def calculate_life_path_number(
        self, birth_date: date, preserve_master: bool = True
    ) -> int:
        """
        Calculate Life Path number (mostly for natal, but used here for consistency).

        Standard Method: Reduce(Year) + Reduce(Month) + Reduce(Day) -> Reduce Sum
        """
        reduced_year = self._reduce(birth_date.year, preserve_master)
        reduced_month = self._reduce(birth_date.month, preserve_master)
        reduced_day = self._reduce(birth_date.day, preserve_master)

        total = reduced_year + reduced_month + reduced_day
        return self._reduce(total, preserve_master)

    def get_day_features(self, target_date: date) -> Dict[str, int]:
        """
        Generate all numerological features for a given day.

        Returns:
            Dict containing UDN, UYN, and raw sums for analysis.
        """
        udn_master = self.calculate_universal_day_number(
            target_date, preserve_master=True
        )
        udn_reduced = self.calculate_universal_day_number(
            target_date, preserve_master=False
        )

        uyn_master = self.calculate_universal_year_number(
            target_date.year, preserve_master=True
        )

        return {
            "date_iso": target_date.isoformat(),
            "universal_day_number": udn_master,
            "universal_day_number_reduced": udn_reduced,
            "universal_year_number": uyn_master,
            "is_master_day": udn_master in self.MASTER_NUMBERS,
            "day": target_date.day,
            "month": target_date.month,
            "year": target_date.year,
        }
