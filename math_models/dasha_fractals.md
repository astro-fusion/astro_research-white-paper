# Dasha Fractals and Conditional Applicability

## The Fractal Nature of Time

Vimshottari Dasha systems operate on a fractal logic, where a 120-year cycle $(Mahadasha)$ is recursively divided into sub-periods:

- **Antardasha:** Level 2
- **Pratyantardasha:** Level 3
- **Sookshma Dasha:** Level 4
- **Prana Dasha:** Level 5

### Temporal Resolution

At the level of the Prana Dasha, the time resolution reaches minutes and seconds, necessitating the high-precision topocentric ephemeris calculations documented in `math_models/ephemeris_precision.md`.

## Conditional Dasha Activation

Universal application of Vimshottari is the default. However, Astro-Fusion implements boolean logic to trigger conditional Dashas based on birth chart criteria.

### Logic Tree Example

| Dasha System          | Activation Criteria (Boolean)    |
| :-------------------- | :------------------------------- |
| **Dwisaptati Sama**   | `IF (Ascendant_Lord.house == 7)` |
| **Chathurasiti Sama** | `IF (L10.house == 10)`           |
| **Shashtihayani**     | `IF (Sun.house == 1)`            |

## Double-Transit (Gochar) Superimposition

The model cross-references the active Dasha lord with real-time transits $(Gochar)$.

$$ P(\text{Event}) = f(\text{Dasha_Strength}) \times g(\text{Transit_Trigger}) $$

Where the Transit Trigger is maximized when **Transit Jupiter** and **Transit Saturn** simultaneously aspect the natal house activated by the Dasha lord.
