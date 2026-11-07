# Natal Calculation API Specification

## Overview

The Natal Calculation API provides high-precision astronomical data and astrological chart states for third-party verification and internal consumption.

## Endpoints

### `POST /v1/calculate/chart`

Generates a comprehensive natal state.

**Payload:**

```json
{
  "dateTime": "2026-02-20T11:55:00Z",
  "location": {
    "latitude": 27.7172,
    "longitude": 85.324,
    "elevation": 1400
  },
  "config": {
    "ayanamsa": "Lahiri",
    "houseSystem": "Placidus",
    "topocentric": true
  }
}
```

**Response:**

```json
{
  "astronomical": {
    "positions": { "Sun": 305.4, "Moon": 42.1 },
    "precision": "High (Topocentric + Parallax)"
  },
  "astrological": {
    "rasi": [...],
    "bhava_chalit": [...],
    "varga": { "D9": [...], "D60": [...] }
  }
}
```

### `GET /v1/config/ayanamsa/models`

Returns the mathematical variance matrices for supported Ayanamsa models.

### `POST /v1/validate/yoga`

Input a chart state to receive a probabilistic scoring of all active Yogas.
