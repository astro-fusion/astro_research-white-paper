# flake8: noqa
#!/usr/bin/env python3
"""
Correlation Analysis Script.

Describes the relation between the daily numerology planet and Vedic
astrology quantities, and tests the pre-registered equivalence hypotheses of
``hypothesis.yaml``: a non-significant correlation is not evidence of
independence, so "no relation" is claimed only through TOST equivalence tests
(per-planet Fisher-z correlation, and Cohen's kappa between the numerology
planet and the Moon's nakshatra lord), with stationary block-bootstrap
standard errors because consecutive days are dependent.
"""

import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)  # repo root

from studies._paths import study_data_dir  # noqa: E402
from vedic_astrology_core.config import PLANET_NAMES, Planet
from vedic_astrology_core.stats.equivalence import cohen_kappa_ci, tost
from vedic_astrology_core.stats.nulls import stationary_bootstrap_indices


class CorrelationAnalyzer:
    """
    Perform comprehensive correlation analysis between systems.
    """

    def __init__(self, data_path: Optional[str] = None):
        """
        Initialize the analyzer.

        Args:
            data_path: Path to temporal analysis CSV file (optional, will auto-detect)
        """
        if data_path is None:
            # Auto-detect the data file
            data_dir = str(study_data_dir("numerology_vs_astrology"))
            data_path = os.path.join(data_dir, "temporal_analysis_5years.csv")

        if not os.path.exists(data_path):
            raise FileNotFoundError(f"Data file not found: {data_path}")

        self.data_path = data_path
        self.data = None
        self.results = {}

        # All planets to analyze
        self.planets = [
            Planet.SUN,
            Planet.MOON,
            Planet.MARS,
            Planet.MERCURY,
            Planet.JUPITER,
            Planet.VENUS,
            Planet.SATURN,
            Planet.RAHU,
            Planet.KETU,
        ]

    def load_data(self) -> pd.DataFrame:
        """Load and preprocess the temporal data."""
        print(f"Loading data from {self.data_path}...")
        self.data = pd.read_csv(self.data_path)

        # Convert date column
        self.data["date"] = pd.to_datetime(self.data["date"])

        # Ensure we have the required columns
        required_cols = [
            "date",
            "numerology_active_planet",
            "numerology_mulanka_number",
        ]
        for planet in self.planets:
            required_cols.extend(
                [f"numerology_{planet.name}", f"astrology_{planet.name}"]
            )

        missing_cols = [col for col in required_cols if col not in self.data.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")

        print(
            f"Loaded {len(self.data)} records covering "
            f"{self.data['date'].min()} to {self.data['date'].max()}"
        )
        return self.data

    def analyze_correlations(self) -> Dict[str, Any]:
        """
        Perform comprehensive correlation analysis.

        Returns:
            Dictionary with correlation results for all planets
        """
        if self.data is None:
            self.load_data()

        print("Analyzing correlations between numerology and astrology systems...")

        correlation_results = {}

        for planet in self.planets:
            planet_name = planet.name
            num_col = f"numerology_{planet_name}"
            ast_col = f"astrology_{planet_name}"

            numerology_scores = self.data[num_col]
            astrology_scores = self.data[ast_col]

            # Calculate various correlation metrics
            # Handle case where numerology scores are constant (only 0s and 100s)
            if numerology_scores.nunique() <= 2:  # Binary data (0 or 100)
                # Use point-biserial correlation for binary vs continuous
                binary_scores = (numerology_scores > 0).astype(int)  # Convert to 0/1
                pearson_corr, pearson_p = stats.pointbiserialr(
                    binary_scores, astrology_scores
                )
                spearman_corr, spearman_p = stats.spearmanr(
                    binary_scores, astrology_scores
                )
            else:
                pearson_corr, pearson_p = stats.pearsonr(
                    numerology_scores, astrology_scores
                )
                spearman_corr, spearman_p = stats.spearmanr(
                    numerology_scores, astrology_scores
                )

            # Calculate coefficient of determination (R²)
            r_squared = pearson_corr**2

            # Perform additional statistical tests
            # 1. Test if correlation is significantly different from zero
            # 2. Calculate effect size
            # 3. Test for independence (Chi-square approximation)

            # Calculate volatility/volatility difference
            num_volatility = np.std(numerology_scores)
            ast_volatility = np.std(astrology_scores)
            volatility_ratio = (
                ast_volatility / num_volatility if num_volatility > 0 else float("inf")
            )

            # Calculate change frequency
            num_changes = self._count_changes(numerology_scores)
            ast_changes = self._count_changes(astrology_scores, threshold=0.1)

            # Calculate information content (entropy-like measure)
            num_entropy = self._calculate_entropy(numerology_scores)
            ast_entropy = self._calculate_entropy(astrology_scores, bins=20)

            correlation_results[planet_name] = {
                "planet_name": PLANET_NAMES[planet],
                "correlation_metrics": {
                    "pearson_correlation": float(pearson_corr),
                    "pearson_p_value": float(pearson_p),
                    "spearman_correlation": float(spearman_corr),
                    "spearman_p_value": float(spearman_p),
                    "r_squared": float(r_squared),
                    "correlation_strength": self._interpret_correlation(pearson_corr),
                },
                "volatility_analysis": {
                    "numerology_volatility": float(num_volatility),
                    "astrology_volatility": float(ast_volatility),
                    "volatility_ratio": float(volatility_ratio),
                    "numerology_changes": num_changes,
                    "astrology_changes": ast_changes,
                    "change_ratio": (
                        ast_changes / num_changes if num_changes > 0 else float("inf")
                    ),
                },
                "information_analysis": {
                    "numerology_entropy": float(num_entropy),
                    "astrology_entropy": float(ast_entropy),
                    "entropy_ratio": (
                        float(ast_entropy / num_entropy)
                        if num_entropy > 0
                        else float("inf")
                    ),
                },
                "statistical_tests": {
                    "correlation_significance": (
                        "significant" if pearson_p < 0.05 else "not_significant"
                    ),
                    "effect_size": self._calculate_effect_size(
                        pearson_corr, len(self.data)
                    ),
                    "mutual_information": self._test_independence(
                        numerology_scores, astrology_scores
                    ),
                },
            }

        self.results["planet_correlations"] = correlation_results
        return correlation_results

    def analyze_temporal_patterns(self) -> Dict[str, Any]:
        """
        Analyze temporal patterns and system differences.

        Returns:
            Dictionary with temporal pattern analysis
        """
        if self.data is None:
            self.load_data()

        print("Analyzing temporal patterns...")

        # Overall system comparison
        numerology_cols = [f"numerology_{p.name}" for p in self.planets]
        astrology_cols = [f"astrology_{p.name}" for p in self.planets]

        # Calculate system-wide statistics
        numerology_matrix = self.data[numerology_cols].values
        astrology_matrix = self.data[astrology_cols].values

        # System correlation matrix
        system_correlation = np.corrcoef(
            numerology_matrix.flatten(), astrology_matrix.flatten()
        )[0, 1]

        # Calculate average correlations across all planets
        planet_correlations = [
            self.results["planet_correlations"][p.name]["correlation_metrics"][
                "pearson_correlation"
            ]
            for p in self.planets
        ]
        avg_correlation = np.mean(planet_correlations)

        # Analyze numerology change patterns
        active_planets = self.data["numerology_active_planet"].value_counts()
        mulanka_numbers = self.data["numerology_mulanka_number"].value_counts()

        # Calculate transition probabilities for numerology
        transitions = self._calculate_transition_probabilities()

        temporal_results = {
            "system_wide_analysis": {
                "overall_correlation": float(system_correlation),
                "average_planet_correlation": float(avg_correlation),
                "correlation_std": float(np.std(planet_correlations)),
                "correlation_range": {
                    "min": float(min(planet_correlations)),
                    "max": float(max(planet_correlations)),
                },
            },
            "numerology_patterns": {
                "active_planet_distribution": active_planets.to_dict(),
                "mulanka_number_distribution": mulanka_numbers.to_dict(),
                "transition_probabilities": transitions,
                "avg_days_per_planet": len(self.data) / len(active_planets),
            },
            "temporal_characteristics": {
                "total_observations": len(self.data),
                "date_range": {
                    "start": self.data["date"].min().isoformat(),
                    "end": self.data["date"].max().isoformat(),
                    "days": len(self.data),
                },
                "seasonal_patterns": self._analyze_seasonal_patterns(),
            },
        }

        self.results["temporal_patterns"] = temporal_results
        return temporal_results

    def perform_hypothesis_tests(
        self,
        margin_r: float = 0.10,
        margin_kappa: float = 0.05,
        alpha: float = 0.05,
        n_boot: int = 2000,
        mean_block: float = 27.0,
        rng: Optional[np.random.Generator] = None,
    ) -> Dict[str, Any]:
        """
        Run the pre-registered equivalence tests (H1 kappa, H2 per planet).

        Earlier versions set ``reject_null = p >= 0.05`` under the null
        "the systems are correlated", pooled all planets into one flattened
        correlation, and ran a paired t-test on a single pair of numbers.
        None of these can support a claim of independence; equivalence must
        be shown against a margin fixed in advance (TOST).

        Returns:
            Dictionary with the H1 kappa test and the H2 per-planet tests.
        """
        if self.data is None:
            self.load_data()
        if rng is None:
            rng = np.random.default_rng(42)

        print("Performing equivalence tests...")
        n = len(self.data)
        boot_idx = [
            stationary_bootstrap_indices(n, mean_block, rng) for _ in range(n_boot)
        ]

        planet_tests = []
        z_margin = float(np.arctanh(margin_r))
        for planet in self.planets:
            x = (self.data[f"numerology_{planet.name}"].to_numpy() > 0).astype(float)
            y = self.data[f"astrology_{planet.name}"].to_numpy(dtype=float)
            row = {"planet": PLANET_NAMES[planet], "id": planet.name, "n": n}
            if x.std() == 0 or y.std() == 0:
                row.update({"skipped": "constant series"})
                planet_tests.append(row)
                continue
            r = float(np.corrcoef(x, y)[0, 1])
            draws = np.array([_corr(x[i], y[i]) for i in boot_idx])
            draws = np.arctanh(np.clip(draws[np.isfinite(draws)], -0.999999, 0.999999))
            se = float(np.std(draws, ddof=1))
            t = tost(float(np.arctanh(r)), se, -z_margin, z_margin, alpha=alpha)
            row.update(
                {
                    "r": r,
                    "r_ci90_low": float(np.tanh(t.ci_low)),
                    "r_ci90_high": float(np.tanh(t.ci_high)),
                    "se_fisher_z": se,
                    "p_tost": t.p_value,
                    "equivalent": t.equivalent,
                    "margin_r": margin_r,
                }
            )
            planet_tests.append(row)

        kappa_test: Dict[str, Any] = {"skipped": "no Moon nakshatra lord column"}
        lord_col = "astrology_moon_nakshatra_lord"
        if lord_col in self.data.columns:
            labels = [p.name for p in self.planets]
            a = self.data["numerology_active_planet"].astype(str).to_numpy()
            b = self.data[lord_col].astype(str).to_numpy()
            analytic = cohen_kappa_ci(a, b, labels=labels)
            boot = cohen_kappa_ci(
                a, b, labels=labels, n_boot=n_boot, mean_block=mean_block, rng=rng
            )
            se = max(analytic.se, boot.se)
            t = tost(boot.kappa, se, -margin_kappa, margin_kappa, alpha=alpha)
            kappa_test = {
                "kappa": boot.kappa,
                "observed_agreement": boot.observed_agreement,
                "expected_agreement": boot.expected_agreement,
                "n": boot.n,
                "se_analytic": analytic.se,
                "se_bootstrap": boot.se,
                "se_used": se,
                "ci95_bootstrap": [boot.ci_low, boot.ci_high],
                "ci90_tost": [t.ci_low, t.ci_high],
                "p_tost": t.p_value,
                "equivalent": t.equivalent,
                "margin_kappa": margin_kappa,
                "per_planet_agreement": {
                    k: int(((a == k) & (b == k)).sum()) for k in labels
                },
            }

        hypothesis_results = {
            "H1_kappa": kappa_test,
            "H2_planets": planet_tests,
            "alpha": alpha,
            "n_boot": n_boot,
            "mean_block": mean_block,
        }
        self.results["hypothesis_tests"] = hypothesis_results
        return hypothesis_results

    def generate_report(self) -> str:
        """
        Generate a comprehensive analysis report.

        Returns:
            Formatted string report
        """
        if not self.results:
            self.analyze_correlations()
            self.analyze_temporal_patterns()
            self.perform_hypothesis_tests()

        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("NUMEROLOGY vs VEDIC ASTROLOGY CORRELATION ANALYSIS REPORT")
        report_lines.append("=" * 80)
        report_lines.append("")

        # System overview
        report_lines.append("SYSTEM OVERVIEW:")
        temporal = self.results["temporal_patterns"]
        system_analysis = temporal["system_wide_analysis"]
        report_lines.append(
            "  Analysis Period: "
            f"{temporal['temporal_characteristics']['date_range']['start']} to "
            f"{temporal['temporal_characteristics']['date_range']['end']}"
        )
        obs_count = temporal["temporal_characteristics"]["total_observations"]
        report_lines.append(f"  Total Observations: {obs_count:,} days")
        report_lines.append(
            f"  - Avg correlation: {system_analysis['average_planet_correlation']:.3f}"
        )
        report_lines.append("")

        # Key findings
        report_lines.append("KEY FINDINGS:")
        report_lines.append(
            f"  - Overall system correlation: {system_analysis['overall_correlation']:.3f}"
        )
        report_lines.append(
            f"  - Correlation range: "
            f"{system_analysis['correlation_range']['min']:.3f} to "
            f"{system_analysis['correlation_range']['max']:.3f}"
        )
        report_lines.append("")

        # Equivalence tests (hypothesis.yaml)
        report_lines.append("EQUIVALENCE TESTS (TOST):")
        hypo_tests = self.results["hypothesis_tests"]
        k = hypo_tests["H1_kappa"]
        if "kappa" in k:
            report_lines.append(
                f"  - H1 kappa = {k['kappa']:.4f}, 90% CI "
                f"{k['ci90_tost'][0]:.4f} to {k['ci90_tost'][1]:.4f}, "
                f"margin +-{k['margin_kappa']}, p = {k['p_tost']:.4g}, "
                f"equivalent: {k['equivalent']}"
            )
        shown = [t for t in hypo_tests["H2_planets"] if t.get("equivalent")]
        report_lines.append(
            f"  - H2 planets shown equivalent within +-0.10: "
            f"{len(shown)}/{len(hypo_tests['H2_planets'])}"
        )
        report_lines.append("")

        # Detailed planet analysis
        report_lines.append("PLANET-BY-PLANET ANALYSIS:")
        report_lines.append("-" * 50)

        for planet_name, analysis in self.results["planet_correlations"].items():
            corr_metrics = analysis["correlation_metrics"]
            vol_analysis = analysis["volatility_analysis"]

            report_lines.append(f"{analysis['planet_name']}:")
            report_lines.append(
                f"  Correlation: {corr_metrics['pearson_correlation']:.3f} "
                f"({corr_metrics['correlation_strength']})"
            )
            report_lines.append(
                f"  Volatility ratio (Ast/Num): {vol_analysis['volatility_ratio']:.1f}x"
            )
            report_lines.append(
                f"  Change frequency ratio (Ast/Num): {vol_analysis['change_ratio']:.1f}x"
            )
            report_lines.append("")

        report_lines.append("=" * 80)

        return "\n".join(report_lines)

    def save_results(self, output_path: Optional[str] = None) -> str:
        """
        Save analysis results to JSON file.

        Args:
            output_path: Optional custom output path

        Returns:
            Path to saved file
        """
        if output_path is None:
            data_dir = str(study_data_dir("numerology_vs_astrology"))
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(
                data_dir, f"correlation_analysis_{timestamp}.json"
            )

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        print(f"Results saved to {output_path}")
        return output_path

    def _count_changes(self, series: pd.Series, threshold: float = 1.0) -> int:
        """Count the number of significant changes in a time series."""
        changes = 0
        for i in range(1, len(series)):
            if abs(series.iloc[i] - series.iloc[i - 1]) >= threshold:
                changes += 1
        return changes

    def _calculate_entropy(self, series: pd.Series, bins: int = 10) -> float:
        """Calculate Shannon entropy of a series."""
        hist, _ = np.histogram(series, bins=bins, density=True)
        hist = hist[hist > 0]  # Remove zeros
        return -np.sum(hist * np.log2(hist))

    def _interpret_correlation(self, correlation: float) -> str:
        """Interpret correlation strength."""
        abs_corr = abs(correlation)
        if abs_corr < 0.1:
            return "no correlation"
        elif abs_corr < 0.3:
            return "weak correlation"
        elif abs_corr < 0.5:
            return "moderate correlation"
        elif abs_corr < 0.7:
            return "strong correlation"
        else:
            return "very strong correlation"

    def _calculate_effect_size(self, correlation: float, sample_size: int) -> float:
        """Calculate effect size for correlation."""
        # Using Cohen's f² for correlation effect size
        r_squared = correlation**2
        if r_squared < 0.02:
            return 0.0  # Negligible
        elif r_squared < 0.13:
            return 0.2  # Small
        elif r_squared < 0.26:
            return 0.5  # Medium
        else:
            return 0.8  # Large

    def _test_independence(
        self, series1: pd.Series, series2: pd.Series
    ) -> Dict[str, Any]:
        """Return the binned mutual information of two series (descriptive only)."""
        # Simple bin-based independence test
        hist_2d, _, _ = np.histogram2d(series1, series2, bins=10)
        hist_2d = hist_2d / hist_2d.sum()

        # Calculate mutual information
        hist_marg1 = hist_2d.sum(axis=1)
        hist_marg2 = hist_2d.sum(axis=0)

        mi = 0
        for i in range(hist_2d.shape[0]):
            for j in range(hist_2d.shape[1]):
                if hist_2d[i, j] > 0:
                    mi += hist_2d[i, j] * np.log2(
                        hist_2d[i, j] / (hist_marg1[i] * hist_marg2[j])
                    )

        # Calculate normalized mutual information
        entropy1 = -np.sum(
            hist_marg1[hist_marg1 > 0] * np.log2(hist_marg1[hist_marg1 > 0])
        )
        entropy2 = -np.sum(
            hist_marg2[hist_marg2 > 0] * np.log2(hist_marg2[hist_marg2 > 0])
        )

        normalized_mi = (
            mi / min(entropy1, entropy2) if min(entropy1, entropy2) > 0 else 0
        )

        return {"mutual_information": float(mi), "normalized_mi": float(normalized_mi)}

    def _calculate_transition_probabilities(self) -> Dict[str, Any]:
        """Calculate transition probabilities for numerology active planets."""
        active_planets = self.data["numerology_active_planet"].tolist()
        transitions = {}

        for i in range(1, len(active_planets)):
            current = active_planets[i - 1]
            next_planet = active_planets[i]

            if current not in transitions:
                transitions[current] = {}

            if next_planet not in transitions[current]:
                transitions[current][next_planet] = 0

            transitions[current][next_planet] += 1

        # Normalize to probabilities
        for current, next_dict in transitions.items():
            total = sum(next_dict.values())
            for next_planet in next_dict:
                next_dict[next_planet] /= total

        return transitions

    def _analyze_seasonal_patterns(self) -> Dict[str, Any]:
        """Analyze seasonal patterns in the data."""
        # Group by month
        monthly_data = self.data.groupby(self.data["date"].dt.month)

        seasonal_patterns = {}

        for month, month_data in monthly_data:
            # Calculate average correlations for this month
            monthly_correlations = []
            for planet in self.planets:
                num_col = f"numerology_{planet.name}"
                ast_col = f"astrology_{planet.name}"
                corr = month_data[num_col].corr(month_data[ast_col])
                monthly_correlations.append(corr)

            seasonal_patterns[f"month_{month}"] = {
                "avg_correlation": float(np.mean(monthly_correlations)),
                "correlation_std": float(np.std(monthly_correlations)),
                "sample_size": len(month_data),
            }

        return seasonal_patterns


def _corr(x: np.ndarray, y: np.ndarray) -> float:
    """Return Pearson's r, or NaN when either resample is constant."""
    if x.std() == 0 or y.std() == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def main():
    """Run the descriptive analysis and the equivalence tests on the data file."""
    analyzer = CorrelationAnalyzer()
    analyzer.load_data()
    analyzer.analyze_correlations()
    analyzer.analyze_temporal_patterns()
    analyzer.perform_hypothesis_tests()
    print(analyzer.generate_report())
    analyzer.save_results()


if __name__ == "__main__":
    main()
