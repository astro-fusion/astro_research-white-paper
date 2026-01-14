"""
Configuration Module

Handles configuration management including:
- Vedic constants (planets, signs, numbers)
- Settings management with YAML support
- Environment-specific configurations
"""

from .constants import *
from .settings import Config, load_config

__all__ = [
    # constants
    "PLANETS",
    "SIGNS",
    "NUMBER_TO_PLANET",
    # settings
    "Config",
    "load_config",
]
