# Olyns Recycling — Home Assistant Integration

Basic vibe coded Home Assistant integration to periodically poll the Olyns recycling API and display a local bin status on a Home Assistant dashboard

Adds four sensors for your Olyns recycling bin and a dashboard card that
shows fill levels when the bin is open, or a friendly status when it isn't.

---

## Files

```
custom_components/olyns/
  __init__.py
  const.py
  manifest.json
  sensor.py
olyns_dashboard_card.yaml
```

---

## Installation

### 1 — Copy the custom component

Copy the `custom_components/olyns/` folder into your Home Assistant config
directory so the path looks like:

```
/config/custom_components/olyns/__init__.py
/config/custom_components/olyns/const.py
/config/custom_components/olyns/manifest.json
/config/custom_components/olyns/sensor.py
```

> **Tip:** The config directory is the same folder that contains
> `configuration.yaml`.  If you use the Samba or SSH add-on you can drag the
> folder in directly.

### 2 — Find your collector ID

Your collector ID is the number at the end of the URL your proxy was using,
e.g. `http://localhost:8200/170` → ID is `170`.

### 3 — Add to configuration.yaml

```yaml
sensor:
  - platform: olyns
    collector_id: "170"   # ← replace with your actual ID
    name: "Olyns"         # optional — changes entity IDs if you rename this
```

### 4 — Restart Home Assistant

**Settings → System → Restart**

After restart you should see four new entities in **Settings → Entities**:

| Entity ID | Description |
|---|---|
| `sensor.olyns_status` | Open / Closed – Maintenance / Closed – After Hours / Unavailable |
| `sensor.olyns_aluminum` | Aluminum fill level (%) |
| `sensor.olyns_plastic` | Plastic fill level (%) |
| `sensor.olyns_glass` | Glass fill level (%) |

All four are grouped under a single **Olyns** device visible in
**Settings → Devices & Services → Helpers** (or search "Olyns" in Devices).

### 5 — Add the dashboard card

1. Open your dashboard
2. Three-dot menu → **Edit Dashboard**
3. **Add Card** → scroll to bottom → **Manual**
4. Paste the contents of `olyns_dashboard_card.yaml`
5. Adjust entity IDs if you used a different `name:` in step 3

---

## How the polling works

All four sensors share a single HTTP request made once every **10 minutes**
via Home Assistant's `DataUpdateCoordinator`.  The Olyns API is never hit
more than once per poll cycle, regardless of how many sensors are on screen.

---

## Troubleshooting

| Symptom | Check |
|---|---|
| Sensors show "Unavailable" | HA log → look for `olyns` warnings. Usually a wrong collector ID or the Olyns API being down. |
| Entity IDs don't match the card | You used a different `name:` in configuration.yaml. Either update the card YAML or change the name back to "Olyns". |
| Status card doesn't appear | Confirm mushroom-cards is installed via HACS, or use the fallback markdown card in the YAML comments. |

---

## Updating the poll interval

Edit `const.py` and change `SCAN_INTERVAL_SECONDS = 600`.
Restart HA after saving.
