"""
Configuration Management

Handles application settings and configuration management with YAML support.
Provides centralized configuration for all modules in the system.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Union

try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False
    yaml = None

from .constants import AYANAMSA_SYSTEMS, HOUSE_SYSTEMS

# Default configuration
DEFAULT_CONFIG: Dict[str, Any] = {
    "astrology": {
        "ayanamsa_system": "lahiri",
        "house_system": "placidus",
        "sidereal_zodiac": True,
        "default_latitude": 28.6139,  # Delhi
        "default_longitude": 77.1025,  # Delhi
        "default_timezone": "Asia/Kolkata",
    },
    "numerology": {
        "sunrise_correction": True,
        "vedic_day_calculation": True,
        "master_numbers_reduced": True,  # Reduce 11,22,33 to 2,4,6
    },
    "dignity": {
        "scoring_scale": "0-100",
        "include_retrograde_bonus": True,
        "include_combustion_penalty": True,
        "include_shadbala": False,  # Advanced feature, disabled by default
        "friendship_matrix": "traditional",
    },
    "visualization": {
        "default_library": "plotly",  # 'plotly' or 'matplotlib'
        "color_scheme": "default",
        "figure_size": [10, 6],
        "dpi": 150,
        "interactive_charts": True,
    },
    "performance": {
        "cache_ephemeris": True,
        "cache_timeout_hours": 24,
        "batch_processing": True,
        "max_cache_size_mb": 100,
    },
    "logging": {
        "level": "INFO",
        "file_logging": False,
        "log_directory": "logs",
        "max_log_files": 30,
        "log_format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    },
    "output": {
        "decimal_precision": 2,
        "include_symbols": True,
        "language": "en",
        "report_format": "text",
    },
}


class Config:
    """
    Configuration management class.

    Handles loading, validation, and access to configuration settings
    for the Vedic Numerology-Astrology system.
    """

    def __init__(self, config_file: Optional[Union[str, Path]] = None):
        """
        Initialize configuration.

        Args:
            config_file: Path to YAML configuration file (optional)
        """
        self._config = DEFAULT_CONFIG.copy()
        self.config_file = config_file

        if config_file and YAML_AVAILABLE:
            self.load_config(config_file)

        self._validate_config()

    def load_config(self, config_file: Union[str, Path]) -> None:
        """
        Load configuration from YAML file.

        Args:
            config_file: Path to configuration file

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML parsing fails
        """
        if not YAML_AVAILABLE:
            raise ImportError("PyYAML is required for configuration file support")

        config_path = Path(config_file)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            user_config = yaml.safe_load(f)

        # Deep merge user config with defaults
        self._deep_merge(self._config, user_config)

    def save_config(self, config_file: Union[str, Path]) -> None:
        """
        Save current configuration to YAML file.

        Args:
            config_file: Path to save configuration file

        Raises:
            ImportError: If PyYAML is not available
        """
        if not YAML_AVAILABLE:
            raise ImportError("PyYAML is required to save configuration files")

        config_path = Path(config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(self._config, f, default_flow_style=False, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-separated key.

        Args:
            key: Dot-separated configuration key (e.g., 'astrology.ayanamsa_system')
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split(".")
        value: Any = self._config

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value by dot-separated key.

        Args:
            key: Dot-separated configuration key
            value: Value to set
        """
        keys = key.split(".")
        config = self._config

        # Navigate to the parent of the final key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        # Set the final value
        config[keys[-1]] = value

    def reset_to_defaults(self) -> None:
        """Reset configuration to default values."""
        self._config = DEFAULT_CONFIG.copy()

    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> None:
        """
        Deep merge update dictionary into base dictionary.

        Args:
            base: Base dictionary to merge into
            update: Dictionary with updates
        """
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _validate_config(self) -> None:
        """
        Validate configuration values.

        Raises:
            ValueError: If configuration contains invalid values
        """
        # Validate Ayanamsa system
        ayanamsa = self.get("astrology.ayanamsa_system")
        if ayanamsa and ayanamsa.lower() not in [
            k.lower() for k in AYANAMSA_SYSTEMS.keys()
        ]:
            valid_systems = list(AYANAMSA_SYSTEMS.keys())
            raise ValueError(
                f"Invalid Ayanamsa system '{ayanamsa}'. Valid systems: {valid_systems}"
            )

        # Validate house system
        house_system = self.get("astrology.house_system")
        if house_system and house_system.lower() not in [
            k.lower() for k in HOUSE_SYSTEMS.keys()
        ]:
            valid_systems = list(HOUSE_SYSTEMS.keys())
            raise ValueError(
                f"Invalid house system '{house_system}'. Valid systems: {valid_systems}"
            )

        # Validate visualization library
        viz_lib = self.get("visualization.default_library")
        if viz_lib and viz_lib.lower() not in ["plotly", "matplotlib"]:
            raise ValueError("Visualization library must be 'plotly' or 'matplotlib'")

        # Validate coordinate ranges
        lat = self.get("astrology.default_latitude")
        lon = self.get("astrology.default_longitude")

        if lat is not None and not (-90 <= lat <= 90):
            raise ValueError(f"Default latitude must be between -90 and 90, got {lat}")

        if lon is not None and not (-180 <= lon <= 180):
            raise ValueError(
                f"Default longitude must be between -180 and 180, got {lon}"
            )

    def to_dict(self) -> Dict[str, Any]:
        """
        Get configuration as dictionary.

        Returns:
            Copy of current configuration
        """
        return self._config.copy()

    def __getitem__(self, key: str) -> Any:
        """Get configuration value using dictionary-style access."""
        return self.get(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Set configuration value using dictionary-style access."""
        self.set(key, value)

    def __contains__(self, key: str) -> bool:
        """Check if configuration key exists."""
        return self.get(key) is not None

    def __repr__(self) -> str:
        """String representation of configuration."""
        return f"Config({self.config_file or 'defaults'})"


def load_config(config_file: Optional[Union[str, Path]] = None) -> Config:
    """
    Load configuration from file or create with defaults.

    Args:
        config_file: Path to configuration file (optional)

    Returns:
        Config object
    """
    return Config(config_file)


def create_default_config_file(
    config_file: Union[str, Path] = "config/default_config.yaml",
) -> None:
    """
    Create a default configuration file.

    Args:
        config_file: Path where to create the config file
    """
    if not YAML_AVAILABLE:
        raise ImportError("PyYAML is required to create configuration files")

    config = Config()
    config.save_config(config_file)
    print(f"Default configuration file created at: {config_file}")


def get_config_paths() -> Dict[str, Path]:
    """
    Get standard configuration file paths.

    Returns:
        Dictionary with paths for different config file locations
    """
    home = Path.home()
    cwd = Path.cwd()

    return {
        "user_home": home / ".vedic_numerology" / "config.yaml",
        "project_root": cwd / "config" / "default_config.yaml",
        "current_dir": cwd / "vedic_config.yaml",
        "system_config": Path("/etc/vedic_numerology/config.yaml"),
    }


def find_config_file() -> Optional[Path]:
    """
    Find an existing configuration file in standard locations.

    Returns:
        Path to first found configuration file, or None
    """
    config_paths = get_config_paths()

    for path in config_paths.values():
        if path.exists():
            return path

    return None


def load_or_create_config(config_file: Optional[Union[str, Path]] = None) -> Config:
    """
    Load configuration file or create with defaults if none exists.

    Args:
        config_file: Specific config file to load (optional)

    Returns:
        Config object
    """
    if config_file:
        return load_config(config_file)

    # Try to find existing config
    existing_config = find_config_file()
    if existing_config:
        return load_config(existing_config)

    # Return default config
    return Config()


# Global configuration instance
_global_config = None


def get_global_config() -> Config:
    """
    Get the global configuration instance.

    Returns:
        Global Config object
    """
    global _global_config
    if _global_config is None:
        _global_config = load_or_create_config()
    return _global_config


def set_global_config(config: Config) -> None:
    """
    Set the global configuration instance.

    Args:
        config: Config object to set as global
    """
    global _global_config
    _global_config = config


# Export key functions and classes
__all__ = [
    "Config",
    "load_config",
    "create_default_config_file",
    "get_config_paths",
    "find_config_file",
    "load_or_create_config",
    "get_global_config",
    "set_global_config",
    "DEFAULT_CONFIG",
]
