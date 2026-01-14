Numerology Calculations
=======================

This guide explains the Vedic numerology calculations used in the system.

Mulanka (Birth Number)
----------------------

The Mulanka represents the birth number calculated from the date of birth with sunrise correction.

**Calculation Method:**

1. Convert birth date to Julian Day Number
2. Apply sunrise correction for birth location
3. Reduce the date number to a single digit (1-9)

**Example:**

.. code-block:: python

   from vedic_numerology.numerology import calculate_mulanka

   # Calculate Mulanka for Mars reference case
   result = calculate_mulanka("1984-08-27", "10:30", 28.6139, 77.1025)
   print(f"Mulanka: {result['number']} ({result['planet']})")
   # Output: Mulanka: 9 (Mars)

**Planetary Rulership:**

- 1: Sun (Surya)
- 2: Moon (Chandra)
- 3: Jupiter (Guru)
- 4: Uranus/Rahu (modern inclusion)
- 5: Mercury (Budha)
- 6: Venus (Shukra)
- 7: Neptune/Ketu (modern inclusion)
- 8: Saturn (Shani)
- 9: Mars (Mangal)

Bhagyanka (Destiny Number)
--------------------------

The Bhagyanka represents the destiny or life path number calculated from the full birth date and time.

**Calculation Method:**

1. Sum all digits of birth date and time
2. Apply name number influences if available
3. Reduce to a single digit with special master number consideration

**Example:**

.. code-block:: python

   from vedic_numerology.numerology import calculate_bhagyanka

   result = calculate_bhagyanka("1984-08-27", "10:30")
   print(f"Bhagyanka: {result['number']} ({result['planet']})")

Compound Numbers
----------------

Advanced numerological combinations that provide deeper insights.

**Karma Number:**
Sum of birth date digits representing karmic influences.

**Life Path Number:**
Combination of Mulanka and Bhagyanka for life journey analysis.

**Personal Year Number:**
Current year calculations for timing analysis.

Sunrise Correction
------------------

Vedic numerology traditionally uses sunrise correction for accurate birth number calculations.

**Why Sunrise Correction?**

- Accounts for the transition from one day to the next
- Aligns with Vedic day calculation principles
- Provides more accurate numerological timing

**Implementation:**

.. code-block:: python

   from vedic_numerology.numerology import calculate_sunrise_correction

   # Calculate sunrise time for birth location
   sunrise_correction = calculate_sunrise_correction(
       date="1984-08-27",
       latitude=28.6139,
       longitude=77.1025
   )

   print(f"Sunrise time: {sunrise_correction}")

Number Reduction
----------------

Standard method for reducing multi-digit numbers to single digits.

**Rules:**

1. Sum all digits: 1984 → 1+9+8+4 = 22
2. If result > 9, sum again: 22 → 2+2 = 4
3. Special handling for master numbers (11, 22, 33)

**Example:**

.. code-block:: python

   from vedic_numerology.numerology import reduce_to_single_digit

   # Reduce various numbers
   print(reduce_to_single_digit(1984))  # 22 → 4
   print(reduce_to_single_digit(1990))  # 19 → 1
   print(reduce_to_single_digit(2024))  # 8

Validation and Edge Cases
--------------------------

**Input Validation:**

- Date format: YYYY-MM-DD
- Time format: HH:MM (24-hour)
- Coordinates: Decimal degrees

**Edge Cases:**

- Leap year dates
- Timezone considerations
- Midnight births
- International date line crossings

**Error Handling:**

.. code-block:: python

   try:
       result = calculate_mulanka("invalid-date", "10:30", 28.6139, 77.1025)
   except ValueError as e:
       print(f"Error: {e}")
       # Handle invalid input gracefully

Integration with Astrology
--------------------------

Numerology calculations are designed to integrate with astrological analysis for comprehensive birth chart interpretation.

**Combined Analysis:**

.. code-block:: python

   from vedic_numerology import VedicNumerologyAstrology

   vna = VedicNumerologyAstrology("1984-08-27", "10:30", 28.6139, 77.1025)

   # Get both numerology and astrology
   mulanka = vna.calculate_mulanka()
   bhagyanka = vna.calculate_bhagyanka()

   # Check planetary support
   support = vna.analyze_support_contradiction()
   print(f"Mulanka {mulanka['number']} support: {support['mulanka']['support_level']}")

Customization Options
--------------------

**Ayanamsa Systems:**
Different ayanamsa systems can affect sunrise calculations.

**Calendar Systems:**
Support for different calendar conventions.

**Regional Variations:**
Cultural and regional numerological traditions.

Performance Considerations
---------------------------

**Optimization Features:**

- Cached calculations for repeated dates
- Efficient astronomical calculations
- Memory-efficient data structures

**Benchmarking:**

.. code-block:: python

   import time
   from vedic_numerology.numerology import NumerologyCalculator

   calc = NumerologyCalculator()
   start_time = time.time()

   # Benchmark calculation speed
   for i in range(1000):
       calc.calculate_mulanka("1984-08-27")

   elapsed = time.time() - start_time
   print(".4f")

References and Standards
------------------------

**Vedic Texts:**
- Ancient numerological treatises
- Classical calculation methods
- Traditional rulership systems

**Modern Research:**
- Statistical validation studies
- Cross-cultural comparisons
- Contemporary applications

**Implementation Standards:**
- Astronomical calculation precision
- Numerical accuracy requirements
- Computational efficiency benchmarks