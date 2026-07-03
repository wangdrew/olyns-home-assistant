"""Constants for the Olyns Recycling integration."""

DOMAIN = "olyns"

OLYNS_API_URL = "https://api.olyns.com/api/collectors?program=olyns"

# Polling interval in seconds — 10 minutes to respect the Olyns API
SCAN_INTERVAL_SECONDS = 600

DEFAULT_NAME = "Olyns"

CONF_COLLECTOR_ID = "collector_id"

# Status values returned by the API logic
STATUS_OPEN = "open"
STATUS_CLOSED_MAINTENANCE = "closed_maintenance"
STATUS_CLOSED_HOURS = "closed_hours"
STATUS_CLOSED_UNKNOWN = "closed_unknown"

# Human-readable labels for the status sensor
STATUS_LABELS = {
    STATUS_OPEN: "Open",
    STATUS_CLOSED_MAINTENANCE: "Closed – Maintenance",
    STATUS_CLOSED_HOURS: "Closed – After Hours",
    STATUS_CLOSED_UNKNOWN: "Unavailable",
}
