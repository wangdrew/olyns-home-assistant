"""Olyns Recycling Bin — Sensor Platform.

Creates four sensors under a single "Olyns" device:
  • sensor.<name>_status        — open / closed_maintenance / closed_hours / closed_unknown
  • sensor.<name>_aluminum      — 0–100 %
  • sensor.<name>_plastic       — 0–100 %
  • sensor.<name>_glass         — 0–100 %

Polling is rate-limited to once every 10 minutes so we stay friendly to the
Olyns API.  All four sensors share a single HTTP fetch via DataUpdateCoordinator,
so there is never more than one request per poll cycle regardless of how many
sensors are active.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

import requests
import voluptuous as vol

from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import CONF_NAME, PERCENTAGE
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import (
    CONF_COLLECTOR_ID,
    DEFAULT_NAME,
    DOMAIN,
    OLYNS_API_URL,
    SCAN_INTERVAL_SECONDS,
    STATUS_CLOSED_HOURS,
    STATUS_CLOSED_MAINTENANCE,
    STATUS_CLOSED_UNKNOWN,
    STATUS_LABELS,
    STATUS_OPEN,
)

_LOGGER = logging.getLogger(__name__)

# ── YAML schema for configuration.yaml ──────────────────────────────────────

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_COLLECTOR_ID): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)

# ── Sensor definitions ───────────────────────────────────────────────────────

# key → (friendly suffix, icon, unit or None)
SENSOR_TYPES: dict[str, tuple[str, str, str | None]] = {
    "status":   ("Status",   "mdi:recycle",                  None),
    "aluminum": ("Aluminum", "mdi:bottle-soda-classic-outline", PERCENTAGE),
    "plastic":  ("Plastic",  "mdi:bottle-soda-outline",       PERCENTAGE),
    "glass":    ("Glass",    "mdi:bottle-wine-outline",        PERCENTAGE),
}

# ── Platform setup ───────────────────────────────────────────────────────────

async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the Olyns sensor platform from configuration.yaml."""

    collector_id: str = config[CONF_COLLECTOR_ID]
    device_name: str = config[CONF_NAME]

    coordinator = OlynsDataCoordinator(hass, collector_id, device_name)

    # Perform the first fetch before adding entities.  If the API is
    # unreachable at startup, HA will log a warning and retry on the next
    # scheduled interval — sensors will appear as "unavailable" in the
    # meantime, which is the correct behaviour.
    await coordinator.async_refresh()

    async_add_entities(
        OlynsSensor(coordinator, key, device_name, collector_id)
        for key in SENSOR_TYPES
    )


# ── Data coordinator ─────────────────────────────────────────────────────────

class OlynsDataCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Single coordinator that fetches all four values in one API call."""

    def __init__(
        self,
        hass: HomeAssistant,
        collector_id: str,
        device_name: str,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{collector_id}",
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.collector_id = collector_id
        self.device_name = device_name

    # HA calls this on every poll cycle (every 10 minutes)
    async def _async_update_data(self) -> dict[str, Any]:
        try:
            # requests is blocking, so we hand it off to a thread pool
            return await self.hass.async_add_executor_job(self._fetch)
        except UpdateFailed:
            raise
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(f"Unexpected error fetching Olyns data: {err}") from err

    def _fetch(self) -> dict[str, Any]:
        """Blocking HTTP fetch — runs in an executor thread."""
        try:
            response = requests.get(OLYNS_API_URL, timeout=10)
            response.raise_for_status()
        except requests.RequestException as err:
            raise UpdateFailed(f"Olyns API request failed: {err}") from err

        data = response.json()
        collectors = data.get("collectors", [])

        # Match by id (API may return int or str, so normalise both sides)
        target = next(
            (c for c in collectors if str(c.get("id")) == str(self.collector_id)),
            None,
        )

        if target is None:
            raise UpdateFailed(
                f"Collector '{self.collector_id}' not found in Olyns API response. "
                "Check your collector_id in configuration.yaml."
            )

        bin_levels = target.get("bin_levels", {})
        op_status = target.get("operational_status", "")
        outside_hours = target.get("outside_operating_hours", False)
        bin_status = target.get("status", "")

        # Mirror the status logic from the original proxy script
        if op_status == "needs-maintenance":
            overall_status = STATUS_CLOSED_MAINTENANCE
        elif outside_hours is True:
            overall_status = STATUS_CLOSED_HOURS
        elif bin_status != "Active" and op_status != "ready":
            overall_status = STATUS_CLOSED_UNKNOWN
        else:
            overall_status = STATUS_OPEN

        return {
            "status":   overall_status,
            "aluminum": bin_levels.get("alu_bin_level_pct", 0),
            "plastic":  bin_levels.get("pet_bin_level_pct", 0),
            "glass":    bin_levels.get("gls_bin_level_pct", 0),
        }


# ── Sensor entity ────────────────────────────────────────────────────────────

class OlynsSensor(CoordinatorEntity[OlynsDataCoordinator], SensorEntity):
    """One of the four Olyns sensors (status, aluminum, plastic, glass)."""

    def __init__(
        self,
        coordinator: OlynsDataCoordinator,
        sensor_key: str,
        device_name: str,
        collector_id: str,
    ) -> None:
        super().__init__(coordinator)

        suffix, icon, unit = SENSOR_TYPES[sensor_key]

        self._sensor_key = sensor_key
        self._attr_name = f"{device_name} {suffix}"
        self._attr_unique_id = f"olyns_{collector_id}_{sensor_key}"
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit

        # Percentage sensors have a meaningful numeric state class;
        # the status sensor is a plain string/enum.
        if unit is not None:
            self._attr_state_class = SensorStateClass.MEASUREMENT

    # ── State ────────────────────────────────────────────────────────────────

    @property
    def native_value(self) -> Any:
        if self.coordinator.data is None:
            return None
        raw = self.coordinator.data.get(self._sensor_key)
        # For the status sensor, surface a human-readable label
        if self._sensor_key == "status":
            return STATUS_LABELS.get(raw, raw)
        return raw

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the raw status key as an attribute (useful for conditions)."""
        if self._sensor_key == "status" and self.coordinator.data:
            return {"raw_status": self.coordinator.data.get("status")}
        return {}

    # ── Device grouping ──────────────────────────────────────────────────────

    @property
    def device_info(self) -> dict[str, Any]:
        """Group all four sensors under a single Olyns device in the UI."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.collector_id)},
            "name": self.coordinator.device_name,
            "manufacturer": "Olyns",
            "model": "Smart Recycling Bin",
            "entry_type": "service",
        }
