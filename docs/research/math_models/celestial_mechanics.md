# Celestial Mechanics and Retrogradation Algorithms

## Retrograde Motion (Vakri)

Retrogradation is a geocentric illusion caused by the differing orbital velocities of Earth and other planets. In Vedic astrology, a retrograde planet (Vakri) is considered exceptionally strong (Cheshta Bala).

### Mathematical Derivation of Velocity

To isolate the stationary and retrograde phases, the system calculates the first derivative of longitude ($\lambda$) with respect to time ($t$):

$$ v = \frac{d\lambda}{dt} $$

- **Stationary (S):** $v \approx 0$
- **Retrograde (R):** $v < 0$
- **Direct (D):** $v > 0$

The second derivative ($a = \frac{dv}{dt}$) represents planetary acceleration, helping to identify the transition phases (entry into and exit from retrogradation).

## Atmospheric Refraction

Visual planetary positions near the horizon are altered by the Earth's atmosphere. Astro-Fusion implements the **Bennett Formula** (1982) for refraction correction ($R$):

$$ R = \frac{1}{\tan(h + \frac{7.31}{h + 4.4})} $$

Where $h$ is the apparent altitude in degrees. This value is adjusted based on localized environmental data:

- **Temperature:** $T$ (Standard 10°C)
- **Pressure:** $P$ (Standard 1010 mbar)

$$ R\_{corrected} = R \times \frac{P}{1010} \times \frac{283}{273 + T} $$

## Implementation Guardrails

- **Stationary Phase Detection:** Planets within $\pm 1\%$ of zero velocity are flagged as 'Stationary', triggering specific interpretive rules regarding "intensity" and "delay".
- **Luminaries Exclusion:** The Sun and Moon never undergo retrogradation; the code contains boolean checks to prevent erroneous retrograde flags for these bodies.
