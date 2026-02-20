# Epistemic Transparency and Confidence Scoring

## Objective

To provide users with a mathematical measure of the reliability of an automated astrological interpretation, accounting for data quality, rule complexity, and algorithmic bias.

## Confidence Score ($S_c$) Derivation

The interpretation confidence is calculated as a weighted average of three primary indices:

$$ S_c = w_1 I_a + w_2 I_r + w_3 I_b $$

### 1. Astrometric Index ($I_a$)

Measures the precision of initial celestial conditions.

- **Topocentric + Elevation:** 1.0
- **Geocentric:** 0.8
- **Unknown Birth Time (approx):** 0.4 - 0.6

### 2. Rule Consistency Index ($I_r$)

Measures the harmony or dissonance between active astrological rules.

- **Congruent Indicators:** (e.g., Exalted Lord + Benefic Sub-period) $\to$ High $I_r$.
- **Contradictory Indicators:** (e.g., Exalted Lord + Debilitated Dispositor) $\to$ Lower $I_r$.

### 3. Bias Correction Index ($I_b$)

Adjusts for LLM stochasticity and historical data bias.

- Uses **Cosine Similarity** between current interpretation and established classical baseline vectors.

## User Presentation

Confidence scores are presented as percentages:

- **90-100%:** Deterministic (Highly Reliable)
- **70-89%:** Probabilistic (Probable Outcome)
- **<70%:** Speculative (Requires Human Verification)
