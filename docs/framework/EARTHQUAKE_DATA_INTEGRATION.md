# Earthquake Data Integration Guide

## 📊 Data Format Requirements

### Earthquake Data CSV
**File location:** `use_cases/earthquake/data/raw/earthquakes.csv`

**Required columns:**
```csv
date,time,latitude,longitude,magnitude,depth_km,location
```

**Data types:**
- `date`: YYYY-MM-DD format
- `time`: HH:MM or HH:MM:SS format
- `latitude`: -90 to 90 (decimal degrees)
- `longitude`: -180 to 180 (decimal degrees)
- `magnitude`: 3.0 to 9.0+ (Richter scale)
- `depth_km`: 0 to 700+ (kilometers)
- `location`: String description

**Example rows:**
```csv
date,time,latitude,longitude,magnitude,depth_km,location
2023-01-15,10:30:45,35.5,139.5,6.2,50,Fukushima,Japan
2023-02-22,14:45:30,-35.2,-71.3,5.8,30,Bio-Bio,Chile
2023-03-10,06:15:00,38.2,35.0,5.1,10,Kahramanmaras,Turkey
```

### Planetary Data CSV
**File location:** `use_cases/earthquake/data/raw/planetary_positions.csv`

**Required columns:**
```csv
datetime,SUN_position,MOON_position,MARS_position,MERCURY_position,JUPITER_position,VENUS_position,SATURN_position,RAHU_position,KETU_position,SUN_strength,MOON_strength,MARS_strength,MERCURY_strength,JUPITER_strength,VENUS_strength,SATURN_strength,RAHU_strength,KETU_strength
```

**Data types:**
- `datetime`: YYYY-MM-DD HH:MM:SS format
- `*_position`: 0-360 degrees (zodiac position)
- `*_strength`: 0-100 score (strength level)

**Example rows:**
```csv
datetime,SUN_position,MOON_position,MARS_position,MERCURY_position,JUPITER_position,VENUS_position,SATURN_position,RAHU_position,KETU_position,SUN_strength,MOON_strength,MARS_strength,MERCURY_strength,JUPITER_strength,VENUS_strength,SATURN_strength,RAHU_strength,KETU_strength
2023-01-15,285.3,120.5,95.2,45.1,210.5,325.2,185.3,95.5,275.5,85.0,75.0,65.2,55.0,80.0,70.0,60.0,50.0,45.0
2023-01-16,286.2,135.2,96.1,46.0,211.2,326.1,185.8,95.8,275.2,85.2,80.0,66.1,55.5,80.1,70.5,60.1,50.1,45.1
```

---

## 🔗 Data Sources

### Earthquake Data
1. **USGS (United States Geological Survey)**
   - URL: https://earthquake.usgs.gov/earthquakes/search/
   - Data: Global earthquakes, magnitude 2.5+
   - Format: Export as CSV

2. **IRIS (Incorporated Research Institutions for Seismology)**
   - URL: https://www.iris.edu/hq/
   - Data: Seismic event data
   - Format: Multiple formats available

3. **EMSC (European-Mediterranean Seismological Centre)**
   - URL: https://www.emsc-csem.org/
   - Data: European/Mediterranean earthquakes
   - Format: Download as CSV

4. **International Seismological Centre (ISC)**
   - URL: https://www.isc.ac.uk/
   - Data: Comprehensive global catalog
   - Format: Multiple export options

### Planetary Data
1. **Swiss Ephemeris (Astro.com)**
   - Python library: `pyswisseph`
   - Installation: `pip install pyswisseph`
   - Calculates planetary positions for any date/time

2. **Vedic Astrology Calculators**
   - Your existing project calculations
   - Use existing strength calculation formulas

3. **Astronomical Libraries**
   - `skyfield` (Python)
   - `astropy` (Python)
   - Provide high-precision positions

---

## 🚀 Quick Start

### Option 1: Using Simulated Data (Testing)

```bash
cd /Users/bishalghimire/Documents/WORK/Open\ Source/astro-research
source venv/bin/activate

# Run with default simulated data
python use_cases/earthquake/scripts/earthquake_planetary_analysis.py
```

**Output:** `use_cases/earthquake/data/earthquake_planetary_correlation_analysis.json`

### Option 2: Using Real Data

**Step 1: Download earthquake data from USGS**
```bash
# Go to https://earthquake.usgs.gov/earthquakes/search/
# Download as CSV (1990-2024)
# Save to: use_cases/earthquake/data/raw/earthquakes.csv
```

**Step 2: Generate planetary data**
```python
import pandas as pd
from datetime import datetime
import pyswisseph as swe

# Configure Swiss Ephemeris
swe.set_ephe_path('/path/to/ephemeris')

start_date = datetime(1990, 1, 1)
end_date = datetime(2024, 12, 31)

dates = pd.date_range(start_date, end_date, freq='D')
data = []

for date in dates:
    jd = swe.utc_to_jd(date.year, date.month, date.day, 12, 0, 0)[0]
    
    # Calculate planets
    planets = {
        'SUN': swe.SUN,
        'MOON': swe.MOON,
        'MARS': swe.MARS,
        # ... etc
    }
    
    row = {'datetime': date}
    for name, planet_id in planets.items():
        pos, speed = swe.calc_ut(jd, planet_id)
        row[f'{name}_position'] = pos[0]
        # Calculate strength...
        row[f'{name}_strength'] = calculate_strength(pos[0], jd)
    
    data.append(row)

df = pd.DataFrame(data)
df.to_csv('use_cases/earthquake/data/raw/planetary_positions.csv', index=False)
```

**Step 3: Run analysis with real data**
```python
from earthquake_planetary_analysis import EarthquakeAstrologicalAnalysis

# Load real data
analyzer = EarthquakeAstrologicalAnalysis(
    'use_cases/earthquake/data/raw/earthquakes.csv'
)

# Don't regenerate - use loaded data
# analyzer.planetary_data = pd.read_csv('use_cases/earthquake/data/raw/planetary_positions.csv')

# Run correlations
results = analyzer.run_all_correlations()
analyzer.export_results_json('use_cases/earthquake/data/earthquake_analysis_real.json')

print(analyzer.generate_analysis_summary())
```

---

## 📋 Data Processing Checklist

### Before Running Analysis:

- [ ] Earthquake data CSV created with all required columns
- [ ] Date/time formats verified (YYYY-MM-DD and HH:MM:SS)
- [ ] Latitude/longitude values in valid ranges
- [ ] Magnitude values > 3.0 (usually)
- [ ] Planetary positions in 0-360 degree range
- [ ] Planetary strength scores in 0-100 range
- [ ] No missing values in critical columns (impute if needed)
- [ ] Datetime format consistent across all records

### Data Cleaning Script:

```python
import pandas as pd
import numpy as np

# Load data
df = pd.read_csv('earthquakes.csv')

# Clean earthquake data
df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'])
df['magnitude'] = pd.to_numeric(df['magnitude'], errors='coerce')
df['depth_km'] = pd.to_numeric(df['depth_km'], errors='coerce')
df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')

# Remove invalid records
df = df.dropna(subset=['magnitude', 'latitude', 'longitude'])
df = df[(df['magnitude'] >= 3.0) & (df['magnitude'] <= 9.5)]
df = df[(df['latitude'] >= -90) & (df['latitude'] <= 90)]
df = df[(df['longitude'] >= -180) & (df['longitude'] <= 180)]

# Save cleaned data
df.to_csv('earthquakes_cleaned.csv', index=False)
print(f"Cleaned {len(df)} earthquake records")
```

---

## 🔍 Data Exploration

### View Data Summary:

```python
import pandas as pd

# Load earthquake data
earthquakes = pd.read_csv('use_cases/earthquake/data/raw/earthquakes.csv')

print("=== EARTHQUAKE DATA SUMMARY ===")
print(f"Total records: {len(earthquakes)}")
print(f"\nDate range: {earthquakes['date'].min()} to {earthquakes['date'].max()}")
print(f"Magnitude range: {earthquakes['magnitude'].min()} to {earthquakes['magnitude'].max()}")
print(f"Average magnitude: {earthquakes['magnitude'].mean():.2f}")
print(f"\nRecords by magnitude:")
print(earthquakes['magnitude'].apply(lambda x: f"{int(x)}.x").value_counts().sort_index())
print(f"\nTop locations:")
print(earthquakes['location'].value_counts().head(10))

# Load planetary data
planets = pd.read_csv('use_cases/earthquake/data/raw/planetary_positions.csv')
print("\n=== PLANETARY DATA SUMMARY ===")
print(f"Total records: {len(planets)}")
print(f"Date range: {planets['datetime'].min()} to {planets['datetime'].max()}")

# Show correlation between earthquakes and planetary events
print("\n=== INITIAL OBSERVATIONS ===")
print(f"Earthquakes per year: {len(earthquakes) / (earthquakes['date'].max().year - earthquakes['date'].min().year):.1f}")
```

---

## 📊 Analysis Output

### Results JSON Structure:

```json
{
  "analysis_timestamp": "2026-01-25T...",
  "earthquake_count": 5000,
  "analysis_period": {
    "start": "1990-01-01",
    "end": "2024-12-31"
  },
  "conjunction_analysis": {
    "mangal_ketu": {
      "description": "Mars-Ketu conjunction",
      "result": {
        "conjunction": "MARS-KETU",
        "conjunctions_found": 145,
        "earthquakes_near_conjunction": 287,
        "expected_earthquakes": 245.3,
        "ratio_near_vs_expected": 1.17,
        "chi_square_statistic": 7.24,
        "total_earthquakes": 5000
      }
    }
  },
  "strength_trigger_analysis": {
    "mars_activation": {
      "description": "Mars in high strength",
      "result": {
        "earthquakes_during_high_strength": 1850,
        "earthquakes_during_low_strength": 3150,
        "ratio_observed_vs_expected": 1.05
      }
    }
  }
}
```

### Interpreting Results:

**Chi-square > 3.841** = Statistically significant (p < 0.05)
**Ratio > 1.5** = Strong correlation
**Ratio 1.0-1.5** = Weak correlation
**Ratio < 1.0** = Possible inverse effect

---

## 🔄 Automated Workflow

### Create Shell Script: `run_earthquake_analysis.sh`

```bash
#!/bin/bash

# Earthquake-Planetary Analysis Automation Script

set -e  # Exit on error

PROJECT_ROOT="/Users/bishalghimire/Documents/WORK/Open Source/astro-research"
cd "$PROJECT_ROOT"

echo "======================================"
echo "EARTHQUAKE-PLANETARY ANALYSIS"
echo "======================================"

# Activate environment
source venv/bin/activate

# Check if data exists
if [ ! -f "use_cases/earthquake/data/raw/earthquakes.csv" ]; then
    echo "❌ Earthquake data not found!"
    echo "   Download from: https://earthquake.usgs.gov/earthquakes/search/"
    echo "   Save to: use_cases/earthquake/data/raw/earthquakes.csv"
    exit 1
fi

if [ ! -f "use_cases/earthquake/data/raw/planetary_positions.csv" ]; then
    echo "❌ Planetary data not found!"
    echo "   Generate using Swiss Ephemeris or astrology calculations"
    exit 1
fi

# Run analysis
echo "Running correlation analysis..."
python use_cases/earthquake/scripts/earthquake_planetary_analysis.py

# Create QUARTO document
echo "Creating research document..."
quarto render use_cases/earthquake/manuscripts/earthquake_analysis.qmd

echo "✅ Analysis complete!"
echo "Results: use_cases/earthquake/data/earthquake_planetary_correlation_analysis.json"
echo "Document: use_cases/earthquake/manuscripts/earthquake_analysis.pdf"
```

**Run with:**
```bash
chmod +x run_earthquake_analysis.sh
./run_earthquake_analysis.sh
```

---

## 📝 QUARTO Template for Earthquake Analysis

Create file: `use_cases/earthquake/manuscripts/earthquake_analysis.qmd`

```markdown
---
title: "Earthquake-Planetary Correlation Analysis"
author: "Research Team"
date: today
format: pdf
bibliography: references.bib
---

## Abstract
This study analyzes the correlation between planetary positions and earthquake occurrence.

## 1. Introduction
Vedic astrology suggests that certain planetary combinations (e.g., Mars-Ketu) may 
influence tectonic activity. This data-driven study tests this hypothesis.

## 2. Methodology
We analyzed X years of earthquake data (N = 5000 events) against daily planetary 
positions using:
- Conjunction analysis (Mars-Ketu within 8 degrees)
- Strength trigger analysis (Mars strength > 75)
- Statistical validation (chi-square tests)

## 3. Results
[Results would be programmatically inserted here from JSON]

## 4. Discussion
[Interpretation of findings]

## 5. Conclusions
[Final conclusions]

## References
```

---

## ✅ Checklist Before Publishing

- [ ] Earthquake data downloaded and verified
- [ ] Planetary data generated and validated
- [ ] Analysis script runs without errors
- [ ] Results JSON generated successfully
- [ ] QUARTO document renders to PDF
- [ ] All figures/tables display correctly
- [ ] Statistical findings described accurately
- [ ] Conclusions supported by data
- [ ] Methods reproducible by others

---

**Next Step:** Download earthquake data and prepare CSV file for analysis!

