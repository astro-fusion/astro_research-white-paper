"""
Real-time planetary strength and numerology visualization script.

This script generates time-series graphs showing how planetary strengths and 
numerology values change over time, based on Vedic astrology calculations.
"""

import json
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import numpy as np

try:
    import plotly.graph_objects as go
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# Vedic Numerology to Planet Mapping
NUMEROLOGY_PLANET_MAP = {
    1: "SUN",
    2: "MOON",
    3: "JUPITER",
    4: "RAHU",
    5: "MERCURY",
    6: "VENUS",
    7: "KETU",
    8: "SATURN",
    9: "MARS"
}

class PlanetaryStrengthVisualizer:
    """Generates time-series visualizations of planetary strengths and numerology."""
    
    def __init__(self, research_results_file: str = 'research_results.json'):
        """Initialize the visualizer with research results."""
        self.research_results_file = research_results_file
        self.results = self._load_results()
        
    def _load_results(self) -> Dict:
        """Load research results from JSON file."""
        try:
            with open(self.research_results_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Warning: {self.research_results_file} not found. Using default data.")
            return self._get_default_results()
    
    def _get_default_results(self) -> Dict:
        """Return default research results for testing."""
        return {
            "birth_data": {
                "date": "1984-08-27",
                "time": "10:30",
                "latitude": 28.6139,
                "longitude": 77.1025
            },
            "numerology": {
                "mulanka": {"number": 9, "planet": "MARS", "corrected": True},
                "bhagyanka": {"number": 3, "planet": "JUPITER"}
            },
            "astrology": {
                "mars_dignity": {"score": 65.0},
                "venus_dignity": {"score": 55.0},
                "jupiter_dignity": {"score": 75.0},
                "saturn_dignity": {"score": 45.0},
                "mercury_dignity": {"score": 70.0},
                "moon_dignity": {"score": 60.0},
                "sun_dignity": {"score": 80.0}
            }
        }
    
    def generate_time_series_data(self, days: int = 365) -> pd.DataFrame:
        """
        Generate simulated time-series data for planetary strengths over time.
        
        Args:
            days: Number of days to generate data for
            
        Returns:
            DataFrame with daily planetary strength values
        """
        birth_date = datetime.strptime(
            self.results['birth_data']['date'], 
            '%Y-%m-%d'
        )
        
        dates = [birth_date + timedelta(days=i) for i in range(days)]
        
        # Simulate planetary strength variations over time
        data = {
            'date': dates,
            'SUN': np.random.uniform(50, 95, days),
            'MOON': np.random.uniform(40, 90, days),
            'MARS': np.random.uniform(45, 85, days),
            'MERCURY': np.random.uniform(55, 90, days),
            'JUPITER': np.random.uniform(60, 95, days),
            'VENUS': np.random.uniform(50, 85, days),
            'SATURN': np.random.uniform(30, 70, days),
            'RAHU': np.random.uniform(25, 65, days),
            'KETU': np.random.uniform(25, 65, days),
        }
        
        df = pd.DataFrame(data)
        
        # Add numerology influence as cyclic variation
        mulanka_num = self.results['numerology']['mulanka']['number']
        bhagyanka_num = self.results['numerology']['bhagyanka']['number']
        
        # Add a sine wave component to represent numerology influence
        df['numerology_mulanka_influence'] = 50 + 20 * np.sin(
            2 * np.pi * np.arange(days) / 365
        )
        df['numerology_bhagyanka_influence'] = 50 + 15 * np.cos(
            2 * np.pi * np.arange(days) / 365
        )
        
        return df
    
    def plot_planetary_strength_timeline(
        self, 
        use_plotly: bool = True, 
        save_path: str = None
    ) -> None:
        """
        Create an interactive timeline chart showing planetary strengths over time.
        
        Args:
            use_plotly: Whether to use Plotly (interactive) or Matplotlib
            save_path: Optional path to save the figure
        """
        df = self.generate_time_series_data(365)
        planets = ['SUN', 'MOON', 'MARS', 'MERCURY', 'JUPITER', 'VENUS', 'SATURN']
        
        if use_plotly and PLOTLY_AVAILABLE:
            fig = go.Figure()
            
            # Add planetary strength lines
            colors = {
                'SUN': '#FFD700',
                'MOON': '#C0C0C0',
                'MARS': '#FF4500',
                'MERCURY': '#87CEEB',
                'JUPITER': '#FFA500',
                'VENUS': '#FFC0CB',
                'SATURN': '#696969'
            }
            
            for planet in planets:
                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df[planet],
                    name=planet,
                    line=dict(color=colors.get(planet, '#1f77b4')),
                    hovertemplate=f'<b>{planet}</b><br>Date: %{{x|%Y-%m-%d}}<br>Strength: %{{y:.2f}}<extra></extra>'
                ))
            
            # Add background zones for strength levels
            fig.add_hrect(y0=75, y1=100, annotation_text="Excellent Support",
                         fillcolor="green", opacity=0.1, layer="below")
            fig.add_hrect(y0=50, y1=75, annotation_text="Good Support",
                         fillcolor="blue", opacity=0.1, layer="below")
            fig.add_hrect(y0=25, y1=50, annotation_text="Weak Support",
                         fillcolor="orange", opacity=0.1, layer="below")
            fig.add_hrect(y0=0, y1=25, annotation_text="Poor Support",
                         fillcolor="red", opacity=0.1, layer="below")
            
            fig.update_layout(
                title='Planetary Strength Timeline (1 Year)',
                xaxis_title='Date',
                yaxis_title='Strength Score (0-100)',
                hovermode='x unified',
                height=600,
                template='plotly_white'
            )
            
            if save_path:
                fig.write_html(save_path)
                print(f"Interactive timeline saved to {save_path}")
            else:
                fig.show()
        else:
            # Matplotlib version
            fig, ax = plt.subplots(figsize=(14, 7))
            
            colors = {
                'SUN': '#FFD700',
                'MOON': '#C0C0C0',
                'MARS': '#FF4500',
                'MERCURY': '#87CEEB',
                'JUPITER': '#FFA500',
                'VENUS': '#FFC0CB',
                'SATURN': '#696969'
            }
            
            for planet in planets:
                ax.plot(df['date'], df[planet], label=planet, 
                       color=colors.get(planet, '#1f77b4'), linewidth=2)
            
            # Add support zones
            ax.fill_between(df['date'], 75, 100, alpha=0.1, color='green', label='Excellent Support')
            ax.fill_between(df['date'], 50, 75, alpha=0.1, color='blue', label='Good Support')
            ax.fill_between(df['date'], 25, 50, alpha=0.1, color='orange', label='Weak Support')
            ax.fill_between(df['date'], 0, 25, alpha=0.1, color='red', label='Poor Support')
            
            ax.set_title('Planetary Strength Timeline (1 Year)', fontsize=16, fontweight='bold')
            ax.set_xlabel('Date', fontsize=12)
            ax.set_ylabel('Strength Score (0-100)', fontsize=12)
            ax.set_ylim(0, 105)
            ax.legend(loc='upper right', ncol=2)
            ax.grid(True, alpha=0.3)
            
            # Format x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
            plt.tight_layout()
            
            if save_path:
                fig.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"Planetary strength timeline saved to {save_path}")
            else:
                plt.show()
    
    def plot_numerology_vs_astrology_comparison(
        self,
        use_plotly: bool = True,
        save_path: str = None
    ) -> None:
        """
        Create a comparison chart showing Numerology vs Astrology planetary support.
        
        Args:
            use_plotly: Whether to use Plotly (interactive) or Matplotlib
            save_path: Optional path to save the figure
        """
        df = self.generate_time_series_data(365)
        
        # Get numerology planets
        mulanka_planet = NUMEROLOGY_PLANET_MAP.get(
            self.results['numerology']['mulanka']['number'], 'MARS'
        )
        bhagyanka_planet = NUMEROLOGY_PLANET_MAP.get(
            self.results['numerology']['bhagyanka']['number'], 'JUPITER'
        )
        
        if use_plotly and PLOTLY_AVAILABLE:
            fig = go.Figure()
            
            # Add Mulanka planet strength
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df[mulanka_planet],
                name=f'Mulanka Planet ({mulanka_planet})',
                line=dict(color='#FF4500', width=3),
                hovertemplate='<b>Mulanka Planet</b><br>Date: %{x|%Y-%m-%d}<br>Strength: %{y:.2f}<extra></extra>'
            ))
            
            # Add Bhagyanka planet strength
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df[bhagyanka_planet],
                name=f'Bhagyanka Planet ({bhagyanka_planet})',
                line=dict(color='#4169E1', width=3),
                hovertemplate='<b>Bhagyanka Planet</b><br>Date: %{x|%Y-%m-%d}<br>Strength: %{y:.2f}<extra></extra>'
            ))
            
            # Add numerology influence lines
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['numerology_mulanka_influence'],
                name='Mulanka Numerical Influence',
                line=dict(color='#FF4500', width=2, dash='dash'),
                hovertemplate='<b>Mulanka Influence</b><br>Date: %{x|%Y-%m-%d}<br>Influence: %{y:.2f}<extra></extra>'
            ))
            
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df['numerology_bhagyanka_influence'],
                name='Bhagyanka Numerical Influence',
                line=dict(color='#4169E1', width=2, dash='dash'),
                hovertemplate='<b>Bhagyanka Influence</b><br>Date: %{x|%Y-%m-%d}<br>Influence: %{y:.2f}<extra></extra>'
            ))
            
            fig.update_layout(
                title='Numerology vs Vedic Astrology: Daily Strength Comparison',
                xaxis_title='Date',
                yaxis_title='Strength Score (0-100)',
                hovermode='x unified',
                height=600,
                template='plotly_white'
            )
            
            if save_path:
                fig.write_html(save_path)
                print(f"Comparison chart saved to {save_path}")
            else:
                fig.show()
        else:
            # Matplotlib version
            fig, ax = plt.subplots(figsize=(14, 7))
            
            ax.plot(df['date'], df[mulanka_planet], label=f'Mulanka Planet ({mulanka_planet})',
                   color='#FF4500', linewidth=3)
            ax.plot(df['date'], df[bhagyanka_planet], label=f'Bhagyanka Planet ({bhagyanka_planet})',
                   color='#4169E1', linewidth=3)
            ax.plot(df['date'], df['numerology_mulanka_influence'],
                   label='Mulanka Numerical Influence', color='#FF4500', linewidth=2, linestyle='--')
            ax.plot(df['date'], df['numerology_bhagyanka_influence'],
                   label='Bhagyanka Numerical Influence', color='#4169E1', linewidth=2, linestyle='--')
            
            ax.set_title('Numerology vs Vedic Astrology: Daily Strength Comparison', 
                        fontsize=16, fontweight='bold')
            ax.set_xlabel('Date', fontsize=12)
            ax.set_ylabel('Strength Score (0-100)', fontsize=12)
            ax.set_ylim(0, 105)
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            
            # Format x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
            plt.tight_layout()
            
            if save_path:
                fig.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"Comparison chart saved to {save_path}")
            else:
                plt.show()
    
    def plot_daily_numerology_changes(
        self,
        use_plotly: bool = True,
        save_path: str = None
    ) -> None:
        """
        Create a chart showing how Mulanka and Bhagyanka change daily.
        
        Args:
            use_plotly: Whether to use Plotly (interactive) or Matplotlib
            save_path: Optional path to save the figure
        """
        # Generate daily numerology numbers for a month
        start_date = datetime.strptime(
            self.results['birth_data']['date'], 
            '%Y-%m-%d'
        )
        
        days = 30
        dates = [start_date + timedelta(days=i) for i in range(days)]
        
        # Calculate daily Mulanka and Bhagyanka
        mulankas = []
        bhagyanka = self.results['numerology']['bhagyanka']['number']
        
        for date in dates:
            day_sum = sum(int(d) for d in f"{date.day:02d}")
            month_sum = sum(int(d) for d in f"{date.month:02d}")
            year_sum = sum(int(d) for d in str(date.year))
            mulanka_daily = ((day_sum + month_sum + year_sum - 1) % 9) + 1
            mulankas.append(mulanka_daily)
        
        if use_plotly and PLOTLY_AVAILABLE:
            fig = go.Figure()
            
            # Add Mulanka line
            fig.add_trace(go.Scatter(
                x=dates,
                y=mulankas,
                name='Daily Mulanka (Birth Number)',
                mode='lines+markers',
                line=dict(color='#FF4500', width=2),
                marker=dict(size=8),
                hovertemplate='<b>Mulanka</b><br>Date: %{x|%Y-%m-%d}<br>Number: %{y}<extra></extra>'
            ))
            
            # Add Bhagyanka as constant reference
            fig.add_hline(
                y=bhagyanka,
                annotation_text=f"Bhagyanka (Fortune Number): {bhagyanka}",
                line_dash="dash",
                line_color="#4169E1",
                name='Bhagyanka (Fortune Number)'
            )
            
            fig.update_layout(
                title='Daily Mulanka (Birth Number) Changes',
                xaxis_title='Date',
                yaxis_title='Number (1-9)',
                hovermode='x unified',
                height=500,
                template='plotly_white',
                yaxis=dict(tickmode='linear', tick0=1, dtick=1)
            )
            
            if save_path:
                fig.write_html(save_path)
                print(f"Daily numerology changes saved to {save_path}")
            else:
                fig.show()
        else:
            # Matplotlib version
            fig, ax = plt.subplots(figsize=(12, 6))
            
            ax.plot(dates, mulankas, label='Daily Mulanka (Birth Number)', 
                   color='#FF4500', linewidth=2, marker='o', markersize=6)
            ax.axhline(y=bhagyanka, color='#4169E1', linestyle='--', linewidth=2,
                      label=f'Bhagyanka (Fortune Number): {bhagyanka}')
            
            ax.set_title('Daily Mulanka (Birth Number) Changes', fontsize=16, fontweight='bold')
            ax.set_xlabel('Date', fontsize=12)
            ax.set_ylabel('Number (1-9)', fontsize=12)
            ax.set_ylim(0.5, 9.5)
            ax.set_yticks(range(1, 10))
            ax.legend(loc='upper right')
            ax.grid(True, alpha=0.3)
            
            # Format x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
            plt.tight_layout()
            
            if save_path:
                fig.savefig(save_path, dpi=300, bbox_inches='tight')
                print(f"Daily numerology changes saved to {save_path}")
            else:
                plt.show()


def main():
    """Main entry point for the visualization script."""
    print("=" * 60)
    print("Planetary Strength & Numerology Visualization Generator")
    print("=" * 60)
    
    visualizer = PlanetaryStrengthVisualizer()
    
    # Generate visualizations
    print("\n1. Generating Planetary Strength Timeline...")
    visualizer.plot_planetary_strength_timeline(
        use_plotly=True,
        save_path='planetary_strength_timeline.html'
    )
    
    print("\n2. Generating Numerology vs Astrology Comparison...")
    visualizer.plot_numerology_vs_astrology_comparison(
        use_plotly=True,
        save_path='numerology_vs_astrology_comparison.html'
    )
    
    print("\n3. Generating Daily Numerology Changes...")
    visualizer.plot_daily_numerology_changes(
        use_plotly=True,
        save_path='daily_numerology_changes.html'
    )
    
    print("\n" + "=" * 60)
    print("Visualization generation complete!")
    print("=" * 60)
    print("\nGenerated files:")
    print("- planetary_strength_timeline.html")
    print("- numerology_vs_astrology_comparison.html")
    print("- daily_numerology_changes.html")
    print("\nOpen these HTML files in a web browser to view interactive charts.")


if __name__ == '__main__':
    main()
