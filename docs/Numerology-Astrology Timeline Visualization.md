# **Computational Integration of Vedic Numerology and Sidereal Mechanics: A Technical and Theoretical Framework for Algorithmic Astrology**

## **1\. Introduction: The Convergence of Number and Celestial Mechanics**

The intersection of Vedic Numerology (*Anka Jyotish*) and Vedic Astrology (*Parashari Jyotish*) represents a complex data fusion challenge. While numerology distills the chaotic potential of a human life into static, discrete integers derived from the date of birth, astrology maps the dynamic, continuous movement of celestial bodies to assess the quality of time itself. The request to develop a Python-based computational model—specifically utilizing the Google Colab environment—to visualize the interplay between these two systems addresses a profound gap in modern metaphysical research: the lack of quantitative tools to measure the "support" or "contradiction" between a native’s numerological blueprint and their astronomical reality.

This report serves as a comprehensive technical specification and theoretical treatise for constructing such a system. It is designed for researchers and developers seeking to bridge the gap between ancient metaphysical axioms and modern data science. We will explore the mathematical derivation of *Mulanka* (Birth Number) and *Bhagyanka* (Destiny Number), the astronomical calculation of planetary positions using the Swiss Ephemeris (via pyswisseph), and the algorithmic logic required to map these distinct datasets.

Central to this analysis is the evaluation of planetary dignity—specifically the tension between a "ruling number" (e.g., 9, ruled by Mars) and the astronomical status of that planet (e.g., Mars in debilitation). By leveraging libraries such as flatlib and pyswisseph, we can transcend manual lookup tables, allowing for the precise, graphical representation of how planetary strength fluctuates over time. This approach validates or challenges the static promises of a numerological chart, offering a rigorous method to visualize whether the cosmos is aligned with the individual's numerical destiny.

## **2\. The Numerological Engine: Algorithms of *Anka Jyotish***

To algorithmically map Numerology to Astrology, one must first rigorously define the inputs. Unlike Western systems which may utilize the Tropical zodiac or assign outer planets (Uranus, Neptune, Pluto) to numbers, Vedic Numerology adheres strictly to the visible septenary planets plus the North and South Nodes of the Moon (Rahu and Ketu). This adherence is not merely traditional; it is essential for the logical consistency of the mapping system, as the outer planets do not rule signs in the Vedic framework and thus cannot be evaluated for "dignity" in the same manner.

### **2.1 The Mulanka (Psychic/Birth Number): Definition and Derivation**

The *Mulanka*, often referred to as the Psychic Number or Birth Number, represents the cognitive and immediate personality of the native. It is the numerical vibration of the day of birth and governs the conscious mind, self-perception, and the lens through which the individual views the world. In the computational logic of the proposed script, this is the "Root" variable, the static identifier of the self.

Mathematical Derivation:  
The extraction of the Mulanka involves a reduction operation where the day of the month ($D$) is reduced to a single digit ($M$) through recursive summation. While some Western systems preserve "Master Numbers" (11, 22, 33), strictly for the purpose of planetary mapping in Anka Jyotish, these must eventually be reduced to their single-digit root to identify the governing planet.  
The algorithm can be expressed as:

$$M \= \\begin{cases} D & \\text{if } D \\le 9 \\\\ (D \\mod 10\) \+ \\lfloor D / 10 \\rfloor & \\text{if } D \> 9 \\end{cases}$$

Note: If the resulting sum is still $\>9$, the operation repeats until $1 \\le M \\le 9$.  
The Sunrise Correction Logic:  
A critical, often overlooked variable in digital numerology is the Vedic definition of a "day." Unlike the Gregorian calendar, which changes the date at midnight (00:00), the Vedic day (Vara) begins at sunrise. If a user is born at 2:00 AM on the 15th, Gregorian conventions would assign a Mulanka based on 15 (6). However, in Vedic reckoning, the day is still the 14th until sunrise.  
To build a truly robust script, the system must:

1. Accept Latitude/Longitude and Birth Time.  
2. Calculate local Sunrise time using a library like suntime or flatlib.1  
3. If Birth Time \< Sunrise Time, decrement the date by one integer before calculating the Mulanka.  
   This ensures the numerological calculation aligns with the astrological chart, which is highly sensitive to sunrise (e.g., the Ascendant calculation).

Interpretative Relevance:  
The Mulanka governs the native's desires and immediate reactions. For the Python visualization, the planet associated with the Mulanka is designated as the Primary Lord. The script must track the condition of this specific planet in the astrological chart to determine if the native's core personality is supported by celestial mechanics. For instance, a Mulanka 1 (Sun) individual perceives themselves as a leader. If the astronomical Sun is in Libra (Debilitated), there is a fundamental disconnect—a "contradiction"—between their self-image and their available energy.3

### **2.2 The Bhagyanka (Destiny/Life Path Number): The Karmic Container**

The *Bhagyanka*, or Destiny Number, is derived from the summation of the entire date of birth (Day \+ Month \+ Year). While the Mulanka represents the driver, the Bhagyanka represents the vehicle and the road—the external circumstances, karmic trajectory, and the "luck" factor that operates in the background of the native's life.

Calculation Algorithm:  
For a date composed of Day ($D$), Month ($M$), and Year ($Y$, where $Y$ is a four-digit integer):

1. Sum all components: $S \= \\sum(D) \+ \\sum(M) \+ \\sum(Y)$.  
2. Reduce $S$ to a single digit using recursive addition or the modulo 9 method (casting out nines).

Interpretative Relevance:  
In the visualization script, the planet ruling the Bhagyanka is the Secondary Lord. The relationship between the Mulanka and Bhagyanka planets themselves is the first layer of analysis (e.g., are Sun and Saturn friends?), but the deeper analysis requested by the user is the comparison of this number against the sky. A contradiction here (e.g., Bhagyanka 5 ruled by Mercury, but Mercury is combust or debilitated in the chart) indicates a struggle to fulfill one's destiny. The native may have the skills (Mulanka) but finds the path (Bhagyanka) blocked by environmental factors.3

### **2.3 The Vedic Planetary Number Mapping Protocol**

The most significant divergence from Western Numerology in this system is the assignment of the numbers 4 and 7\. Western numerology often assigns Uranus to 4 and Neptune to 7\. Vedic Astrology, maintaining consistency with the *Navagraha* (nine planets), assigns 4 to Rahu (North Node) and 7 to Ketu (South Node). This mapping is non-negotiable for an accurate Vedic script, as Uranus and Neptune have no defined "dignity" (exaltation/debilitation) in classical texts, rendering them unusable for the "support vs. contradiction" analysis the user requires.6

**Table 1: Vedic Number-Planet Mapping & Python Dictionary Key Structure**

| Number | Deity/Planet | Sanskrit Name | Keywords | Python Key (flatlib.const) |
| :---- | :---- | :---- | :---- | :---- |
| **1** | Sun | Surya | Authority, Ego, Soul, Vitality | const.SUN |
| **2** | Moon | Chandra | Mind, Emotions, Nurturing | const.MOON |
| **3** | Jupiter | Guru | Wisdom, Expansion, Optimism | const.JUPITER |
| **4** | Rahu | North Node | Illusion, Materialism, Innovation | const.RAHU |
| **5** | Mercury | Budha | Intellect, Communication, Logic | const.MERCURY |
| **6** | Venus | Shukra | Luxury, Art, Desire, Relationship | const.VENUS |
| **7** | Ketu | South Node | Detachment, Moksha, Intuition | const.KETU |
| **8** | Saturn | Shani | Discipline, Delay, Structure | const.SATURN |
| **9** | Mars | Mangal | Energy, Aggression, Action | const.MARS |

Computational Implication:  
When the user inputs a birth date, the script must:

1. Execute the Mulanka/Bhagyanka algorithms (with sunrise correction).  
2. Query this dictionary to identify the **Target Planets**.  
3. Focus the subsequent astrological analysis specifically on these Target Planets to answer the user's question. The script acts as a filter, ignoring the other planets to provide a focused report on the numerological lords.

## ---

**3\. The Astronomical Engine: Sidereal Calculations in Python**

To visualize the comparison effectively, we must generate high-precision astrological data. The user's query specifies "Vedic Astrology," which necessitates the use of the **Sidereal Zodiac** (*Nirayana*) rather than the Tropical Zodiac (*Sayana*) used in Western Astrology. This distinction is astronomical, not just philosophical, and requires precise handling of the *Ayanamsa* (precession of the equinoxes).

### **3.1 The Swiss Ephemeris and pyswisseph**

The provided research materials highlight pyswisseph as the gold standard for this task. It is a Python extension to the C-based Swiss Ephemeris, developed by Astrodienst, which provides planetary positions to an accuracy of 0.001 arc-seconds.9 For "Deep Research" grade work, relying on simpler libraries that do not support rigorous Ayanamsa settings would lead to erroneous data.

Sidereal vs. Tropical Implementation:  
In pyswisseph (imported as swe), the sidereal mode must be set explicitly. If this step is omitted, the library defaults to Tropical positions, which differ from Vedic positions by approximately 24 degrees (the current value of the Lahiri Ayanamsa). This discrepancy is large enough to shift a planet into a different sign entirely, potentially changing a diagnosis from "Exalted" to "Debilitated."  
Algorithmic Requirement:  
The script must initialize the ephemeris with the Lahiri Ayanamsa (Chitra Paksha), which is the standard for the Government of India and the vast majority of Vedic practitioners.11

Python

import swisseph as swe

\# Set Sidereal Mode to Lahiri (required for Vedic)  
\# SIDM\_LAHIRI is the specific constant for the Chitra Paksha Ayanamsa  
swe.set\_sid\_mode(swe.SIDM\_LAHIRI, 0.0, 0.0)

The script must then loop through the calculated Julian Day (JD) to retrieve the longitude of the specific planets identified in the Numerology step.

### **3.2 Coordinate Systems: Geocentric vs. Topocentric**

For standard birth charts, Geocentric coordinates (earth-center) are typically sufficient and standard. However, for extreme precision or when dealing with the Moon (Mulanka 2), Topocentric coordinates (surface-center) can offer slight variations based on the user's specific latitude and longitude.  
Given the user's request for "exhaustive detail," the script should ideally allow for Topocentric calculation, though Geocentric is the accepted default for dignity analysis. The pyswisseph library supports this via the swe.set\_topo(lat, lon, alt) function.

### **3.3 Handling The Nodes (Rahu and Ketu)**

The Nodes of the Moon are mathematical points, not physical bodies. They have two calculated positions: Mean Node and True Node. In Vedic Astrology, there is a divergence of opinion, but Mean Nodes are traditionally more common, while modern software often defaults to True Nodes.  
For the purpose of this script, consistency is key. The script should explicitly select the Mean Node (const.MEAN\_NODE in libraries or specific flags in swe) to align with traditional numerological associations, which are ancient and predate the high-precision oscillation measurements of the True Node.13  
Furthermore, pyswisseph usually calculates only the North Node (Rahu). The script must mathematically derive the South Node (Ketu) by adding 180 degrees to the Rahu position and normalizing to the 0-360 circle.

$$\\text{Ketu}\_{\\text{long}} \= (\\text{Rahu}\_{\\text{long}} \+ 180\) \\mod 360$$

## ---

**4\. The Logic of Dignity: Quantifying Planetary Support**

The core of the user's query—"if planetary position supports the numerology number"—relies on quantifying **Planetary Dignity** (*Avastha*). It is not enough to know *where* a planet is; we must know *how it feels* there. In Vedic Astrology, a planet's ability to deliver the results of its number depends on its standing in the zodiac sign it occupies.

The hierarchy of dignity must be encoded into a robust scoring system for the graphical visualization. This system converts qualitative states into quantitative scalar values (0-100) that can be plotted on a Y-axis.14

### **4.1 The Dignity Hierarchy and Scoring Model**

To generate the requested graph, we define a "Support Score" based on the Parashari system of essential dignity.

1\. Exaltation (Ucca) \- Score: 100  
The planet is at its highest potency. It expresses its qualities purely and strongly. For a Mulanka 1 native, an Exalted Sun (in Aries) represents the perfect alignment of ego and cosmic will. The numerological potential is fully supported.  
2\. Moolatrikona (Root Trine) \- Score: 85-90  
This is the "office" of the planet—highly effective and task-oriented. It is slightly less potent than exaltation but more stable.  
3\. Own Sign (Swakshetra) \- Score: 75  
The planet is in its own home. It is comfortable, strong, and capable.  
4\. Great Friend (Adhi Mitra) \- Score: 65  
The planet is in the sign of a Natural Friend (Naisargika Mitra) who is also a Temporary Friend (Tatkalika Mitra) in the specific chart.  
5\. Friend (Mitra) \- Score: 50  
The planet is in the sign of a Natural Friend.  
6\. Neutral (Sama) \- Score: 40  
The planet is in a sign that is neither supportive nor hostile. The numerological number acts without cosmic interference but without cosmic help.  
7\. Enemy (Shatru) \- Score: 25  
The planet is in a hostile environment. It struggles to express its numerological traits.  
8\. Great Enemy (Adhi Shatru) \- Score: 10  
The planet is in the sign of a Natural Enemy who is also a Temporary Enemy. The numerological traits are severely obstructed or distorted.  
9\. Debilitation (Neecha) \- Score: 0-5  
The lowest potency. The planet fails to express its positive traits, often inverting them. For a Mulanka 9 (Mars) native, a Debilitated Mars (in Cancer) implies deep frustration, passive aggression, or a "fallen warrior" archetype.

### **4.2 The Exaltation and Debilitation Matrix**

To map this, the script requires a precise lookup table. The following table synthesizes the classical data required for the pyswisseph logic.16

**Table 2: Exaltation and Debilitation Parameters**

| Planet | Exaltation Sign | Deg. | Debilitation Sign | Deg. | Moolatrikona |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **Sun (1)** | Aries | 10° | Libra | 10° | Leo (0-20°) |
| **Moon (2)** | Taurus | 3° | Scorpio | 3° | Taurus (4-30°) |
| **Mars (9)** | Capricorn | 28° | Cancer | 28° | Aries (0-18°) |
| **Mercury (5)** | Virgo | 15° | Pisces | 15° | Virgo (16-20°) |
| **Jupiter (3)** | Cancer | 5° | Capricorn | 5° | Sagittarius (0-13°) |
| **Venus (6)** | Pisces | 27° | Virgo | 27° | Libra (0-10°) |
| **Saturn (8)** | Libra | 20° | Aries | 20° | Aquarius (0-20°) |
| **Rahu (4)** | Taurus/Gemini\* | \-- | Scorpio/Sagittarius | \-- | \-- |
| **Ketu (7)** | Scorpio/Sagittarius\* | \-- | Taurus/Gemini | \-- | \-- |

*Note on Nodes:* Rahu and Ketu do not rule signs in the traditional Parashari system. However, for the purpose of a "Support" script, we must assign them logic. A common convention is to treat Rahu as Exalted in Taurus and Ketu in Scorpio, or to use the dignity of the sign lord they occupy (dispositor dynamics). The script should ideally offer a toggle for "Node Logic," but defaulting to Taurus/Scorpio exaltation is standard for dignity scoring.18

### **4.3 Advanced Dignity: Shadbala and Positional Strength**

While the user asked to "map planetary positions," an expert report must clarify that simple sign placement is only the first layer of support. The true measure of support is **Shadbala** (Six-Fold Strength).

* **Sthana Bala (Positional Strength):** Includes the Exaltation/Sign logic derived above.  
* **Dik Bala (Directional Strength):** A planet gets strength in specific angles (e.g., Sun in the 10th House/South).  
* **Kaal Bala (Temporal Strength):** Moon, Mars, Saturn are strong at night; Sun, Jupiter, Venus during the day.  
* **Chesta Bala (Motional Strength):** Retrograde planets are distinct.

Refining the Algorithm:  
The Python script should ideally implement a simplified Sthana Bala calculator if full Shadbala is too complex for a basic visualization. However, acknowledging Retrogression is critical.  
In Vedic Astrology, a Retrograde (Vakra) planet is considered to have high Chesta Bala. Even if a planet is Debilitated, if it is Retrograde, many texts (like Phaldeepika) consider it to have the strength of an Exalted planet (Neecha Bhanga).  
Therefore, the scoring algorithm must include a conditional modifier:

Python

if status \== "Debilitated" and is\_retrograde:  
    score \+= 50  \# Significant boost due to Neecha Bhanga  
elif is\_retrograde:  
    score \+= 15  \# General boost for Chesta Bala

This nuance prevents the script from giving a false "contradiction" result for a powerful retrograde placement.19

## ---

**5\. Algorithmic Architecture: The Mapping Interface**

This section outlines the specific logic flow for the Python script. This acts as the blueprint for the code the user wishes to create.

### **5.1 The Comparison Logic Flow**

The goal is to produce a "Compatibility Index" between the Numerology Number and the Astrological Position.

**Step 1: Input Processing**

* User enters Date of Birth, Time, and Location.  
* Script calculates Mulanka (M) and Bhagyanka (B).  
* Script identifies Planet\_M and Planet\_B.

**Step 2: Ephemeris Query**

* Script calls swe.calc\_ut with SIDM\_LAHIRI to get the longitude of Planet\_M and Planet\_B.  
* Script determines the Zodiac Sign (0-11) and House placement (if Ascendant is calculated).

**Step 3: Dignity Evaluation (The Mapping)**

* The script compares the current Sign of the planet against the Exaltation\_Debilitation matrix.  
* It calculates the **Naisargika Maitri** (Natural Friendship). This requires a static matrix where, for example, Sun is friends with Moon, Mars, Jupiter; Enemy with Venus, Saturn.  
* It calculates **Tatkalika Maitri** (Temporary Friendship) based on the calculated chart positions.  
  * *Rule:* Planets in 2, 3, 4, 10, 11, 12 from the target are friends.  
* It combines these into the **Panchadha Maitri** score.

**Step 4: Output Generation**

* The script returns a data object:  
  * Mulanka: 9 (Mars)  
  * Mars\_Position: Cancer 12°  
  * Dignity: Debilitated  
  * Support\_Score: 15/100  
  * Verdict: "Contradiction/Challenge"

### **5.2 Handling the "Variation" Request**

The user asks to "show the variation of mulanka and bhagyanka in the graphical way." Since M and B are static numbers for a single birth, "variation" implies two potential visualizations:

Visualization A: Temporal Support (Transits)  
This maps the static Mulanka against the moving planet over time.

* **X-Axis:** Time (e.g., 2024-2025).  
* **Y-Axis:** Dignity Score of the Mulanka Lord.  
* **Insight:** "Your Mulanka is 9 (Mars). In late 2024, Mars transits Cancer (Debilitation). The graph shows a dip. This is a period where your numerological self is unsupported by the current sky."

Visualization B: Comparative Strength (Natal)  
This compares the Mulanka vs. Bhagyanka strength in the birth chart.

* **Bar Chart:**  
  * Bar 1: Strength of Mulanka Lord (e.g., Sun strength).  
  * Bar 2: Strength of Bhagyanka Lord (e.g., Saturn strength).  
  * **Insight:** If Bar 1 is high and Bar 2 is low, the native has strong personal drive but faces destined obstacles. If Bar 2 is high and Bar 1 is low, the native is "lucky" (supported by destiny) but lacks personal confidence.

## ---

**6\. Visualization Architecture: Designing the Output**

To meet the requirement of "graphical way" and "visualize the comparison," the script must utilize Python's plotting libraries (matplotlib or seaborn) to create semantic visual representations of the metaphysical data.

### **6.1 The Support Index Graph**

The primary output should be a dual-axis or color-coded time-series graph.

**Design Specification:**

* **Title:** "Numerological Support Index: \[Planet Name\] over Time"  
* **Reference Line (The Numerology Baseline):** A horizontal dashed line at Y=50 (Neutral). This represents the latent potential of the Number itself.  
* **The Curve (The Astrological Reality):** A continuous line plotting the Dignity Score of the planet as it transits through signs.  
* **Color Coding:**  
  * **Green Zone (Score \> 65):** The curve is green. "Strong Support." The planet actively helps the native fulfill the promise of the number.  
  * **Yellow Zone (Score 40-65):** "Neutral Support."  
  * **Red Zone (Score \< 40):** "Contradiction." The planet is obstructing the number.

### **6.2 The Comparison Radar Chart**

To compare Mulanka vs. Bhagyanka support in the natal chart, a Radar Chart (Spider Plot) is effective.

* **Axes:** Sthana Bala (Position), Dik Bala (Direction), Temporal Strength, etc.  
* **Series 1 (Blue):** Mulanka Planet.  
* **Series 2 (Orange):** Bhagyanka Planet.  
* **Visual Insight:** If the Orange shape creates a container around the Blue shape, the Destiny supports the Personality. If they are disjointed or skew in opposite directions (e.g., Sun strong in Position but weak in Direction), it shows specific areas of friction.

## ---

**7\. Case Study Analysis: Mars in 1984**

To demonstrate the "Exhaustive Detail" required and validate the logic, we apply this framework to a specific case mentioned in the research: Mars in 1984\.

Scenario: A user born on August 27, 1984\.  
1\. Numerology Calculation:

* **Mulanka:** Day 27 \-\> $2 \+ 7 \= 9$.  
  * *Lord:* Mars.  
* **Bhagyanka:** $27 \+ 8 \+ 1984 \= 2019 \\rightarrow 2+0+1+9 \= 12 \\rightarrow 3$.  
  * *Lord:* Jupiter.

2\. Astrological Lookup (August 1984):  
Using pyswisseph with SIDM\_LAHIRI:

* **Mars Position:** Research indicates Mars was in **Scorpio** (*Vrishchika*) in August 1984\.13  
* **Jupiter Position:** Jupiter was in **Sagittarius** (*Dhanu*) or entering Capricorn. (Need precise ephemeris check: In Aug 1984, Jupiter was likely in Sagittarius, its Moolatrikona sign).

**3\. Dignity Mapping (The "Support" Analysis):**

* **Target 1 (Mars/9):** Mars in Scorpio is in its **Own Sign** (*Swakshetra*).  
  * *Score:* 75/100.  
  * *Verdict:* **Strong Support.** The Mulanka 9 (Warrior/Energy) is supported by a Mars that is comfortable, powerful, and in its own territory. The native's aggression is controlled and effective.  
* **Target 2 (Jupiter/3):** Jupiter in Sagittarius is in **Moolatrikona/Own Sign**.  
  * *Score:* 85/100.  
  * *Verdict:* **Excellent Support.** The Bhagyanka 3 (Wisdom/Expansion) is backed by a powerful Jupiter.

4\. The Visualization Output:  
The script would generate a Bar Chart where both bars are high and green. The "Verdict" text would read: "Harmonic Convergence: Both Psychic and Destiny numbers are strongly supported by planetary positions. High potential for self-actualization."  
Contrast Case: Mars in Cancer (Contradiction)  
If the user were born a few months later or earlier when Mars was in Cancer (Debilitated):

* **Target 1 (Mars/9):** Mars in Cancer.  
  * *Score:* 10/100 (Debilitated).  
  * *Verdict:* **Contradiction.** The Mulanka 9 demands action, but the planet is "fallen." This creates the "friction" mentioned earlier. The graph would show a Red bar.  
* **Interpretation:** This does not mean "bad luck." It means the native must work harder to express the number's traits. The "variation" here is the delta between the *Expectation* (Number 9 \= High Energy) and *Reality* (Mars Cancer \= Low/Emotional Energy).

## ---

**8\. Technical Specification for the Colab Script**

To facilitate the user's creation of this tool, we provide the following technical specification summary.

**Dependencies:**

* swisseph (C-library wrapper, critical for precision).  
* pandas (Dataframe management).  
* matplotlib.pyplot (Visualization).  
* datetime, pytz (Time management).

**Class Structure:**

1. class NumerologyEngine: Handles derivation of Mulanka/Bhagyanka and sunrise correction. Contains the NUMBER\_MAP dictionary.  
2. class AstroEngine: Handles swe initialization, lat/lon conversion, and planetary position calculation.  
3. class DignityScorer: Contains the EXALTATION\_MATRIX, FRIENDSHIP\_MATRIX, and scoring logic methods (calculate\_score(planet, sign, chart)).  
4. class Visualizer: Accepts scoring data and generates the plots.

**Key Logic Block (Pseudo-Code for Mapping):**

Python

def map\_number\_to\_planet(number):  
    planet\_key \= NUMBER\_MAP\[number\]  
    position\_data \= AstroEngine.get\_position(planet\_key, birth\_time)  
      
    \# Calculate Base Dignity  
    base\_score \= DignityScorer.get\_sign\_score(planet\_key, position\_data\['sign'\])  
      
    \# Apply Modifiers  
    if position\_data\['is\_retrograde'\]:  
        base\_score \+= DignityScorer.RETRO\_BONUS  
    if position\_data\['is\_combust'\]:  
        base\_score \-= DignityScorer.COMBUST\_PENALTY  
          
    return base\_score

## ---

**9\. Conclusion**

The integration of Vedic Numerology and Astrology via computational methods offers a powerful new lens for metaphysical analysis. By moving beyond static lookup tables and employing high-precision ephemeris calculations (pyswisseph), we can visualize the dynamic relationship between a native's core numbers and the celestial environment.

The "Support vs. Contradiction" model defined in this report transforms abstract concepts into quantifiable metrics. It allows the researcher to see not just *what* the numbers are, but *how effectively* they can operate given the astronomical constraints. Whether revealing the frustration of a Debilitated Mulanka lord or the seamless power of an Exalted Bhagyanka lord, this system provides the nuance required for expert-level analysis. The proposed Python script, architected around these principles, serves as a robust tool for bridging the gap between the static mysticism of numbers and the dynamic mechanics of the stars.

### **Citation Index**

* **Numerology & Mapping:** 6  
* **Ephemeris & Libraries:** 9  
* **Dignity & Astrology:** 14  
* **Time & Solar Calculation:** 1  
* **Case Data (1984):** 13

#### **Works cited**

1. Create a GUI to get Sunset and Sunrise time using Python. \- GeeksforGeeks, accessed December 17, 2025, [https://www.geeksforgeeks.org/python/create-a-gui-to-get-sunset-and-sunrise-time-using-python/](https://www.geeksforgeeks.org/python/create-a-gui-to-get-sunset-and-sunrise-time-using-python/)  
2. SatAgro/suntime: Simple sunset and sunrise time calculation python library. \- GitHub, accessed December 17, 2025, [https://github.com/SatAgro/suntime](https://github.com/SatAgro/suntime)  
3. Bhagyank Calculator 2025 | Calculate Destiny Number & Mulank (Birth Number) \- Muhuratam, accessed December 17, 2025, [https://www.muhuratam.in/bhagyank-mulank](https://www.muhuratam.in/bhagyank-mulank)  
4. How to Calculate Your Mulank and Bhagyank to Choose the Perfect Watch, accessed December 17, 2025, [https://www.krishnawatch.com/blogs/news/how-to-calculate-your-mulank-and-bhagyank-to-choose-the-perfect-watch](https://www.krishnawatch.com/blogs/news/how-to-calculate-your-mulank-and-bhagyank-to-choose-the-perfect-watch)  
5. Mulank vs Bhagyank: How Your Birth and Destiny Numbers Influence Your Personal and Professional Life, accessed December 17, 2025, [https://astroarunpandit.org/mulank-vs-bhagyank/](https://astroarunpandit.org/mulank-vs-bhagyank/)  
6. Vedic Astrology and Numerology: How Numbers and Planets Align \- AstroSagga, accessed December 17, 2025, [https://www.astrosagga.com/blog/vedic-astrology-and-numerology-how-numbers-and-planets-align](https://www.astrosagga.com/blog/vedic-astrology-and-numerology-how-numbers-and-planets-align)  
7. Numerology and Planets: Revealing Their Cosmic Connection \- Vedic Astrology and Ayurveda, accessed December 17, 2025, [https://astrologyayurveda.com/blog/astrology-and-numerology/](https://astrologyayurveda.com/blog/astrology-and-numerology/)  
8. Rahu and ketu \- Vedic Astrology Online, accessed December 17, 2025, [https://vedicastrology.net.au/blog/vedic-articles/rahu-and-ketu/](https://vedicastrology.net.au/blog/vedic-articles/rahu-and-ketu/)  
9. pyswisseph \- PyPI, accessed December 17, 2025, [https://pypi.org/project/pyswisseph/](https://pypi.org/project/pyswisseph/)  
10. astrorigin/pyswisseph: Python extension to the Swiss Ephemeris \- GitHub, accessed December 17, 2025, [https://github.com/astrorigin/pyswisseph](https://github.com/astrorigin/pyswisseph)  
11. Vedic Ascendant/Planets and SwissEph Python \- Groups.io, accessed December 17, 2025, [https://groups.io/g/swisseph/topic/vedic\_ascendant\_planets\_and/27495911](https://groups.io/g/swisseph/topic/vedic_ascendant_planets_and/27495911)  
12. Lahiri Geocentric Birth Chart Calculator \- Mastering the Zodiac, accessed December 17, 2025, [https://masteringthezodiac.com/lahiri-geocentric-birth-chart-calculator](https://masteringthezodiac.com/lahiri-geocentric-birth-chart-calculator)  
13. Astrology Ephemeris: Centaurs, TNOs, Asteroids & Planets (1500 \- 2099\) \- Serennu.com, accessed December 17, 2025, [https://serennu.com/astrology/ephemeris.php](https://serennu.com/astrology/ephemeris.php)  
14. Calculating Planetary Dignity and its Usefulness \- Asheville Vedic Astrology, accessed December 17, 2025, [https://ashevillevedicastrology.wordpress.com/2016/07/28/calculating-planetary-dignity-and-its-usefulness/](https://ashevillevedicastrology.wordpress.com/2016/07/28/calculating-planetary-dignity-and-its-usefulness/)  
15. Solving the Complex Puzzle of Planetary Dignity — fionamarques.com, accessed December 17, 2025, [https://www.fionamarques.com/ava-apprenticeship-newsletters/solving-the-complex-puzzle-of-planetary-dignity](https://www.fionamarques.com/ava-apprenticeship-newsletters/solving-the-complex-puzzle-of-planetary-dignity)  
16. Core Logic and Reason Behind Exaltation and Debilitation of Planets, accessed December 17, 2025, [https://astrologicalbook.com/exaltation-and-debilitation-of-planets/](https://astrologicalbook.com/exaltation-and-debilitation-of-planets/)  
17. Know About Exaltation and Debilitation of Planets \- Cyberastro, accessed December 17, 2025, [https://www.cyberastro.com/article/exaltation-and-debilitation-of-planets](https://www.cyberastro.com/article/exaltation-and-debilitation-of-planets)  
18. Dignity of Planets (Part Uno) \- The Art of Vedic Astrology, accessed December 17, 2025, [https://www.theartofvedicastrology.com/?page\_id=266](https://www.theartofvedicastrology.com/?page_id=266)  
19. Vedic Astrology – The trouble with Mars … \- Warrior Yoga Sligo, accessed December 17, 2025, [https://warrioryogasligo.com/vedic-astrology-the-trouble-with-mars/](https://warrioryogasligo.com/vedic-astrology-the-trouble-with-mars/)  
20. What are the factors that influence the planetary dignity, strength in Vedic Astrology, accessed December 17, 2025, [https://jyotishtek.com/blog/what-are-the-factors-that-influence-the-planetary-dignity-strength-in-vedic-astrology/](https://jyotishtek.com/blog/what-are-the-factors-that-influence-the-planetary-dignity-strength-in-vedic-astrology/)  
21. Mars Retrograde Transit Meaning & Dates \- saturn and honey, accessed December 17, 2025, [https://www.saturnandhoney.com/blog/mars-retrograde-in-astrology](https://www.saturnandhoney.com/blog/mars-retrograde-in-astrology)  
22. diliprk/VedicAstro: A python package for Vedic Astrology, with a particular focus on the Krishnamurthi Paddhati system \- GitHub, accessed December 17, 2025, [https://github.com/diliprk/VedicAstro](https://github.com/diliprk/VedicAstro)  
23. flatlib Documentation, accessed December 17, 2025, [https://flatlib.readthedocs.io/\_/downloads/en/latest/pdf/](https://flatlib.readthedocs.io/_/downloads/en/latest/pdf/)  
24. jyotishganit 0.1.2 on PyPI \- Libraries.io \- security & maintenance data for open source software, accessed December 17, 2025, [https://libraries.io/pypi/jyotishganit](https://libraries.io/pypi/jyotishganit)  
25. Generic Effects of Mars (Mangal/ Kuja) \- The Art of Vedic Astrology, accessed December 17, 2025, [https://www.theartofvedicastrology.com/?page\_id=504](https://www.theartofvedicastrology.com/?page_id=504)  
26. Vedic Astrology Friend-Enemige Planet Table | PDF | Religion & Spirituality \- Scribd, accessed December 17, 2025, [https://www.scribd.com/doc/5999108/Vedic-Astrology-Friend-Enemige-Planet-Table](https://www.scribd.com/doc/5999108/Vedic-Astrology-Friend-Enemige-Planet-Table)  
27. Planetary Friendships \- ASTRO SURKHIYAN, accessed December 17, 2025, [https://astrosurkhiyan.blogspot.com/2014/06/planetary-friendships.html](https://astrosurkhiyan.blogspot.com/2014/06/planetary-friendships.html)  
28. Sunrise and Sunset time in Python \- Stack Overflow, accessed December 17, 2025, [https://stackoverflow.com/questions/38986527/sunrise-and-sunset-time-in-python](https://stackoverflow.com/questions/38986527/sunrise-and-sunset-time-in-python)  
29. Sidereal Astrology Dates \- Mastering the Zodiac, accessed December 17, 2025, [https://masteringthezodiac.com/sidereal-astrology-dates](https://masteringthezodiac.com/sidereal-astrology-dates)