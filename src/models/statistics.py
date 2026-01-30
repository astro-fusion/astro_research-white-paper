"""
Statistical Analysis Module
===========================

This module implements the "Severe Testing" framework required for the scientific report.
It includes rigorous econometric and signal processing tests to evaluate the
hypothesis of planetary influence on financial markets.

Key Components:
1. Stationarity Tests (ADF, KPSS): Ensuring time series validity.
2. Spectral Analysis (Lomb-Scargle): Detecting periodicities in unevenly spaced data.
3. Granger Causality (VAR): Testing predictive precedence with Bonferroni correction.
4. Molchan Diagnosis: Evaluating binary event prediction skills.
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from scipy import stats

# Econometrics
from statsmodels.tsa.stattools import adfuller, kpss, grangercausalitytests
from statsmodels.tsa.api import VAR

# Astrophysics / Signal Processing
from astropy.timeseries import LombScargle

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_stationarity(timeseries: pd.Series, name: str = "Series") -> Dict[str, Any]:
    """
    Performs Augmented Dickey-Fuller (ADF) and KPSS tests to check for stationarity.
    
    Args:
        timeseries: The time series data.
        name: Name of the variable for reporting.
        
    Returns:
        Dictionary with test statistics and conclusion.
    """
    # Clean data (drop NaNs)
    ts_clean = timeseries.dropna()
    
    # ADF Test (Null: Unit Root Exists / Non-Stationary)
    adf_result = adfuller(ts_clean)
    adf_stat, adf_p = adf_result[0], adf_result[1]
    
    # KPSS Test (Null: Stationary)
    # Using 'c' for constant (stationarity around mean)
    try:
        kpss_result = kpss(ts_clean, regression='c', nlags='auto')
        kpss_stat, kpss_p = kpss_result[0], kpss_result[1]
    except Exception as e:
        logger.warning(f"KPSS test failed for {name}: {e}")
        kpss_stat, kpss_p = None, None

    # Conclusion
    is_stationary = (adf_p < 0.05) and (kpss_p > 0.05 if kpss_p else True)
    
    return {
        "Variable": name,
        "ADF Statistic": round(adf_stat, 4),
        "ADF p-value": round(adf_p, 4),
        "KPSS Statistic": round(kpss_stat, 4) if kpss_stat else "N/A",
        "KPSS p-value": round(kpss_p, 4) if kpss_p else "N/A",
        "Stationary": "Yes" if is_stationary else "No"
    }

def run_lomb_scargle(timeseries: pd.Series, 
                     min_period: float = 2.0, 
                     max_period: float = 3000.0) -> Tuple[np.ndarray, np.ndarray, float]:
    """
    Generates Lomb-Scargle Periodogram for unevenly spaced time series.
    
    Args:
        timeseries: Series with DatetimeIndex.
        min_period: Minimum cycle length in days.
        max_period: Maximum cycle length in days.
        
    Returns:
        periods: Array of periods tested.
        power: Array of spectral power density.
        fap_threshold: False Alarm Probability threshold (0.01 level).
    """
    # Time in days relative to start
    t = (timeseries.index - timeseries.index[0]).total_seconds() / 86400
    y = timeseries.values
    
    # Frequency grid
    frequency, power = LombScargle(t, y).autopower(
        minimum_frequency=1/max_period,
        maximum_frequency=1/min_period
    )
    
    # False Alarm Probability (1% significance)
    fap_threshold = LombScargle(t, y).false_alarm_level(0.01)
    
    periods = 1 / frequency
    return periods, power, fap_threshold

def run_granger_causality(data: pd.DataFrame, 
                          target_col: str, 
                          exog_cols: List[str], 
                          maxlag: int = 5,
                          bonferroni_n: int = 1) -> Dict[str, Any]:
    """
    Performs Granger Causality tests using a VAR model framework.
    
    Args:
        data: DataFrame containing target and exogenous variables.
        target_col: The dependent variable (e.g., 'Gold_Log_Return').
        exog_cols: List of independent variables (e.g., 'Mars_Sin', 'Mars_Cos').
        maxlag: Maximum lag order to test.
        bonferroni_n: Number of hypotheses tested (for p-value correction).
        
    Returns:
        Dictionary of results.
    """
    results = {}
    df_subset = data[[target_col] + exog_cols].dropna()
    
    # Check if we have enough data
    if len(df_subset) < 30:
        return {"Error": "Insufficient data"}
    
    # Fit VAR model to select best lag order based on AIC
    model = VAR(df_subset)
    try:
        lag_order_results = model.select_order(maxlags=maxlag)
        best_lag = lag_order_results.selected_orders['aic']
        if best_lag == 0:
            best_lag = 1 # Force at least lag 1 for causality test
    except Exception as e:
        logger.warning(f"VAR select_order failed: {e}. Defaulting to lag 1.")
        best_lag = 1

    # Run Granger Causality
    # statsmodels grangercausalitytests returns a dictionary: {lag: (result, [params])}
    # We test the hypothesis: Do exog_cols cause target_col?
    # Note: grangercausalitytests is bivariate. For multivariate, we use VAR model.test_causality
    
    final_model = model.fit(best_lag)
    causality_result = final_model.test_causality(target_col, exog_cols, kind='f')
    
    p_value = causality_result.pvalue
    f_stat = causality_result.test_statistic
    
    # Bonferroni Correction
    corrected_threshold = 0.05 / bonferroni_n
    is_significant = p_value < corrected_threshold
    
    return {
        "Target": target_col,
        "Predictors": ", ".join(exog_cols),
        "Best Lag (AIC)": int(best_lag),
        "F-Statistic": float(round(f_stat, 4)),
        "p-value": float(p_value), # Return raw p-value
        "Bonferroni Threshold": float(corrected_threshold),
        "Significant": "Yes" if is_significant else "No"
    }

def calculate_molchan_trajectory(predictions: pd.Series, 
                                 actuals: pd.Series, 
                                 thresholds: List[float]) -> pd.DataFrame:
    """
    Calculates the Molchan Diagram trajectory (Miss Rate vs. Fraction of Time Alarm).
    
    Args:
        predictions: Continuous signal (e.g., probability or strength).
        actuals: Binary event series (1 = Earthquake/Crash, 0 = None).
        thresholds: List of thresholds to define "Alarm".
        
    Returns:
        DataFrame with columns ['Tau', 'Nu'] (Fraction of Time, Miss Rate).
    """
    results = []
    
    total_time = len(predictions)
    total_events = actuals.sum()
    
    if total_events == 0:
        logger.warning("No events in actuals series.")
        return pd.DataFrame(columns=['Tau', 'Nu'])
    
    for thresh in thresholds:
        # Define Alarm: Prediction >= Threshold
        alarms = (predictions >= thresh).astype(int)
        
        # Fraction of Time declared as Alarm (Tau)
        tau = alarms.sum() / total_time
        
        # Misses: Event occurred (1) but Alarm was OFF (0)
        misses = ((actuals == 1) & (alarms == 0)).sum()
        
        # Miss Rate (Nu)
        nu = misses / total_events
        
        results.append({'Threshold': thresh, 'Tau': tau, 'Nu': nu})
        
    return pd.DataFrame(results).sort_values('Tau')

def run_monte_carlo_permutation_test(data: pd.DataFrame, 
                                     target_col: str, 
                                     exog_cols: List[str], 
                                     n_permutations: int = 1000) -> Dict[str, Any]:
    """
    Performs a Monte Carlo Permutation Test to evaluate the significance of
    correlations against a randomized baseline.
    
    The Null Hypothesis is that the relationship is random. By shuffling the
    planetary data (breaking temporal alignment) while keeping the market data
    intact, we generate a distribution of 'chance' correlations.
    
    Args:
        data: DataFrame with aligned data.
        target_col: The dependent variable.
        exog_cols: List of independent variables.
        n_permutations: Number of shuffles to perform.
        
    Returns:
        Dictionary containing:
        - 'actual_score': The R-squared or Correlation of the real data.
        - 'permuted_scores': List of scores from shuffled data.
        - 'p_value': Fraction of shuffled scores better than actual.
    """
    # Simple metric: Mean Absolute Correlation for simplicity in this demo,
    # or R-squared from a regression. Let's use R-squared from OLS for robustness.
    # Using statsmodels OLS.
    from statsmodels.regression.linear_model import OLS
    from statsmodels.tools.tools import add_constant
    
    df_clean = data[[target_col] + exog_cols].dropna()
    y = df_clean[target_col]
    X = df_clean[exog_cols]
    
    # 1. Calculate Actual Statistics
    model_actual = OLS(y, add_constant(X)).fit()
    actual_score = model_actual.rsquared
    
    permuted_scores = []
    
    # 2. Run Permutations
    X_perm = X.copy()
    
    logger.info(f"Running {n_permutations} Monte Carlo permutations for {target_col}...")
    
    for _ in range(n_permutations):
        # Shuffle X (planetary data) randomly
        # We use numpy.random.permutation on the indices to keep column integrity relative to each other?
        # No, usually we want to break the link between X and y. 
        # Shuffling the rows of X while keeping y fixed is sufficient.
        X_shuffled = X.sample(frac=1, replace=False).reset_index(drop=True)
        # We need to reset index to align with Y's index for OLS? 
        # OLS aligns by index. So we can just assign the values back.
        
        # Actually, simpler: Shuffle Y.
        y_shuffled = y.sample(frac=1, replace=False).values
        
        model_perm = OLS(y_shuffled, add_constant(X.values)).fit()
        permuted_scores.append(model_perm.rsquared)
        
    permuted_scores = np.array(permuted_scores)
    
    # 3. Calculate Empirical p-value
    # p = (Number of permuted scores >= actual score) / n_permutations
    n_better = np.sum(permuted_scores >= actual_score)
    p_value = n_better / n_permutations
    
    return {
        "actual_score": float(actual_score),
        "permuted_scores": permuted_scores.tolist(),
        "p_value": float(p_value)
    }
