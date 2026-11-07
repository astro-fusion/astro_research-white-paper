# Topocentric vs Geocentric Parallax Computations

## The Geocentric Perspective

Standard interstellar ephemerides calculate planetary positions from the Earth's center. For most distant planets, the angular difference is negligible. However, for the Moon and high-precision Ascendant calculations, a geocentric model introduces significant error.

## The Topocentric Transformation

Topocentric calculations are taken from the observer's exact surface location. This requires adjusting for the Earth's radius and the observer's elevation.

### Parallax Correction Formula

The correction for planetary parallax ($\Delta p$) is calculated using:

$$\sin(\Delta p) = \frac{R_E}{d} \sin(z)$$

Where:

- $R_E$: Local radius of the Earth at the observer's latitude.
- $d$: Distance to the celestial body.
- $z$: Apparent zenith distance.

### Implementation in Astro-Fusion

The system utilizes spherical trigonometry to transform geocentric coordinates $(x, y, z)$ into topocentric coordinates $(x', y', z')$:

$$
\begin{bmatrix} x' \\ y' \\ z' \end{bmatrix} = \begin{bmatrix} x \\ y \\ z \end{bmatrix} - \rho \begin{bmatrix} \cos \phi' \cos \theta \\ \cos \phi' \sin \theta \\ \sin \phi' \end{bmatrix}
$$

Where:

- $\rho$: Distance from the Earth's center to the observer.
- $\phi'$: Geocentric latitude.
- $\theta$: Local sidereal time.

## Precision Impacts

| Body           | Max Geocentric Error | Significance                                 |
| :------------- | :------------------- | :------------------------------------------- |
| **Moon**       | up to ~1°            | Critical for Nakshatra/Dasha timing.         |
| **Mars/Venus** | up to ~20"           | Relevant for tight Yoga triggers.            |
| **Ascendant**  | ~1-2'                | Impacts fine-tuned divisional charts (D-60). |

## Atmospheric Refraction

The engine further applies the **Saemundsson formula** for atmospheric refraction correction, integrating temperature and barometric pressure data to adjust the visual horizon.
