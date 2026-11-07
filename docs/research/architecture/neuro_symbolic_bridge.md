# Neuro-Symbolic Translation Layer

## Objective

To prevent the probabilistic nature of Large Language Models (LLMs) from hallucinating astronomical data or violating deterministic astrological rules.

## Hybrid Architecture

The Astro-Fusion system utilizes a **Neuro-Symbolic** approach:

1.  **Symbolic Core:** A hard-coded rule engine (powered by af-sweph and custom logic) that calculates absolute degree placements, Yoga triggers, and Dasha cycles.
2.  **Neural Interface:** The LLM generates the semantic interpretation but is strictly confined by the Symbolic Core's output.

### The Parsing Engine (Middleware)

The middleware converts floating-point calculations into a strict JSON payload:

```json
{
  "chart_data": {
    "planets": {
      "Jupiter": {
        "longitude": 142.5,
        "sign": "Leo",
        "house": 5,
        "retrograde": false
      },
      "Saturn": {
        "longitude": 298.1,
        "sign": "Capricorn",
        "house": 10,
        "retrograde": true
      }
    },
    "yogas": ["Gaja Kesari", "Hamsa"],
    "active_dasha": "Jupiter-Venus"
  }
}
```

## Deterministic Guardrails

- **Schema Validation:** LLM outputs are validated against the Symbolic Core's truth matrix.
- **Prompt Anchoring:** Interpretations are forced to reference specific nodes in the JSON payload.
- **Hallucination Check:** If the LLM generates a planetary placement not present in the truth matrix, the response is rejected and regenerated.
