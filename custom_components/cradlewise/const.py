"""Constants for the Cradlewise HA integration."""

DOMAIN = "cradlewise"

CONF_EMAIL = "email"
CONF_PASSWORD = "password"

# Polling intervals
DEFAULT_SCAN_INTERVAL = 30  # seconds

PLATFORMS: list[str] = ["sensor", "binary_sensor"]
