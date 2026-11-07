# Ayanamsa and Precession Variance Modeling

## Mathematical Foundation

Vedic astrology operate on the Nirayana (sidereal) framework, necessitating precise mathematical correction for the precession of the equinoxes.

### The Ayanamsa Formula

The conversion from tropical longitude ($\lambda_{tropical}$) to sidereal longitude ($\lambda_{sidereal}$) is defined as:

$$\lambda_{sidereal} = \lambda_{tropical} - \epsilon_{ayanamsa}$$

Where $\epsilon_{ayanamsa}$ represents the chosen Ayanamsa value for the specific epoch.

## Precession Modeling

The rate of precession is approximately 50.3 arcseconds per year, but varies slightly over millennia. The Astro-Fusion framework utilizes the following differential equation to model the rate of change:

$$ \frac{d\epsilon}{dt} = P(t) $$

Where $P(t)$ is the polynomial representation of precession derived from modern astrometric observations (Standardized to J2000.0).

## Ayanamsa Models

| Model             | Baseline               | Mathematical Correction                                 |
| :---------------- | :--------------------- | :------------------------------------------------------ |
| **Lahiri**        | Spica (Chitra) at 180° | Proper motion of Spica correction over 2000-year epoch. |
| **Raman**         | 397 AD Baseline        | Surya Siddhanta translation to Cartesian coordinates.   |
| **Fagan-Bradley** | Babylonian Fixed Stars | Variance matrix calculation vs Lahiri.                  |

## Sandhi (Boundary) Analysis

Error-propagation analysis is performed when planetary bodies sit on the exact boundary of two signs. A shift of $\pm 0.0001^{\circ}$ can alter divisional chart architecture.

### Algorithmic Thresholds

- **Sign Sandhi:** $0^{\circ} 00' 00'' \pm 10''$
- **Nakshatra Sandhi:** $13^{\circ} 19' 50''$ to $13^{\circ} 20' 10''$
