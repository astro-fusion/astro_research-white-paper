# 🌙 Real-Time Planetary Strength & Numerology Visualization

## What's New? ✨

The astro-research project has been enhanced with **real-time variant graphs** that display how planetary strengths and numerology values change over time. This is a significant advancement in understanding the dynamic relationship between Vedic Astrology and traditional numerology.

## 🎯 Key Features

### 1. **Planetary Strength Timeline**
- View the strength of all 9 Vedic planets (Navagraha) over a full year
- Interactive charts with hover tooltips and zoom controls
- Color-coded support zones (Excellent, Good, Weak, Poor)
- Identify optimal periods for important decisions

### 2. **Numerology vs Vedic Astrology Comparison**
- Compare your Mulanka (Birth Number) and Bhagyanka (Fortune Number) with actual planetary positions
- Identify periods of harmony and conflict between systems
- Visual alignment analysis for strategic timing

### 3. **Daily Numerology Tracker**
- Track daily Mulanka (Birth Number) changes
- Understand discrete vs. continuous astrological systems
- 30-day forecast with daily numerological guidance

## 📊 Visualizations Generated

The system automatically creates three interactive HTML dashboards:

1. **`planetary_strength_timeline.html`** (4.6 MB)
   - 365-day planetary strength overview
   - All 9 planets with individual trend lines
   - Support zone indicators (green/blue/orange/red)

2. **`numerology_vs_astrology_comparison.html`** (4.7 MB)
   - Dual-axis comparison of numerology and astrology
   - Alignment and divergence analysis
   - Harmony detection

3. **`daily_numerology_changes.html`** (4.6 MB)
   - Daily Mulanka number changes
   - 30-day focused view
   - Bhagyanka reference line

4. **`planetary_strength_dashboard.html`** (NEW!)
   - Beautiful central hub for all visualizations
   - Information about strength zones
   - Planet-to-number mapping guide
   - Quick access to all charts

## 🚀 Getting Started

### Quick Start

1. **View the Dashboard**:
   ```bash
   # Open in your web browser
   open planetary_strength_dashboard.html
   # or
   start planetary_strength_dashboard.html  # Windows
   ```

2. **Regenerate Charts** (with updated birth data):
   ```bash
   # Navigate to project directory
   cd astro-research
   
   # Activate virtual environment (if using)
   source venv/bin/activate
   
   # Run the visualization generator
   python create_planetary_strength_graph.py
   ```

### Installation Requirements

```bash
# Install required packages
pip install pandas numpy matplotlib plotly

# Or use the virtual environment setup
python3 -m venv venv
source venv/bin/activate
pip install pandas numpy matplotlib plotly
```

## 📖 Understanding the Data

### Vedic Numerology to Planet Mapping
| Number | Planet | Symbol | Characteristics |
|--------|--------|--------|-----------------|
| 1 | SUN (Surya) | ☀️ | Leadership, authority, vitality |
| 2 | MOON (Chandra) | 🌙 | Emotions, intuition, mind |
| 3 | JUPITER (Guru) | 🪐 | Expansion, wisdom, fortune |
| 4 | RAHU (North Node) | ⚛️ | Desires, worldly pursuits |
| 5 | MERCURY (Budha) | 💫 | Communication, intellect |
| 6 | VENUS (Shukra) | ✨ | Love, beauty, relationships |
| 7 | KETU (South Node) | 🌑 | Spirituality, liberation |
| 8 | SATURN (Shani) | ⏳ | Discipline, responsibility, time |
| 9 | MARS (Mangal) | 🔴 | Courage, energy, action |

### Strength Score Interpretation
- **75-100 (Green)**: Excellent support - ideal for important decisions
- **50-75 (Blue)**: Good support - favorable conditions
- **25-50 (Orange)**: Weak support - proceed with caution
- **0-25 (Red)**: Poor support - avoid critical decisions

## 💡 Practical Applications

### Career & Business
- Identify optimal times to launch new projects
- Plan important business decisions during peak planetary strength
- Negotiate contracts when favorable

### Personal & Relationships
- Plan important dates (marriage, engagements) during aligned periods
- Navigate relationship challenges during weak support periods
- Understand daily numerological influences

### Health & Wellness
- Schedule important medical procedures during favorable periods
- Time wellness initiatives with supportive planetary positions
- Follow daily numerology for personal guidance

### Travel & Events
- Plan journeys during good support periods
- Schedule events when both systems align
- Avoid critical travel during poor support periods

## 📁 File Structure

```
astro-research/
├── create_planetary_strength_graph.py      # Main visualization generator
├── planetary_strength_dashboard.html       # Central dashboard hub
├── planetary_strength_timeline.html        # 1-year planetary overview
├── numerology_vs_astrology_comparison.html # Alignment analysis
├── daily_numerology_changes.html          # Daily tracker
├── PLANETARY_STRENGTH_VISUALIZATION.md     # Detailed documentation
├── research_results.json                  # Data source
└── src/
    ├── vedic_astrology_core/
    │   └── visualization/
    │       └── radar_charts.py            # Visualization functions
    └── vedic_numerology/
        └── visualization.py               # Numerology visualization
```

## 🔧 Advanced Usage

### Customizing the Visualization

Edit `create_planetary_strength_graph.py` to customize:

```python
# Change number of days to display
visualizer.generate_time_series_data(days=730)  # 2 years instead of 1

# Use Matplotlib instead of Plotly
visualizer.plot_planetary_strength_timeline(use_plotly=False)

# Save as image file
visualizer.plot_planetary_strength_timeline(
    use_plotly=False,
    save_path='my_chart.png'
)
```

### Adding Custom Data

Update `research_results.json` with your birth data:

```json
{
  "birth_data": {
    "date": "YYYY-MM-DD",
    "time": "HH:MM",
    "latitude": 0.0,
    "longitude": 0.0
  },
  "numerology": {
    "mulanka": {"number": X, "planet": "PLANET_NAME"},
    "bhagyanka": {"number": Y, "planet": "PLANET_NAME"}
  }
}
```

Then regenerate the visualizations.

## 🌐 Browser Compatibility

| Browser | Status |
|---------|--------|
| Chrome/Chromium | ✅ Full Support |
| Firefox | ✅ Full Support |
| Safari | ✅ Full Support |
| Edge | ✅ Full Support |
| IE 11 | ⚠️ Limited |

**Note**: Interactive features require modern JavaScript support. For best experience, use Chrome, Firefox, Safari, or Edge.

## 📊 Technical Details

### Data Sources
- **Swiss Ephemeris**: High-precision astronomical calculations
- **Vedic Astrology Algorithms**: Traditional dignity and strength calculations
- **Vedic Numerology**: Anka Jyotish system

### Calculation Methods
- Planetary strength based on: position, dignity, houses, aspects, temporal factors
- Numerology based on: date reduction, Mulanka/Bhagyanka calculations
- Interpolation using astronomical principles and mathematical modeling

### Performance
- Chart file sizes: 4.6-4.7 MB (HTML + embedded data)
- Recommended RAM: 4GB+
- Load time: 2-5 seconds per chart (depends on internet connection)

## 🐛 Troubleshooting

### Charts Not Loading
**Solution**: Check internet connection (Plotly CDN) or use offline Matplotlib version

### Slow Performance
**Solution**: Use modern browser with hardware acceleration, or generate static images

### Data Seems Old
**Solution**: Update `research_results.json` and regenerate charts

### Module Not Found Errors
**Solution**: Install required packages with `pip install -r requirements.txt`

## 📚 References & Further Reading

See `PLANETARY_STRENGTH_VISUALIZATION.md` for:
- Detailed algorithm explanations
- Historical references
- Research methodology
- Complete technical specifications

## 🎓 Educational Value

These visualizations serve as educational tools for:
- **Vedic Astrology Students**: Understanding planetary strength calculations
- **Numerology Practitioners**: Seeing numerical influences in action
- **Researchers**: Analyzing correlations between systems
- **Curious Minds**: Exploring ancient knowledge through modern technology

## 🔐 Data Privacy

- All calculations are performed locally
- No data is sent to external servers
- Charts are self-contained HTML files
- Results are stored locally in JSON format

## 📝 License

This visualization system is part of the astro-research project and follows the same licensing terms.

## 🤝 Contributing

Improvements welcome! Please see CONTRIBUTING.md for guidelines.

## 📞 Support

For issues, questions, or suggestions:
1. Check PLANETARY_STRENGTH_VISUALIZATION.md for detailed documentation
2. Review the code comments in `create_planetary_strength_graph.py`
3. Examine example JSON data in `research_results.json`

## 🎉 What's Next?

Planned enhancements:
- Real-time planetary position updates
- Custom date range selection
- Predictive models for future strength
- Support for multiple ayanamsa systems
- Export to various formats
- Statistical analysis and trend detection
- Mobile-responsive designs

---

**Version**: 2.0
**Last Updated**: January 25, 2026
**Status**: Production Ready ✅

Happy exploring! 🌟
