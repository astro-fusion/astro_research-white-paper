"""
USGS Earthquake Data Fetcher

Payload-driven system to fetch earthquake data from the USGS API
and store it locally for offline research analysis.
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

    def __init__(self, use_sample_data: bool = False, verbose: bool = False):
        """
        Initialize the earthquake data fetcher.

        Args:
            use_sample_data: Discarded in production parity.
            verbose: If True, print detailed logging
        """
        self.use_sample_data = use_sample_data
        self.verbose = verbose
        self.sample_data_path = (
            Path(__file__).parent.parent / "data" / "sample_earthquakes.json"
        )

    def fetch_earthquakes(
        self,
        start_date: str,
        end_date: str,
        min_magnitude: float = DEFAULT_MAGNITUDE,
        latitude_range: Optional[Tuple[float, float]] = None,
        longitude_range: Optional[Tuple[float, float]] = None,
        use_usgs_api: bool = False,
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
        if use_usgs_api:
            try:
                return self._fetch_from_usgs_api(
                    start_date, end_date, min_magnitude, latitude_range, longitude_range
                )
            except Exception as e:
                self._log(f"❌ CRITICAL: USGS API fetch failed: {e}")
                self._log("Real data fetch failed. Cannot proceed with valid analysis.")
                raise
        
        # If API is not explicitly requested, check consistency
        # In this strict mode, we should generally default to API usage or require explicit file path
        # But for this function signature, we'll enforce API if sample data was previously the default
        self._log("⚠️ USGS API flag not set, but mock data is disabled.")
        self._log("Attempting API fetch as fallback for real data...")
        return self._fetch_from_usgs_api(
             start_date, end_date, min_magnitude, 
             latitude_range, longitude_range
        )

    def _fetch_from_usgs_api(
        self,
        start_date: str,
        end_date: str,
        min_magnitude: float,
        latitude_range: Optional[Tuple[float, float]] = None,
        longitude_range: Optional[Tuple[float, float]] = None,
    ) -> Dict:
        """
        Fetch data from USGS Earthquake API.
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
            "orderby": "magnitude",  # Largest first
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

    # Mock data generation methods removed to ensure production integrity.
    # No _load_sample_data or _create_mock_data available.

    def process_for_analysis(self, earthquake_data: Dict) -> List[Dict]:
        """
        Process USGS GeoJSON data into analysis format.
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
                "magnitude": float(
                    self._homogenize_magnitude(
                        props.get("mag", 0), props.get("magType", "")
                    )
                ),
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
        Homogenize magnitude to Mw.
        """
        if not mag_type:
            return mag

        mt = mag_type.lower()
        if mt in ("mw", "mww", "mwr", "mwc"):
            return mag

        if mt == "mb":
            if mag > 6.0:
                return 0.85 * mag + 1.03
            return mag

        if mt == "ms":
            if 3.0 <= mag <= 6.1:
                return 0.67 * mag + 2.07
            elif mag > 6.1:
                return 0.99 * mag + 0.08

        return mag

    def decluster_catalog(self, catalog: List[Dict]) -> List[Dict]:
        """
        Decluster the earthquake catalog using Gardner-Knopoff algorithm.
        """
        self._log(f"Declustering {len(catalog)} events...")
        
        events = []
        for eq in catalog:
            if isinstance(eq["time"], str):
                try:
                    dt = datetime.fromisoformat(eq["time"].replace("Z", "+00:00"))
                except ValueError:
                    dt = datetime.strptime(eq["time"][:10], "%Y-%m-%d")
            else:
                dt = eq["time"]

            events.append(
                {
                    "data": eq,
                    "magnitude": float(eq["magnitude"]),
                    "time": dt,
                    "lat": float(eq["latitude"]),
                    "lon": float(eq["longitude"]),
                    "id": eq.get("usgs_url", str(hash(str(eq)))),
                }
            )

        events.sort(key=lambda x: x["magnitude"], reverse=True)

        independent_events = []
        removed_ids = set()

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
            8.0: [94, 985],
        }

        def get_window(mag):
            keys = sorted(gk_windows.keys())
            for k in reversed(keys):
                if mag >= k:
                    return gk_windows[k]
            return gk_windows[2.5]

        from math import radians, cos, sin, asin, sqrt

        def haversine(lat1, lon1, lat2, lon2):
            R = 6371
            dLat = radians(lat2 - lat1)
            dLon = radians(lon2 - lon1)
            a = (
                sin(dLat / 2) ** 2
                + cos(radians(lat1)) * cos(radians(lat2)) * sin(dLon / 2) ** 2
            )
            c = 2 * asin(sqrt(a))
            return R * c

        for i, mainshock in enumerate(events):
            if mainshock["id"] in removed_ids:
                continue

            independent_events.append(mainshock["data"])
            dist_km, time_days = get_window(mainshock["magnitude"])

            for j in range(i + 1, len(events)):
                candidate = events[j]
                if candidate["id"] in removed_ids:
                    continue

                time_diff = abs((candidate["time"] - mainshock["time"]).days)
                if time_diff > time_days:
                    continue

                dist = haversine(
                    mainshock["lat"],
                    mainshock["lon"],
                    candidate["lat"],
                    candidate["lon"],
                )
                if dist <= dist_km:
                    removed_ids.add(candidate["id"])

        self._log(
            f"Declustering complete. Reduced from {len(catalog)} to {len(independent_events)} events."
        )
        return independent_events

    def save_to_file(self, earthquakes: List[Dict], output_path: str) -> None:
        """Save processed earthquakes to JSON file."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(earthquakes, f, indent=2)
        self._log(f"✅ Saved {len(earthquakes)} earthquakes to {output_path}")

    def _log(self, message: str) -> None:
        """Print log message if verbose mode is enabled."""
        if self.verbose:
            print(f"[EarthquakeDataFetcher] {message}")


def main():
    """
    Main workflow: Fetch Real USGS Data for Offline Storage.
    """
    import sys
    
    # Initialize fetcher
    fetcher = EarthquakeDataFetcher(use_sample_data=False, verbose=True)
    
    print("\n" + "="*80)
    print("EARTHQUAKE DATA FETCHER - OFFLINE STORAGE MODE")
    print("Fetching REAL data to populate local storage (Multiple Datasets).")
    print("="*80)
    
    base_dir = Path(__file__).parent.parent / "data"
    base_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # ---------------------------------------------------------
        # DATASET 1: Global Significant Earthquakes (Mag 6.0+)
        # ---------------------------------------------------------
        print("\n1. Fetching Global Data (2020-2025, Mag 6.0+)...")
        global_data = fetcher.fetch_earthquakes(
            start_date="2020-01-01",
            end_date="2025-12-31", 
            min_magnitude=6.0,
            use_usgs_api=True
        )
        
        global_file = base_dir / "usgs_global_6plus_2020_2025.json"
        processed_global = fetcher.process_for_analysis(global_data)
        
        with open(global_file, "w") as f:
            json.dump(processed_global, f, indent=2, default=str)
        print(f"   ✅ Saved {len(processed_global)} records to {global_file.name}")


        # ---------------------------------------------------------
        # DATASET 2: Indian Subcontinent (Mag 5.0+)
        # ---------------------------------------------------------
        # Region: roughly 5N-40N, 60E-100E
        print("\n2. Fetching Indian Subcontinent Data (2020-2025, Mag 5.0+)...")
        india_data = fetcher.fetch_earthquakes(
            start_date="2020-01-01",
            end_date="2025-12-31", 
            min_magnitude=5.0,
            latitude_range=(5.0, 40.0),
            longitude_range=(60.0, 100.0),
            use_usgs_api=True
        )
        
        india_file = base_dir / "usgs_india_5plus_2020_2025.json"
        processed_india = fetcher.process_for_analysis(india_data)
        
        with open(india_file, "w") as f:
            json.dump(processed_india, f, indent=2, default=str)
        print(f"   ✅ Saved {len(processed_india)} records to {india_file.name}")


        print("\n" + "="*80)
        print("STORAGE COMPLETE")
        print(f"1. Global Data: {global_file}")
        print(f"2. Regional Data: {india_file}")
        print("These files are ready for progressive loading in analysis tools.")
        
    except Exception as e:
        print(f"\n❌ ERROR: Failed to fetch data: {e}")
        sys.exit(1)
    
    print("\n" + "="*80)


if __name__ == "__main__":
    main()
