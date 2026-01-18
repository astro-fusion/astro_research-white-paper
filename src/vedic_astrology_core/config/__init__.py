"""
Configuration Module

Handles configuration management including:
- Vedic constants (planets, signs, numbers)
- Settings management with YAML support
- Environment-specific configurations
"""

from .constants import PLANET_NAMES, PLANETS, SIGNS, Planet
from .settings import Config, load_config

__all__ = [
    # constants
    "Planet",
    "PLANETS",
    "SIGNS",
    "PLANET_NAMES",
    # settings
    "Config",
    "load_config",
]
