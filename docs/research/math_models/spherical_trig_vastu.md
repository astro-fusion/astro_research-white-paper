# Spherical Trigonometry in Astro-Vastu

## Centroid Calculation (Brahmasthan) for Irregular Plots

Irregular plot shapes (non-convex polygons) represent a significant challenge in Vastu architecture. Determining the exact true centroid (Brahmasthan) is critical for grid alignment.

### Triangulation and Shoelace Formula

For a polygon with $n$ vertices $(x_i, y_i)$, the area $A$ is calculated using the Shoelace Formula:

$$ A = \frac{1}{2} \left| \sum*{i=1}^{n-1} (x_i y*{i+1} - x\_{i+1} y_i) + (x_n y_1 - x_1 y_n) \right| $$

The centroid $(\bar{x}, \bar{y})$ is then:

$$ \bar{x} = \frac{1}{6A} \sum*{i=1}^{n-1} (x_i + x*{i+1})(x*i y*{i+1} - x*{i+1} y_i) $$
$$ \bar{y} = \frac{1}{6A} \sum*{i=1}^{n-1} (y*i + y*{i+1})(x*i y*{i+1} - x\_{i+1} y_i) $$

## Marma Point Collision Detection

Marma points are highly sensitive energetic intersections on the Vastu Purusha Mandala. Heavy structural elements must not overlap these coordinates.

### Collision Logic

The system maintains a registry of Marma point coordinates $(X_m, Y_m)$. When a user inputs a structural element (wall or pillar), the system executes a collision check:

```python
def check_collision(element_geometry, marma_points):
    for point in marma_points:
        if element_geometry.contains(point):
            return "WARNING: Structural overlap on Marma point at " + str(point)
    return "SAFE"
```

## Geopathic Stress Mapping

The model integrates localized geomagnetic flux data to identify subterranean anomalies, superimposing these onto the architectural grid to fine-tune the remedial spatial placements.
