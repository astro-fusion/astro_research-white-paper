# Multi-Use-Case Validation Framework for Planetary Correlations

## 🎯 Overview

A comprehensive data-driven framework to analyze if various planetary combinations correlate with different phenomena:

1. **Numerology Use Case** ✅ (Already analyzed)
   - Question: Do Vedic Astrology and Numerology correlate?
   - Answer: NO (r ≈ 0.12) → Systems are independent

2. **Earthquake Use Case** 🔄 (In development)
   - Question: Do certain planetary combinations trigger earthquakes?
   - Hypotheses: Mangal-Ketu, Saturn positions, malefic clusters
   - Status: Framework ready for data integration

3. **Additional Use Cases** (Future)
   - Weather/Climate patterns
   - Economic cycles
   - Health epidemics
   - Political events
   - Social movements

---

## 📊 Framework Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA-DRIVEN ANALYSIS FRAMEWORK                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. DATA COLLECTION LAYER                                      │
│     ├─ Event Data (earthquakes, weather, etc.)                 │
│     ├─ Planetary Data (positions, strengths, aspects)          │
│     └─ Correlation Validation Data                             │
│                                                                 │
│  2. ANALYSIS ENGINE LAYER                                      │
│     ├─ Conjunction Analysis                                    │
│     ├─ Strength Trigger Analysis                               │
│     ├─ Clustering Analysis                                     │
│     └─ Temporal Correlation Analysis                           │
│                                                                 │
│  3. STATISTICAL VALIDATION LAYER                               │
│     ├─ Chi-square test                                         │
│     ├─ Pearson correlation                                     │
│     ├─ P-value significance testing                            │
│     └─ Effect size calculation                                 │
│                                                                 │
│  4. REPORTING LAYER                                            │
│     ├─ JSON Results Export                                     │
│     ├─ Markdown Documentation Generation                       │
│     ├─ QUARTO Integration                                      │
│     └─ PDF Generation (via QUARTO)                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🌍 Earthquake Analysis Use Case

### Research Questions

1. **Mangal-Ketu Conjunction**
   - Are earthquakes more frequent when Mars and Ketu are in conjunction?
   - Hypothesis: Malefic combination triggers tectonic activity
   - Test Method: Conjunction window analysis (±30 days)

2. **Mars-Saturn Conjunction**
   - Does Mars-Saturn conjunction correlate with seismic events?
   - Hypothesis: Combination of action + restriction = release
   - Test Method: Same conjunction window analysis

3. **Mars Strength Trigger**
   - Are earthquakes more likely when Mars is in high strength?
   - Hypothesis: Mars activation triggers earth movement
   - Test Method: Strength threshold analysis (>75 strength)

4. **Malefic Cluster**
   - Does clustering of Mars, Saturn, Rahu correlate with earthquakes?
   - Hypothesis: Multiple malefics = multiple energetic triggers
   - Test Method: Period-based clustering analysis

5. **Saturn in Strategic Positions**
   - Specific house/sign placements vs earthquake frequency
   - Hypothesis: Saturn restrictions = pressure release through earthquakes
   - Test Method: Positional cluster analysis

### Data Requirements

**Earthquake Data CSV Format:**
```csv
date,time,latitude,longitude,magnitude,depth_km,location
2023-01-15,10:30,35.5,139.5,6.2,50,Japan
2023-02-22,14:45,-35.2,-71.3,5.8,30,Chile
...
```

**Planetary Data CSV Format:**
```csv
datetime,SUN_position,MOON_position,...,MARS_strength,...
2023-01-15,285.3,120.5,...,65.2,...
2023-01-16,286.2,135.2,...,66.1,...
...
```

### Analysis Workflow

```python
# 1. Load data
analyzer = EarthquakeAstrologicalAnalysis('earthquake_data.csv')
analyzer.generate_planetary_data(start_date, end_date)

# 2. Run conjunction analysis
mangal_ketu = analyzer.analyze_conjunction_earthquake_correlation(
    'MARS', 'KETU', window_days=30
)

# 3. Run strength trigger analysis
mars_trigger = analyzer.analyze_planetary_strength_trigger(
    'MARS', strength_threshold=75.0
)

# 4. Run all correlations
all_results = analyzer.run_all_correlations()

# 5. Export & analyze
analyzer.export_results_json('earthquake_analysis.json')
```

### Expected Metrics

For each analysis, we calculate:

**Conjunction Analysis:**
- `conjunctions_found`: Number of conjunctions in period
- `earthquakes_near_conjunction`: Count near conjunction window
- `expected_earthquakes`: Random expectation (null hypothesis)
- `ratio_near_vs_expected`: Observed/Expected ratio
- `chi_square_statistic`: Statistical significance (p < 0.05 = significant)

**Strength Trigger Analysis:**
- `earthquakes_during_high_strength`: Count when planet is activated
- `earthquakes_during_low_strength`: Count when planet is weak
- `expected_earthquakes_during_high`: Random expectation
- `ratio_observed_vs_expected`: Activation effect size

**Interpretation Guide:**

| Metric | Value | Interpretation |
|--------|-------|---|
| chi_square_statistic | > 3.841 | Statistically significant (p < 0.05) |
| ratio_near_vs_expected | > 1.5 | Strong correlation |
| ratio_near_vs_expected | 1.0-1.5 | Weak correlation |
| ratio_near_vs_expected | 0.8-1.0 | Possible inverse correlation |
| ratio_near_vs_expected | < 0.8 | Likely no correlation |

---

## 📈 Multi-Use-Case Integration

### Phase 1: Individual Use Case Analysis ✅
- ✅ Numerology (complete)
- 🔄 Earthquake (in progress)
- ⏳ Weather/Climate (planned)

### Phase 2: Comparative Analysis
```
Use Case 1: Numerology-Astrology
├─ Correlation: r ≈ 0.12
├─ Significance: None
└─ Conclusion: Independent systems

Use Case 2: Earthquake-Planetary
├─ Conjunction correlations: [pending data]
├─ Strength trigger correlations: [pending data]
└─ Conclusion: [TBD]

Use Case 3: Weather-Planetary
├─ Expected analysis structure
└─ [To be developed]
```

### Phase 3: Pattern Recognition
- Meta-analysis across use cases
- Identify which planetary combinations are truly predictive
- Distinguish between coincidence and causation
- Build integrated model

### Phase 4: Publication & Validation
- Publish individual use case findings
- Present meta-analysis results
- Open peer review process
- Validate on hold-out test sets

---

## 🔧 Implementation: How to Add Data

### For Earthquake Analysis

**Step 1: Gather earthquake data**
```bash
# Create CSV file: use_cases/earthquake/data/earthquake_historical.csv
# Sources: USGS, IRIS, EMSC, etc.
```

**Step 2: Gather planetary data**
```bash
# Option A: Use Swiss Ephemeris (pyswisseph)
# Option B: Use existing astrology calculations
# Place in: use_cases/earthquake/data/planetary_data.csv
```

**Step 3: Run analysis**
```bash
cd /Users/bishalghimire/Documents/WORK/Open\ Source/astro-research
python use_cases/earthquake/scripts/earthquake_planetary_analysis.py
```

**Step 4: Review results**
```bash
# Results in: use_cases/earthquake/data/earthquake_planetary_correlation_analysis.json
```

**Step 5: Create QUARTO document**
```bash
# File: use_cases/earthquake/manuscripts/earthquake_analysis.qmd
# QUARTO will auto-generate PDF from markdown
```

---

## 📝 How to Create QUARTO Research Document

Create file: `use_cases/earthquake/manuscripts/earthquake_analysis.qmd`

```markdown
---
title: "Earthquake-Planetary Correlation Analysis"
author: "Your Name"
date: today
format: pdf
---

## Research Question
Is there a correlation between planetary positions/combinations and earthquakes?

## Methodology
The EarthquakeAstrologicalAnalysis framework analyzes:

- Planetary conjunctions (Mars-Ketu, Mars-Saturn, etc.)
- Planetary strength triggers (Mars activation)
- Statistical validation (chi-square, effect sizes)

## Data
- Earthquakes: [description of dataset]
- Planetary Data: [description of calculations]
- Analysis Period: [dates]

## Results

### Conjunction Analysis
[Include JSON results here, formatted as tables]

### Strength Trigger Analysis
[Include results here]

## Statistical Findings
[Describe significance levels]

## Conclusions
[Interpret findings]
```

Then run:
```bash
quarto render use_cases/earthquake/manuscripts/earthquake_analysis.qmd
```

This generates: `earthquake_analysis.pdf` automatically

---

## 🔄 Framework Extensibility

### To Add New Use Case:

1. **Create data loader**
```python
def _load_specific_event_data(filename):
    # Load your specific event data
    return df
```

2. **Define correlation tests**
```python
COMBINATIONS_TO_TEST = {
    'your_hypothesis': {
        'planets': [...],
        'type': 'conjunction',
        'description': '...'
    }
}
```

3. **Implement analysis method**
```python
def analyze_your_correlation(self, ...):
    # Your specific analysis logic
    return results_dict
```

4. **Run in main**
```python
results = analyzer.run_all_correlations()
analyzer.export_results_json('results.json')
```

5. **Create QUARTO document**
```
Document → auto PDF via QUARTO
```

---

## 📊 Data-Driven Approach Benefits

✅ **Reproducible** - Same data, same analysis → same results  
✅ **Falsifiable** - Can prove correlations wrong with data  
✅ **Transparent** - All methods documented and open  
✅ **Extensible** - Easy to add new use cases  
✅ **Scalable** - Handle large datasets programmatically  
✅ **Publishable** - Meet academic standards  
✅ **Automated** - QUARTO auto-generates publications from data

---

## 🎯 Next Steps

### Immediate (Earthquake Analysis)
1. Gather historical earthquake data (1990-2024)
2. Generate/obtain planetary positions for same period
3. Run analysis script
4. Create QUARTO research document
5. Publish results

### Medium-term (Additional Use Cases)
1. Identify weather/climate patterns
2. Gather economic data
3. Implement parallel analysis frameworks
4. Compare results across use cases

### Long-term (Meta-analysis)
1. Synthesize findings from multiple use cases
2. Identify robust planetary indicators
3. Build integrated prediction model
4. Validate on held-out test data

---

## 📚 Reference Architecture

```
Project Root
├── use_cases/
│   ├── numerology/           [✅ COMPLETE]
│   │   ├── data/
│   │   │   └── correlation_analysis.json
│   │   ├── manuscripts/
│   │   │   └── numerology_analysis.qmd
│   │   └── scripts/
│   │       └── analysis.py
│   │
│   ├── earthquake/           [🔄 IN PROGRESS]
│   │   ├── data/
│   │   │   ├── earthquake_historical.csv
│   │   │   ├── planetary_data.csv
│   │   │   └── earthquake_planetary_correlation_analysis.json
│   │   ├── manuscripts/
│   │   │   └── earthquake_analysis.qmd  [TO CREATE]
│   │   └── scripts/
│   │       └── earthquake_planetary_analysis.py  [CREATED]
│   │
│   ├── weather/              [⏳ PLANNED]
│   │   ├── data/
│   │   ├── manuscripts/
│   │   └── scripts/
│   │
│   └── economics/            [⏳ PLANNED]
│       ├── data/
│       ├── manuscripts/
│       └── scripts/
│
├── docs/
│   └── [QUARTO-generated PDFs from markdown files]
│
└── research_results/
    └── [JSON analysis results from all use cases]
```

---

## ✨ Summary

**This framework enables:**
- Multiple parallel use case validation
- Data-driven hypothesis testing
- Statistical rigor
- Reproducibility
- Easy publication (via QUARTO)
- Extensibility (add new use cases easily)

**Current Status:**
- Numerology use case: ✅ Complete
- Earthquake use case: 🔄 Framework ready, awaiting data
- Future use cases: Ready to implement

**Next Action:** Load earthquake data and run analysis script

