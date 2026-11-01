"""Constants for the Satel Integra integration."""

DEFAULT_CONF_ARM_HOME_MODE = "1"
DEFAULT_PORT = 7094

DOMAIN = "satel_integra"

SUBENTRY_TYPE_PARTITION = "partition"
SUBENTRY_TYPE_ZONE = "zone"
SUBENTRY_TYPE_OUTPUT = "output"
SUBENTRY_TYPE_SWITCHABLE_OUTPUT = "switchable_output"

CONF_PARTITION_NUMBER = "partition_number"
CONF_ZONE_NUMBER = "zone_number"
CONF_OUTPUT_NUMBER = "output_number"
CONF_SWITCHABLE_OUTPUT_NUMBER = "switchable_output_number"

CONF_ARM_HOME_MODE = "arm_home_mode"
CONF_ZONE_TYPE = "type"
CONF_ENCRYPTION_KEY = "encryption_key"

CONF_ENABLE_TEMPERATURE_SENSOR = "enable_temperature_sensor"

# Options added by the extended (custom) version
CONF_ALL_PARTITIONS_PANEL = "all_partitions_panel"
CONF_ALL_PARTITIONS = "all_partitions"
CONF_USE_CODE_FOR_PANELS = "use_code_for_panels"
CONF_ALL_ARM_MODES = "all_arm_modes"
CONF_EVENT_LOG_INTERVAL = "event_log_interval"

DEFAULT_EVENT_LOG_INTERVAL = 10

EVENT_SATEL = f"{DOMAIN}_event"
