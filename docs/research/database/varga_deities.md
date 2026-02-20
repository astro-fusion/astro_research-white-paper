# Varga Divinities and Micro-Rulership Schemas

## Objective

To map the deepest layers of predictive Jyotish by accounting for the specific deities/archetypes ruling the microscopic divisions of the Varga charts, particularly the Shashtiamsha (D-60).

## Shashtiamsha (D-60) Deity Mapping

The D-60 chart divides a single sign (30°) into 60 parts of 30' each. Each part is ruled by a distinct deity.

### Schema Structure

```json
{
  "d60_mapping": [
    { "index": 1, "range": [0.0, 0.5], "deity": "Ghora", "nature": "Malefic", "description": "Terrible, fierce energy" },
    { "index": 2, "range": [0.5, 1.0], "deity": "Rakshasa", "nature": "Malefic", "description": "Demonic, destructive" },
    ...
    { "index": 60, "range": [29.5, 30.0], "deity": "Amrita", "nature": "Benefic", "description": "Immortal nectar, pure divinity" }
  ]
}
```

## Vargottama Aggregation Matrix

A planet's strength is multiplied when it occupies the same sign across multiple divisions.

| Count | State Name   | Power Multiplier |
| :---- | :----------- | :--------------- |
| 2     | Vargottama   | 1.5x             |
| 3     | Parijatamsa  | 2.5x             |
| 4     | Parvatamsa   | 4.0x             |
| 5     | Simhasanamsa | 7.0x             |

## Integration Logic

The interpretive engine scans the `d60_mapping` based on the exact arc-seconds of the planet's longitude. A planet in its exaltation sign in D-1 but in a 'Ghora' amsa in D-60 will have its positive results severely mitigated or transformed into a source of stress.
