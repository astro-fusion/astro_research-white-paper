"""
Earthquake-Planetary Correlation Analysis Framework

Data-driven approach to analyze if certain planetary combinations 
(e.g., Mangal-Ketu conjunction) correlate with earthquake events.

Part of the multi-use-case validation system for planetary influence analysis.
"""

import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import os

class EarthquakeAstrologicalAnalysis:
    """
    Analyze correlation between planetary positions/combinations and earthquake events.
    
    Use Cases:
    - Mangal-Ketu conjunction → Earthquakes?
    - Saturn in certain positions → Earthquakes?
    - Multiple planet conjunctions → Earthquakes?
    - Planetary transits → Seismic activity?
    """
    
    def __init__(self, earthquake_data_file: Optional[str] = None):
        """Initialize earthquake analysis framework."""
        self.earthquakes = self._load_earthquake_data(earthquake_data_file)
        self.planetary_data = None
        self.correlation_results = {}
        
        # Define planetary combinations to test
        self.COMBINATIONS_TO_TEST = {
            'mangal_ketu': {
                'planets': ['MARS', 'KETU'],
                'type': 'conjunction',
                'description': 'Mars-Ketu conjunction (Mars + South Node)'
            },
            'mangal_saturn': {
                'planets': ['MARS', 'SATURN'],
                'type': 'conjunction',
                'description': 'Mars-Saturn conjunction'
            },
            'rahu_ketu': {
                'planets': ['RAHU', 'KETU'],
                'type': 'opposition',
                'description': 'Rahu-Ketu axis (always opposite)'
            },
            'saturn_outer': {
                'planets': ['SATURN', 'RAHU', 'KETU'],
                'type': 'any_two',
                'description': 'Saturn with any outer planet'
            },
            'mars_activation': {
                'planets': ['MARS'],
                'type': 'strength_trigger',
                'description': 'Mars in high strength positions'
            },
            'malefic_cluster': {
                'planets': ['MARS', 'SATURN', 'RAHU'],
                'type': 'clustering',
                'description': 'Cluster of malefic planets'
            }
        }
    
    def _load_earthquake_data(self, filename: Optional[str]) -> pd.DataFrame:
        """
        Load earthquake data from CSV or return template.
        
        Expected format:
        date,time,latitude,longitude,magnitude,depth_km,location
        """
        if filename and os.path.exists(filename):
            df = pd.read_csv(filename)
            df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'].astype(str))
            return df
        else:
            # Return template structure
            return self._create_earthquake_template()
    
    def _create_earthquake_template(self) -> pd.DataFrame:
        """Create template earthquake dataset for analysis."""
        # Sample earthquake data structure
        data = {
            'datetime': pd.date_range('2020-01-01', periods=100, freq='D'),
            'latitude': np.random.uniform(-90, 90, 100),
            'longitude': np.random.uniform(-180, 180, 100),
            'magnitude': np.random.uniform(4.0, 7.5, 100),
            'depth_km': np.random.uniform(5, 600, 100),
            'location': [f'Location_{i}' for i in range(100)]
        }
        return pd.DataFrame(data)
    
    def generate_planetary_data(self, start_date: datetime, 
                               end_date: datetime, 
                               frequency: str = 'daily') -> pd.DataFrame:
        """
        Generate synthetic planetary position/strength data for analysis period.
        
        Args:
            start_date: Start of analysis period
            end_date: End of analysis period
            frequency: 'daily', 'weekly', 'monthly'
            
        Returns:
            DataFrame with planetary positions/strengths
        """
        if frequency == 'daily':
            dates = pd.date_range(start_date, end_date, freq='D')
        elif frequency == 'weekly':
            dates = pd.date_range(start_date, end_date, freq='W')
        else:
            dates = pd.date_range(start_date, end_date, freq='MS')
        
        planets = ['SUN', 'MOON', 'MARS', 'MERCURY', 'JUPITER', 
                  'VENUS', 'SATURN', 'RAHU', 'KETU']
        
        data = {'datetime': dates}
        
        # Generate realistic planetary strength patterns
        for planet in planets:
            # Different planets have different cycles
            if planet == 'MARS':
                # Mars cycle ~687 days
                period = 687
            elif planet == 'SATURN':
                # Saturn cycle ~10,759 days
                period = 3000
            elif planet == 'RAHU':
                # Rahu cycle ~18.6 years
                period = 6793
            else:
                period = 365
            
            # Create strength oscillation
            x = np.arange(len(dates)) / len(dates) * 2 * np.pi
            strength = 50 + 30 * np.sin(x * period / 365)
            data[f'{planet}_strength'] = np.clip(strength, 0, 100)
            
            # Create zodiac position (0-360 degrees)
            position = (x * 360 * period / 365) % 360
            data[f'{planet}_position'] = position
        
        self.planetary_data = pd.DataFrame(data)
        return self.planetary_data
    
    def identify_planetary_conjunction(self, planet1: str, planet2: str, 
                                     tolerance_deg: float = 8.0) -> List[Tuple]:
        """
        Identify when two planets are in conjunction (close proximity).
        
        Args:
            planet1: First planet name
            planet2: Second planet name
            tolerance_deg: Maximum angular separation (degrees) for conjunction
            
        Returns:
            List of (date, angular_distance) tuples
        """
        if self.planetary_data is None:
            return []
        
        pos1 = self.planetary_data[f'{planet1}_position'].values
        pos2 = self.planetary_data[f'{planet2}_position'].values
        dates = self.planetary_data['datetime'].values
        
        conjunctions = []
        
        for i in range(len(pos1)):
            # Calculate angular distance (accounting for circular nature)
            diff = abs(pos1[i] - pos2[i])
            if diff > 180:
                diff = 360 - diff
            
            if diff <= tolerance_deg:
                conjunctions.append((dates[i], diff))
        
        return conjunctions
    
    def analyze_conjunction_earthquake_correlation(self, 
                                                  planet1: str, 
                                                  planet2: str,
                                                  window_days: int = 30) -> Dict:
        """
        Analyze if earthquakes are more likely within N days of a conjunction.
        
        Args:
            planet1: First planet
            planet2: Second planet
            window_days: Days before/after conjunction to check for earthquakes
            
        Returns:
            Dictionary with correlation analysis results
        """
        # Find conjunctions
        conjunctions = self.identify_planetary_conjunction(planet1, planet2)
        
        if not conjunctions:
            return {'status': 'no_conjunctions_found', 'details': {}}
        
        conjunction_dates = [c[0] for c in conjunctions]
        
        # Count earthquakes near conjunctions vs background rate
        earthquakes_near_conjunction = 0
        earthquakes_far_from_conjunction = 0
        total_earthquake_days = 0
        
        for eq_date in self.earthquakes['datetime'].values:
            near_conjunction = False
            
            for conj_date in conjunction_dates:
                conj_datetime = pd.Timestamp(conj_date)
                eq_datetime = pd.Timestamp(eq_date)
                days_diff = abs((eq_datetime - conj_datetime).days)
                
                if days_diff <= window_days:
                    earthquakes_near_conjunction += 1
                    near_conjunction = True
                    break
            
            if not near_conjunction:
                earthquakes_far_from_conjunction += 1
            
            total_earthquake_days += 1
        
        # Calculate statistics
        total_period_days = (self.earthquakes['datetime'].max() - 
                            self.earthquakes['datetime'].min()).days
        
        expected_earthquakes_in_window = (
            len(self.earthquakes) * 
            (len(conjunction_dates) * window_days * 2) / 
            total_period_days
        )
        
        chi_square = ((earthquakes_near_conjunction - expected_earthquakes_in_window) ** 2) / \
                     (expected_earthquakes_in_window + 1)
        
        return {
            'conjunction': f'{planet1}-{planet2}',
            'conjunctions_found': len(conjunctions),
            'conjunction_dates': [pd.Timestamp(c[0]).strftime('%Y-%m-%d') for c in conjunctions[:5]],
            'earthquakes_near_conjunction': earthquakes_near_conjunction,
            'earthquakes_far_from_conjunction': earthquakes_far_from_conjunction,
            'expected_earthquakes': round(expected_earthquakes_in_window, 2),
            'ratio_near_vs_expected': round(earthquakes_near_conjunction / 
                                           max(expected_earthquakes_in_window, 1), 2),
            'chi_square_statistic': round(chi_square, 4),
            'window_days': window_days,
            'total_earthquakes': len(self.earthquakes),
            'analysis_period_days': total_period_days
        }
    
    def analyze_planetary_strength_trigger(self, planet: str, 
                                          strength_threshold: float = 75.0) -> Dict:
        """
        Analyze if earthquakes are more likely when a planet is in high strength.
        
        Args:
            planet: Planet to analyze
            strength_threshold: Minimum strength to consider "activated"
            
        Returns:
            Dictionary with correlation results
        """
        if self.planetary_data is None:
            return {'status': 'no_planetary_data'}
        
        # Find periods of high strength
        high_strength_mask = self.planetary_data[f'{planet}_strength'] >= strength_threshold
        high_strength_dates = self.planetary_data[high_strength_mask]['datetime'].values
        
        if len(high_strength_dates) == 0:
            return {'status': 'no_high_strength_periods'}
        
        # Count earthquakes during high strength vs low strength
        earthquakes_during_high_strength = 0
        earthquakes_during_low_strength = 0
        
        for eq_date in self.earthquakes['datetime'].values:
            eq_dt = pd.Timestamp(eq_date)
            
            # Find closest planetary date
            closest_idx = (self.planetary_data['datetime'] - eq_dt).abs().argmin()
            is_high_strength = high_strength_mask.iloc[closest_idx]
            
            if is_high_strength:
                earthquakes_during_high_strength += 1
            else:
                earthquakes_during_low_strength += 1
        
        # Calculate statistics
        total_high_strength_days = high_strength_mask.sum()
        total_days = len(self.planetary_data)
        high_strength_fraction = total_high_strength_days / total_days
        
        expected_earthquakes_during_high = len(self.earthquakes) * high_strength_fraction
        
        return {
            'planet': planet,
            'strength_threshold': strength_threshold,
            'high_strength_periods_found': int(total_high_strength_days),
            'earthquakes_during_high_strength': earthquakes_during_high_strength,
            'earthquakes_during_low_strength': earthquakes_during_low_strength,
            'expected_earthquakes_during_high': round(expected_earthquakes_during_high, 2),
            'ratio_observed_vs_expected': round(
                earthquakes_during_high_strength / 
                max(expected_earthquakes_during_high, 1), 2
            ),
            'high_strength_fraction_of_year': round(high_strength_fraction, 4),
            'total_earthquakes': len(self.earthquakes),
            'total_analysis_days': total_days
        }
    
    def run_all_correlations(self) -> Dict:
        """Run all defined correlation tests."""
        results = {
            'analysis_timestamp': datetime.now().isoformat(),
            'earthquake_count': len(self.earthquakes),
            'analysis_period': {
                'start': self.earthquakes['datetime'].min().isoformat(),
                'end': self.earthquakes['datetime'].max().isoformat(),
            },
            'conjunction_analysis': {},
            'strength_trigger_analysis': {}
        }
        
        # Test conjunctions
        for combo_name, combo_info in self.COMBINATIONS_TO_TEST.items():
            if combo_info['type'] == 'conjunction' and len(combo_info['planets']) == 2:
                planet1, planet2 = combo_info['planets']
                result = self.analyze_conjunction_earthquake_correlation(planet1, planet2)
                results['conjunction_analysis'][combo_name] = {
                    'description': combo_info['description'],
                    'result': result
                }
        
        # Test strength triggers
        for combo_name, combo_info in self.COMBINATIONS_TO_TEST.items():
            if combo_info['type'] == 'strength_trigger':
                planet = combo_info['planets'][0]
                result = self.analyze_planetary_strength_trigger(planet)
                results['strength_trigger_analysis'][combo_name] = {
                    'description': combo_info['description'],
                    'result': result
                }
        
        self.correlation_results = results
        return results
    
    def export_results_json(self, output_file: str) -> None:
        """Export analysis results to JSON."""
        with open(output_file, 'w') as f:
            json.dump(self.correlation_results, f, indent=2, default=str)
        print(f"Results exported to {output_file}")
    
    def generate_analysis_summary(self) -> str:
        """Generate human-readable summary of findings."""
        if not self.correlation_results:
            return "No correlation analysis results available"
        
        summary = []
        summary.append("=" * 80)
        summary.append("EARTHQUAKE-PLANETARY CORRELATION ANALYSIS SUMMARY")
        summary.append("=" * 80)
        summary.append("")
        summary.append(f"Analysis Period: {self.correlation_results['analysis_period']['start']}")
        summary.append(f"                 to {self.correlation_results['analysis_period']['end']}")
        summary.append(f"Total Earthquakes Analyzed: {self.correlation_results['earthquake_count']}")
        summary.append("")
        
        # Conjunction results
        summary.append("PLANETARY CONJUNCTION ANALYSIS")
        summary.append("-" * 80)
        
        for combo_name, combo_data in self.correlation_results['conjunction_analysis'].items():
            summary.append(f"\n{combo_data['description']}")
            result = combo_data['result']
            
            if 'status' in result:
                summary.append(f"  Status: {result['status']}")
            else:
                summary.append(f"  Conjunctions Found: {result['conjunctions_found']}")
                summary.append(f"  Earthquakes near conjunction: {result['earthquakes_near_conjunction']}")
                summary.append(f"  Expected (random): {result['expected_earthquakes']}")
                summary.append(f"  Ratio (observed/expected): {result['ratio_near_vs_expected']}")
                summary.append(f"  Chi-square: {result['chi_square_statistic']}")
                
                if result['chi_square_statistic'] > 3.841:  # p < 0.05
                    summary.append(f"  ⚠️  POTENTIALLY SIGNIFICANT CORRELATION")
                else:
                    summary.append(f"  → No statistically significant correlation")
        
        # Strength trigger results
        summary.append("\n\nPLANETARY STRENGTH TRIGGER ANALYSIS")
        summary.append("-" * 80)
        
        for combo_name, combo_data in self.correlation_results['strength_trigger_analysis'].items():
            summary.append(f"\n{combo_data['description']}")
            result = combo_data['result']
            
            if 'status' in result:
                summary.append(f"  Status: {result['status']}")
            else:
                summary.append(f"  Earthquakes during high strength: {result['earthquakes_during_high_strength']}")
                summary.append(f"  Expected (random): {result['expected_earthquakes_during_high']}")
                summary.append(f"  Ratio (observed/expected): {result['ratio_observed_vs_expected']}")
        
        summary.append("\n" + "=" * 80)
        return "\n".join(summary)


def main():
    """Main analysis workflow."""
    print("=" * 80)
    print("EARTHQUAKE-PLANETARY CORRELATION ANALYSIS")
    print("Data-driven framework for multi-use-case validation")
    print("=" * 80)
    
    # Initialize analyzer
    analyzer = EarthquakeAstrologicalAnalysis()
    
    # Generate data for 5-year period
    start_date = datetime(2019, 1, 1)
    end_date = datetime(2024, 12, 31)
    
    print("\n1. Generating planetary data (2019-2024)...")
    analyzer.generate_planetary_data(start_date, end_date, frequency='daily')
    
    print("2. Running correlation analyses...")
    results = analyzer.run_all_correlations()
    
    print("3. Generating summary...")
    summary = analyzer.generate_analysis_summary()
    print(summary)
    
    # Export results
    output_file = 'use_cases/earthquake/data/earthquake_planetary_correlation_analysis.json'
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    analyzer.export_results_json(output_file)
    
    print(f"\n✅ Analysis complete. Results saved to {output_file}")


if __name__ == '__main__':
    main()
