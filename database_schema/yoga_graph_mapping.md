# Yoga Detection via Graph Mapping

## Problem Definition

Classical astrology identifies thousands of "Yogas" (planetary combinations). Traditional software uses iterative `IF/THEN` statements, which suffer from $O(N \times M)$ complexity (Planets $\times$ Yogas) and struggle with multi-level dependencies (e.g., "Lord of the 10th in the 9th, and the 9th lord is exalted").

## Graph-Based Architecture

Astro-Fusion maps astrological entities as nodes in a directed graph.

### Nodes

- **Graha (Planet):** Properties include dignity, longitude, lordship.
- **Bhava (House):** Properties include spatial coordinates, occupancy.
- **Rasi (Sign):** Properties include element, modality, ruler.

### Edges

- `RULES`: Relationship between planet and sign/house.
- `OCCUPIES`: Relationship between planet and house.
- `ASPECTS`: Relationship between planet/sign and other nodes.

## Yoga Trigger Optimization

Instead of linear scanning, the system uses graph traversals and pattern matching.

### Pattern Matching Example (Gaja Kesari Yoga)

Query: `MATCH (Moon:Planet)-[:KENDRA]-(Jupiter:Planet)`
The graph engine identifies the relationship instantly based on pre-calculated aspectual edges.

### Complex Yoga (Dharma Karmadhipati Yoga)

Query: `MATCH (P1:Planet)-[:RULES]->(H9:House), (P2:Planet)-[:RULES]->(H10:House), (P1)-[:CONJUNCT|ASPECT]-(P2)`

## Probabilistic Weighting

Each edge in the graph carries a weight determined by:

- **Shadbala:** Functional strength of the planet.
- **Dignity:** Relational strength (Exaltation, Debilitation).
- **Exactitude:** Tightness of the aspect.

The final Yoga score is the product of the participating node and edge weights, outputting a percentage of operational efficacy rather than a binary "True/False".
