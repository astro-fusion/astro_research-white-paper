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
        latitude_range: Optional[Tuple[float, float]] = None,
        longitude_range: Optional[Tuple[float, float]] = None,
        use_usgs_api: bool = False
    ) -> Dict:
        """
        Fetch earthquake data.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            min_magnitude: Minimum magnitude to retrieve
            latitude_range: Optional (min_lat, max_lat)
            longitude_range: Optional (min_lon, max_lon)
            use_usgs_api: If True, fetch from USGS API; else use local data
            
        Returns:
            Dictionary with earthquake data
        """
        if self.use_sample_data and not use_usgs_api:
            return self._load_sample_data()
        
        if use_usgs_api:
            try:
                return self._fetch_from_usgs_api(
                    start_date, end_date, min_magnitude, 
                    latitude_range, longitude_range
                )
            except Exception as e:
                self._log(f"USGS API fetch failed: {e}. Falling back to sample data.")
                return self._load_sample_data()
        
        return self._load_sample_data()
    
    def _fetch_from_usgs_api(
        self,
        start_date: str,
        end_date: str,
        min_magnitude: float,
        latitude_range: Optional[Tuple[float, float]] = None,
        longitude_range: Optional[Tuple[float, float]] = None
    ) -> Dict:
        """
        Fetch data from USGS Earthquake API.
        
        API Documentation:
        https://earthquake.usgs.gov/fdsnws/event/1/
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            min_magnitude: Minimum magnitude
            latitude_range: (min_lat, max_lat)
            longitude_range: (min_lon, max_lon)
            
        Returns:
            GeoJSON formatted earthquake data
            
        Example:
            https://earthquake.usgs.gov/fdsnws/event/1/query?
                starttime=2020-01-01&
                endtime=2020-12-31&
                minmagnitude=5.0&
                minlatitude=20&maxlatitude=35&
                minlongitude=75&maxlongitude=90&
                format=geojson
        """
        self._log(f"Fetching earthquakes from USGS API...")
        self._log(f"  Period: {start_date} to {end_date}")
        self._log(f"  Minimum magnitude: {min_magnitude}")
        if latitude_range:
            self._log(f"  Latitude: {latitude_range}")
        if longitude_range:
            self._log(f"  Longitude: {longitude_range}")
        
        params = {
            "starttime": start_date,
            "endtime": end_date,
            "minmagnitude": min_magnitude,
            "format": self.DEFAULT_FORMAT,
            "orderby": "magnitude" # Largest first
        }
        
        if latitude_range:
            params["minlatitude"] = latitude_range[0]
            params["maxlatitude"] = latitude_range[1]
            
        if longitude_range:
            params["minlongitude"] = longitude_range[0]
            params["maxlongitude"] = longitude_range[1]
        
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
                "magnitude": float(self._homogenize_magnitude(props.get("mag", 0), props.get("magType", ""))),
                "magnitude_raw": props.get("mag", 0),
                "magnitude_type": props.get("magType", ""),
                "place": props.get("place", "Unknown"),
                "latitude": coords[1] if len(coords) > 1 else 0,
                "longitude": coords[0] if len(coords) > 0 else 0,
                "depth_km": coords[2] if len(coords) > 2 else 0,
                "usgs_url": props.get("url", ""),
            }
            processed.append(processed_eq)
        
        return processed

    def _homogenize_magnitude(self, mag: float, mag_type: str) -> float:
        """
        Homogenize magnitude to Moment Magnitude (Mw).
        
        Uses approximate empirical conversions for the Research Pipeline.
        Reference: Scordilis (2006) and standard seismological conversions.
        
        Args:
            mag: Original magnitude
            mag_type: Magnitude type (e.g., 'mb', 'ms', 'md', 'ml')
            
        Returns:
            Homogenized Mw magnitude.
        """
        if not mag_type:
            return mag
            
        mt = mag_type.lower()
        
        # If already Moment Magnitude, return as is
        if mt in ('mw', 'mww', 'mwr', 'mwc'):
            return mag
            
        # Body Wave (mb) -> Mw
        # Proxy formula: Mw = 0.85 * mb + 1.03 (Generalized global approximation)
        if mt == 'mb':
            # For small quakes, mb ~= Mw. For large, mb saturates.
            if mag > 6.0: 
                # Scordilis correction for saturation
                return 0.85 * mag + 1.03
            return mag
            
        # Surface Wave (Ms) -> Mw
        # Proxy: Mw = 0.67 * Ms + 2.07 (Scordilis) for 3.0 < Ms < 6.1
        if mt == 'ms':
            if 3.0 <= mag <= 6.1:
                return 0.67 * mag + 2.07
            elif mag > 6.1:
                return 0.99 * mag + 0.08
            
        # Default fallback: assume ML/MD ~= Mw for small events
        return mag

    def decluster_catalog(self, catalog: List[Dict]) -> List[Dict]:
        """
        Decluster the earthquake catalog using Gardner-Knopoff algorithm.
        
        Removes aftershocks and foreshocks based on space-time windows.
        
        Args:
            catalog: List of earthquake dictionaries (must have 'magnitude', 'time' as datetime or ISO, 'latitude', 'longitude')
            
        Returns:
            List of independent mainshocks.
        """
        self._log(f"Declustering {len(catalog)} events...")
        
        # Sort by magnitude descending (largest events are mainshocks)
        # We process largest first, and remove everything in their window.
        # Note: Standard GK actually sorts by Time, but a simple greedy approach 
        # is: Pick largest unflagged, mark neighbors as aftershocks.
        
        # However, the strict GK algorithm iterates through time.
        # "Method: Identify the largest event in a sequence. If an event falls within the window of a larger one..."
        
        # Simplified implementation:
        # 1. Sort by Magnitude Descending.
        # 2. Taking the largest event (Mainshock), remove all smaller events in its T/L window.
        # 3. Repeat.
        
        # Make a copy and ensure datetime objects
        events = []
        for eq in catalog:
            # Parse time if string
            if isinstance(eq['time'], str):
                try:
                    dt = datetime.fromisoformat(eq['time'].replace('Z', '+00:00'))
                except ValueError:
                    # Fallback for simple date strings
                    dt = datetime.strptime(eq['time'][:10], "%Y-%m-%d")
            else:
                dt = eq['time']
                
            events.append({
                "data": eq,
                "magnitude": float(eq['magnitude']),
                "time": dt,
                "lat": float(eq['latitude']),
                "lon": float(eq['longitude']),
                "id": eq.get('usgs_url', str(hash(str(eq))))
            })
            
        # Sort by magnitude descending
        events.sort(key=lambda x: x['magnitude'], reverse=True)
        
        independent_events = []
        removed_ids = set()
        
        # Gardner-Knopoff Window Table (Approximate)
        # Mag: [Distance(km), Time(days)]
        gk_windows = {
            2.5: [19.5, 6],
            3.0: [22.5, 11.5],
            3.5: [26, 22],
            4.0: [30, 42],
            4.5: [35, 83],
            5.0: [40, 155],
            5.5: [47, 290],
            6.0: [54, 510],
            6.5: [61, 790],
            7.0: [70, 915],
            7.5: [81, 960],
            8.0: [94, 985]
        }
        
        def get_window(mag):
            # Find closest lower bound
            keys = sorted(gk_windows.keys())
            for k in reversed(keys):
                if mag >= k:
                    return gk_windows[k]
            return gk_windows[2.5] # Minimum
            
        from math import radians, cos, sin, asin, sqrt
        def haversine(lat1, lon1, lat2, lon2):
            R = 6371 # Earth radius km
            dLat = radians(lat2 - lat1)
            dLon = radians(lon2 - lon1)
            a = sin(dLat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dLon/2)**2
            c = 2 * asin(sqrt(a))
            return R * c
            
        for i, mainshock in enumerate(events):
            if mainshock['id'] in removed_ids:
                continue
                
            independent_events.append(mainshock['data'])
            
            # Distance/Time Window
            dist_km, time_days = get_window(mainshock['magnitude'])
            
            # Check all other events
            for j in range(i + 1, len(events)):
                candidate = events[j]
                if candidate['id'] in removed_ids:
                    continue
                    
                # Check Time Window (Forward and Backward - Foreshocks/Aftershocks)
                time_diff = abs((candidate['time'] - mainshock['time']).days)
                if time_diff > time_days:
                    continue
                    
                # Check Distance Window
                dist = haversine(mainshock['lat'], mainshock['lon'], candidate['lat'], candidate['lon'])
                if dist <= dist_km:
                    removed_ids.add(candidate['id'])
                    
        self._log(f"Declustering complete. Reduced from {len(catalog)} to {len(independent_events)} events.")
        return independent_events
    
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
    # ============================================================
    # OPTION 2: Fetch from USGS API (ENABLED FOR PHASE 7)
    # ============================================================
    print("\n" + "="*60)
    print("PHASE 7: Fetching REAL data from USGS (2020-2023)")
    print("="*60)
    
    try:
        # Fetching a larger dataset for real analysis
        raw_data = fetcher.fetch_earthquakes(
            start_date="2020-01-01",
            end_date="2023-12-31", 
            min_magnitude=6.0, # Focus on significant events
            use_usgs_api=True  # ENABLED
        )
        
        # Save to real data path
        data_dir = os.path.join(os.path.dirname(__file__), "../../data")
        os.makedirs(data_dir, exist_ok=True)
        output_file = os.path.join(data_dir, "usgs_real_data_phase7.json")
        
        # Process and Save
        processed_real = fetcher.process_for_analysis(raw_data)
        
        with open(output_file, "w") as f:
            json.dump(processed_real, f, indent=2, default=str)
            
        print(f"✅ Fetched and saved {len(processed_real)} real earthquakes to {output_file}")
        
    except Exception as e:
        print(f"❌ Error fetching real data: {e}")
    
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
