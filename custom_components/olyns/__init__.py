"""Olyns Recycling Bin — Home Assistant Integration.

Place this folder at:
  <config>/custom_components/olyns/

Then add to configuration.yaml:
  sensor:
    - platform: olyns
      collector_id: "170"   # ← replace with your collector ID
      name: "Olyns"         # optional, defaults to "Olyns"
"""

from .const import DOMAIN  # noqa: F401
