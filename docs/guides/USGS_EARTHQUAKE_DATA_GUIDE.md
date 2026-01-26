# 📍 USGS Earthquake Data Integration Guide

**Status**: ✅ Ready to Use  
**Data Source**: USGS Earthquake Hazards Program  
**Format**: CSV  

---

## 🎯 Quick Start - Get Real Data in 2 Steps

### **Step 1: Download from USGS**
Visit: https://earthquake.usgs.gov/earthquakes/search/

**Search Parameters:**
- **Magnitude**: 3.0 and greater
- **Date Range**: 1900-01-01 to today
- **Format**: CSV
- **Time Zone**: UTC

**Quick URL** (opens search page):
```
https://earthquake.usgs.gov/earthquakes/search/?starttime=1900-01-01&minmagnitude=3.0&orderby=time
```

### **Step 2: Save and Process**
```bash
# Save downloaded CSV as:
use_cases/earthquake/data/raw/earthquakes.csv

# Run analysis
python use_cases/earthquake/scripts/earthquake_planetary_analysis.py
```

---

## 📥 Detailed USGS Download Instructions

### **Method 1: USGS Web Interface (Recommended)**

1. **Go to USGS Earthquake Search**
   - URL: https://earthquake.usgs.gov/earthquakes/search/

2. **Set Search Parameters**
   ```
   Start Time:    1900-01-01 (or your desired start date)
   End Time:      (Today's date - automatically filled)
   Magnitude:     3.0+ (minimum for analysis)
   Region:        Worldwide (all)
   Depth:         Any (no filter)
   ```

3. **Export as CSV**
   - Click "Download" button
   - Select "CSV" format
   - File will be: `earthquakes.csv`

4. **Column Headers (should include)**
   ```
   time
   latitude
   longitude
   depth
   magnitude
   magType
   nst
   gap
   dmin
   rms
   net
   id
   updated
   place
   type
   horizontalError
   depthError
   magError
   magNst
   status
   locationSource
   magSource
   ```

### **Method 2: Programmatic Download (Python)**

```python
import pandas as pd
from datetime import datetime
import requests

# Download USGS earthquake data
def download_usgs_earthquakes(start_date, end_date, min_magnitude=3.0):
    """
    Download earthquake data from USGS API
    
    Parameters:
    - start_date: "YYYY-MM-DD" format
    - end_date: "YYYY-MM-DD" format
    - min_magnitude: minimum magnitude threshold
    
    Returns: pandas DataFrame with earthquake data
    """
    
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    
    params = {
        'format': 'csv',
        'starttime': start_date,
        'endtime': end_date,
        'minmagnitude': min_magnitude
    }
    
    print(f"📥 Downloading USGS earthquake data...")
    print(f"   Period: {start_date} to {end_date}")
    print(f"   Minimum Magnitude: {min_magnitude}")
    
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    # Save to file
    csv_path = 'use_cases/earthquake/data/raw/earthquakes.csv'
    with open(csv_path, 'w') as f:
        f.write(response.text)
    
    # Load into dataframe
    df = pd.read_csv(csv_path)
    
    print(f"✅ Downloaded {len(df)} earthquakes")
    print(f"   Saved to: {csv_path}")
    
    return df

# Example usage
if __name__ == "__main__":
    df = download_usgs_earthquakes(
        start_date="1990-01-01",
        end_date="2024-12-31",
        min_magnitude=3.0
    )
    
    print("\n📊 Data Summary:")
    print(f"   Date range: {df['time'].min()} to {df['time'].max()}")
    print(f"   Magnitude range: {df['magnitude'].min()} to {df['magnitude'].max()}")
    print(f"   Locations: {df['place'].nunique()} unique")
    print(f"   Data shape: {df.shape}")
```

**To run:**
```bash
pip install requests pandas
python scripts/download_usgs_data.py
```

### **Method 3: API Query (curl)**

```bash
# Download earthquakes from 1990-2024, magnitude 3.0+
curl "https://earthquake.usgs.gov/fdsnws/event/1/query?format=csv&starttime=1990-01-01&endtime=2024-12-31&minmagnitude=3.0" \
  -o use_cases/earthquake/data/raw/earthquakes.csv

# Verify download
echo "Downloaded $(wc -l < use_cases/earthquake/data/raw/earthquakes.csv) rows"
```

---

## 📋 Data Format Reference

### **Expected CSV Columns**
```
time                 # ISO 8601 datetime
latitude             # Epicenter latitude (-90 to 90)
longitude            # Epicenter longitude (-180 to 180)
depth                # Depth in kilometers
magnitude            # Earthquake magnitude
magType              # Type of magnitude (ml, ms, mw, etc.)
nst                  # Number of stations
gap                  # Azimuthal gap
dmin                 # Min distance to nearest station
rms                  # RMS travel time residual
net                  # Network code
id                   # Earthquake ID (USGS)
updated              # Last update timestamp
place                # Description of location
type                 # Event type (earthquake, etc.)
```

### **Data Sample**
```
time,latitude,longitude,depth,magnitude,magType,nst,gap,dmin,rms,net,id,updated,place,type,horizontalError,depthError,magError,magNst,status,locationSource,magSource
2024-01-15T10:30:45.123Z,35.891,-121.418,10.5,3.2,ml,45,60,0.5,0.02,ci,ci40218001,2024-01-15T10:35:22.040Z,"2 km NW of Cuyama, CA",earthquake,0.9,1.2,0.15,12,automatic,ci,ci
2024-01-15T09:45:12.456Z,-17.123,168.234,23.8,4.1,mw,89,45,1.2,0.05,us,us1000lyqp,2024-01-15T10:00:15.123Z,"36 km E of Nadi, Fiji",earthquake,1.1,2.3,0.11,25,reviewed,us,us
```

---

## 🔍 Data Validation

### **Check Downloaded Data**
```bash
# View first few rows
head -5 use_cases/earthquake/data/raw/earthquakes.csv

# Get summary statistics
wc -l use_cases/earthquake/data/raw/earthquakes.csv  # Count rows

# Check for completeness
awk -F',' '{
  if (NF != 21) print "Row with wrong column count: " NR " has " NF " columns"
}' use_cases/earthquake/data/raw/earthquakes.csv

# Validate date range
python3 << 'EOF'
import pandas as pd
df = pd.read_csv('use_cases/earthquake/data/raw/earthquakes.csv')
print(f"Earthquakes: {len(df)}")
print(f"Date range: {df['time'].min()} to {df['time'].max()}")
print(f"Magnitude range: {df['magnitude'].min()} to {df['magnitude'].max()}")
print(f"Missing values:\n{df.isnull().sum()}")
EOF
```

---

## 🗂️ File Organization

### **Expected Directory Structure**
```
use_cases/earthquake/
├── scripts/
│   └── earthquake_planetary_analysis.py
├── data/
│   ├── raw/
│   │   ├── earthquakes.csv              ← Your USGS download
│   │   └── planetary_positions.csv      ← Generated
│   └── earthquake_planetary_correlation_analysis.json  ← Results
└── manuscripts/
    └── earthquake_analysis.qmd
```

---

## 📊 Running Analysis with Real Data

### **Once You Have earthquakes.csv**

```bash
# 1. Verify file is in correct location
ls -lh use_cases/earthquake/data/raw/earthquakes.csv

# 2. Run analysis
python use_cases/earthquake/scripts/earthquake_planetary_analysis.py

# 3. Check results
cat use_cases/earthquake/data/earthquake_planetary_correlation_analysis.json
```

### **Expected Output**
```
✅ Analyzing 456 earthquakes
✅ Testing 6 planetary hypotheses
✅ Generating daily planetary positions
✅ Running correlation tests
✅ Results saved to JSON

Analysis Summary:
- Mars-Ketu conjunction correlation
- Mars-Saturn conjunction correlation
- Planetary strength triggers
- Statistical significance testing
```

---

## 📈 Alternative Data Sources

### **If USGS is unavailable**

| Source | URL | Coverage | Format |
|--------|-----|----------|--------|
| **IRIS** | https://www.iris.ds.iris.edu/ | Global seismic | Multiple |
| **EMSC** | https://www.emsc-csem.org/ | Europe/Mediterranean | CSV, XML |
| **ISC** | https://www.isc.ac.uk/ | International Seismic Centre | Multiple |
| **NEIC** | https://earthquake.usgs.gov/ | USGS National Earthquake | CSV |

---

## 💡 Tips & Best Practices

### **Data Size Considerations**
- **1990-2024 data** ≈ 50,000-100,000 earthquakes (3.0+ magnitude)
- **File size** ≈ 2-5 MB
- **Analysis time** ≈ 30-60 seconds

### **Filtering Options**
```python
# Get only high-magnitude earthquakes
df_filtered = df[df['magnitude'] >= 4.0]

# Get only recent earthquakes
df_filtered = df[df['time'] > '2020-01-01']

# Get specific regions
# Northern hemisphere
df_filtered = df[df['latitude'] > 0]

# Deep earthquakes
df_filtered = df[df['depth'] > 100]
```

### **Data Preprocessing**
```python
import pandas as pd

# Load data
df = pd.read_csv('use_cases/earthquake/data/raw/earthquakes.csv')

# Convert time to datetime
df['time'] = pd.to_datetime(df['time'])

# Sort by time
df = df.sort_values('time')

# Remove any duplicates
df = df.drop_duplicates(subset=['id'])

# Save cleaned data
df.to_csv('earthquakes_cleaned.csv', index=False)
```

---

## 🚀 Automated Download Script

Create `scripts/utilities/download_earthquake_data.py`:

```python
#!/usr/bin/env python3
"""
Automated USGS Earthquake Data Downloader
Downloads earthquake data and prepares for analysis
"""

import sys
import pandas as pd
from datetime import datetime
import requests
from pathlib import Path

def download_usgs_data(start_year=1990, min_magnitude=3.0):
    """Download USGS earthquake data"""
    
    start_date = f"{start_year}-01-01"
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    print(f"📥 Downloading earthquake data from USGS...")
    print(f"   Period: {start_date} to {end_date}")
    print(f"   Minimum Magnitude: {min_magnitude}")
    
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        'format': 'csv',
        'starttime': start_date,
        'endtime': end_date,
        'minmagnitude': min_magnitude
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"❌ Download failed: {e}")
        return False
    
    # Ensure directory exists
    data_dir = Path("use_cases/earthquake/data/raw")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Save to file
    csv_path = data_dir / "earthquakes.csv"
    with open(csv_path, 'w') as f:
        f.write(response.text)
    
    # Verify download
    df = pd.read_csv(csv_path)
    
    print(f"✅ Download successful!")
    print(f"   Records: {len(df)}")
    print(f"   Date range: {df['time'].min()} to {df['time'].max()}")
    print(f"   Magnitude range: {df['magnitude'].min():.1f} - {df['magnitude'].max():.1f}")
    print(f"   File saved: {csv_path}")
    
    return True

if __name__ == "__main__":
    success = download_usgs_data()
    sys.exit(0 if success else 1)
```

**Run it:**
```bash
python scripts/utilities/download_earthquake_data.py
```

---

## ✅ Checklist

- ⏳ Download USGS earthquake data (1990-2024, magnitude 3.0+)
- ⏳ Save to: `use_cases/earthquake/data/raw/earthquakes.csv`
- ⏳ Verify CSV has required columns
- ⏳ Run analysis: `python use_cases/earthquake/scripts/earthquake_planetary_analysis.py`
- ⏳ Check results in JSON output
- ⏳ View findings and statistical validation

---

## 📞 Support

**Issues with download?**
- Check USGS website: https://earthquake.usgs.gov/
- Verify internet connection
- Try different magnitude threshold
- Contact USGS support if API is down

**Questions about data?**
- See USGS FAQ: https://earthquake.usgs.gov/earthquakes/search/
- Read USGS documentation: https://earthquake.usgs.gov/fdsnws/

---

**Ready to download real data?** Follow the quick start steps above!
