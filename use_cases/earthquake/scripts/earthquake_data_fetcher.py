"""
USGS Earthquake Data Fetcher

Fetches earthquake data from the USGS Earthquake Hazards Program API
and processes it for astrological correlation analysis.

Features:
- Fetch from USGS API (free, no authentication)
- Support for date ranges and magnitude filtering
- Local file fallback for testing
- Multiple data source options
"""

import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import os
from pathlib import Path


class EarthquakeDataFetcher:
    """Fetch and process earthquake data from multiple sources."""
    
    # USGS API endpoint
    USGS_API_BASE = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    
    # Default parameters
    DEFAULT_MAGNITUDE = 5.0
    DEFAULT_FORMAT = "geojson"
    
    def __init__(self, use_sample_data: bool = True, verbose: bool = False):
        """
        Initialize the earthquake data fetcher.
        
        Args:
            use_sample_data: If True, use local sample data for testing
            verbose: If True, print detailed logging
        """
        self.use_sample_data = use_sample_data
        self.verbose = verbose
        self.sample_data_path = Path(__file__).parent.parent / "data" / "sample_earthquakes.json"
    
    def fetch_earthquakes(
        self,
        start_date: str,
        end_date: str,
        min_magnitude: float = DEFAULT_MAGNITUDE,
        use_usgs_api: bool = False
    ) -> Dict:
        """
        Fetch earthquake data.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            min_magnitude: Minimum magnitude to retrieve
            use_usgs_api: If True, fetch from USGS API; else use local data
            
        Returns:
            Dictionary with earthquake data
        """
        if self.use_sample_data and not use_usgs_api:
            return self._load_sample_data()
        
        if use_usgs_api:
            try:
                return self._fetch_from_usgs_api(start_date, end_date, min_magnitude)
            except Exception as e:
                self._log(f"USGS API fetch failed: {e}. Falling back to sample data.")
                return self._load_sample_data()
        
        return self._load_sample_data()
    
    def _fetch_from_usgs_api(
        self,
        start_date: str,
        end_date: str,
        min_magnitude: float
    ) -> Dict:
        """
        Fetch data from USGS Earthquake API.
        
        API Documentation:
        https://earthquake.usgs.gov/fdsnws/event/1/
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            min_magnitude: Minimum magnitude
            
        Returns:
            GeoJSON formatted earthquake data
            
        Example:
            https://earthquake.usgs.gov/fdsnws/event/1/query?
                starttime=2020-01-01&
                endtime=2020-12-31&
                minmagnitude=5.0&
                format=geojson
        """
        self._log(f"Fetching earthquakes from USGS API...")
        self._log(f"  Period: {start_date} to {end_date}")
        self._log(f"  Minimum magnitude: {min_magnitude}")
        
        params = {
            "starttime": start_date,
            "endtime": end_date,
            "minmagnitude": min_magnitude,
            "format": self.DEFAULT_FORMAT,
            "orderby": "magnitude-desc"
        }
        
        try:
            response = requests.get(self.USGS_API_BASE, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            self._log(f"✅ Retrieved {len(data.get('features', []))} earthquakes")
            
            return data
        
        except requests.exceptions.RequestException as e:
            self._log(f"❌ Error fetching from USGS API: {e}")
            raise
    
    def _load_sample_data(self) -> Dict:
        """Load sample earthquake data for testing."""
        if self.sample_data_path.exists():
            self._log(f"Loading sample earthquake data from {self.sample_data_path}")
            with open(self.sample_data_path, 'r') as f:
                return json.load(f)
        else:
            self._log(f"⚠️  Sample data not found at {self.sample_data_path}")
            return self._create_mock_data()
    
    def _create_mock_data(self) -> Dict:
        """Create mock earthquake data for testing."""
        self._log("Creating mock earthquake data...")
        
        # Generate 20 mock earthquakes
        features = []
        base_date = datetime(2020, 1, 1)
        
        locations = [
            {"name": "Japan (Honshu)", "lon": 139.6, "lat": 37.6},
            {"name": "Indonesia", "lon": 113.6, "lat": -2.1},
            {"name": "Chile", "lon": -71.5, "lat": -30.0},
            {"name": "Peru", "lon": -75.3, "lat": -9.2},
            {"name": "Mexico", "lon": -96.8, "lat": 15.6},
        ]
        
        for i in range(20):
            date = base_date + timedelta(days=i*5)
            location = locations[i % len(locations)]
            
            feature = {
                "type": "Feature",
                "properties": {
                    "mag": 5.0 + (i % 3),
                    "place": location["name"],
                    "time": int(date.timestamp() * 1000),
                    "updated": int(date.timestamp() * 1000),
                    "url": f"https://earthquake.usgs.gov/earthquakes/events/{i}"
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [location["lon"], location["lat"], 10.0]
                }
            }
            features.append(feature)
        
        return {
            "type": "FeatureCollection",
            "metadata": {
                "generated": int(datetime.now().timestamp() * 1000),
                "url": "MOCK DATA",
                "title": "USGS Earthquake Data (Mock)",
                "status": 200,
                "api": "1.8.1",
                "count": len(features)
            },
            "features": features
        }
    
    def process_for_analysis(self, earthquake_data: Dict) -> List[Dict]:
        """
        Process USGS GeoJSON data into analysis format.
        
        Converts GeoJSON features into dictionaries with:
        - Date (for natal chart calculation)
        - Magnitude
        - Location
        - Coordinates
        
        Args:
            earthquake_data: GeoJSON formatted earthquake data
            
        Returns:
            List of processed earthquake dictionaries
        """
        processed = []
        
        for feature in earthquake_data.get("features", []):
            props = feature.get("properties", {})
            coords = feature.get("geometry", {}).get("coordinates", [])
            
            # Convert timestamp (milliseconds) to datetime
            timestamp_ms = props.get("time", 0)
            eq_date = datetime.fromtimestamp(timestamp_ms / 1000)
            
            processed_eq = {
                "date": eq_date.strftime("%Y-%m-%d"),
                "time": eq_date.isoformat(),
                "magnitude": props.get("mag", 0),
                "place": props.get("place", "Unknown"),
                "latitude": coords[1] if len(coords) > 1 else 0,
                "longitude": coords[0] if len(coords) > 0 else 0,
                "depth_km": coords[2] if len(coords) > 2 else 0,
                "usgs_url": props.get("url", ""),
            }
            processed.append(processed_eq)
        
        return processed
    
    def save_to_file(self, earthquakes: List[Dict], output_path: str) -> None:
        """Save processed earthquakes to JSON file."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(earthquakes, f, indent=2)
        
        self._log(f"✅ Saved {len(earthquakes)} earthquakes to {output_path}")
    
    def _log(self, message: str) -> None:
        """Print log message if verbose mode is enabled."""
        if self.verbose:
            print(f"[EarthquakeDataFetcher] {message}")


def main():
    """Example usage of the earthquake data fetcher."""
    import sys
    
    # Initialize fetcher
    fetcher = EarthquakeDataFetcher(use_sample_data=True, verbose=True)
    
    # Option 1: Use sample data (default)
    print("\n" + "="*60)
    print("OPTION 1: Using Sample Data (Default)")
    print("="*60)
    
    raw_data = fetcher.fetch_earthquakes(
        start_date="2020-01-01",
        end_date="2020-12-31",
        use_usgs_api=False
    )
    
    print(f"✅ Loaded {len(raw_data.get('features', []))} earthquake records")
    
    # Process data
    processed = fetcher.process_for_analysis(raw_data)
    print(f"✅ Processed {len(processed)} earthquakes for analysis")
    
    # Show sample
    if processed:
        print("\nSample earthquake:")
        print(f"  Date: {processed[0]['date']}")
        print(f"  Magnitude: {processed[0]['magnitude']}")
        print(f"  Location: {processed[0]['place']}")
    
    # Option 2: Fetch from USGS API (requires internet)
    print("\n" + "="*60)
    print("OPTION 2: Fetch from USGS API (Uncomment to use)")
    print("="*60)
    print("""
    # Uncomment to fetch real data from USGS
    # Note: Requires internet connection
    
    try:
        raw_data = fetcher.fetch_earthquakes(
            start_date="2020-01-01",
            end_date="2020-12-31",
            min_magnitude=5.0,
            use_usgs_api=True  # Use real USGS data
        )
        print(f"✅ Fetched {len(raw_data.get('features', []))} earthquakes from USGS")
    except Exception as e:
        print(f"❌ Error: {e}")
    """)
    
    print("\n" + "="*60)
    print("Integration Ready!")
    print("="*60)
    print("""
    This fetcher integrates with:
    - use_cases/earthquake/scripts/earthquake_planetary_analysis.py
    - GitHub Actions workflow (.github/workflows/build-deploy.yml)
    - USGS Earthquake Hazards Program API
    """)


if __name__ == "__main__":
    main()
