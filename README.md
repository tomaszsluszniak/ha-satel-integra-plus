# Satel Integra (extended) for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)
[![Validate](https://github.com/tomaszsluszniak/ha-satel-integra-plus/actions/workflows/validate.yml/badge.svg)](https://github.com/tomaszsluszniak/ha-satel-integra-plus/actions/workflows/validate.yml)

An extended version of the built-in **Satel Integra** integration for **Satel INTEGRA** panels
with an **ETHM-1 / ETHM-1 Plus / INT-RS** module. It keeps the same domain (`satel_integra`), so it
replaces the built-in integration **without reconfiguration**: the existing entry, partitions,
zones, outputs and entity IDs stay as they are, and new entities, options and actions are added.

[![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=tomaszsluszniak&repository=ha-satel-integra-plus&category=integration)
[![Open your Home Assistant instance and start setting up Satel Integra.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=satel_integra)

> 🇵🇱 Opis po polsku: [docs/README.pl.md](docs/README.pl.md)

## What it adds to the built-in integration

The built-in integration creates one alarm panel per partition and offers two arming modes. Arming
the whole house means several separate commands, and a wrong code or a refused arming is not
reported at all. The underlying `satel-integra` library implements only part of the INT-RS /
ETHM-1 protocol.

| | built-in `satel_integra` | this integration |
|---|---|---|
| arm / disarm all partitions with one command | no (one panel per partition) | **"All partitions" panel** |
| Satel arming modes in the UI | away = 0, home = one configured mode | **all four modes**: away = 0 (full), custom bypass = 1 (full + bypasses), home = 2 (no interior zones), night = 3 (no interior zones, no entry delay) |
| result of arm / disarm / output commands | not checked | wrong code, no access, "cannot arm, force possible", no response reported as errors |
| zone tamper, alarm, alarm memory, bypass, isolate, masking | no | binary sensors and a **bypass switch** per zone |
| partitions with violated zones (ready to arm), alarm memory | no | binary sensors and panel attributes |
| system status and troubles | no (2026.10) | service mode, system trouble, AC, battery and other part 1 troubles |
| panel event log | no | **event entity** and `satel_integra_event` for every new event, with texts and names |
| force arming, bypass zones, toggle several outputs, clear trouble memory | no | **actions** |
| Lovelace card | no | **bundled card**, loaded automatically |

## Installation (HACS)

1. Open the repository in HACS (it is added as a custom repository on the way):

   [![Open your Home Assistant instance and open this repository in HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=tomaszsluszniak&repository=ha-satel-integra-plus&category=integration)

   Or manually: HACS → ⋮ → **Custom repositories** → `https://github.com/tomaszsluszniak/ha-satel-integra-plus`, type **Integration**.
2. **Download** Satel Integra (extended) and restart Home Assistant.
3. If you already use the built-in Satel Integra, you are done: the existing entry now runs this
   version. Otherwise add the integration:

   [![Open your Home Assistant instance and start setting up Satel Integra.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=satel_integra)

   Or Settings → Devices & services → **Add integration** → **Satel Integra**.

Manual install: copy `custom_components/satel_integra` to `/config/custom_components/` and restart.

Home Assistant installs `satel-integra==1.6.0` on startup. Requires Home Assistant 2026.10 or newer.

**Going back:** remove the integration in HACS and restart. The built-in integration takes over
the same entry again; entities added by this version become orphaned and can be deleted.

## Options

Settings → Devices & services → Satel Integra → **Configure**:

| Option | Default | |
|---|---|---|
| Code | – | user code for outputs, zone bypass switches and actions (and for the alarm panels, see below) |
| Use the stored code for alarm panels | off | arm and disarm without entering a code; anyone with access to Home Assistant can then disarm |
| All Satel arming modes in alarm panels | on | away = 0, custom bypass = 1, home = 2, night = 3; when off: away = 0, home = the mode set for the partition |
| "All partitions" alarm panel | on | one panel for all partitions |
| Partitions controlled by "All partitions" | all | a subset of the configured partitions |
| Event log polling interval | 10 s | `0` disables the event entity and events |

Partitions, zones and outputs are configured as before (sub-entries of the integration).

## Entities

**Alarm panels.** One per partition, as in the built-in integration, plus **All partitions**. The
state shows the arming mode (`armed_away` = 0, `armed_custom_bypass` = 1, `armed_home` = 2,
`armed_night` = 3), with Satel mode names as state labels. Attributes: `arm_mode` (0–3),
`violated_zones`, `alarm_memory`, `first_code_entered`, `temporary_blocked`; on the All partitions
panel also the state of every partition, `armed_partitions`, `disarmed_partitions`,
`partially_armed` and `ready_to_arm`. All partitions sends one command for all partitions; when
partitions are armed in different modes it shows the strongest one.

**Zones.** The zone sensor as before, plus *Tamper* and *Alarm*, a *Bypass* switch, and (disabled
by default) *Alarm memory*, *Tamper alarm*, *Isolated*, *Masked*, *No violation trouble* and
*Long violation trouble*.

**Partitions.** *Violated zones* (not ready to arm) and *Alarm memory*, and (disabled by default)
fire alarm memory, temporarily blocked, first code entered, verified alarm and warning alarm.

**Panel.** *Service mode*, *System trouble*, *AC power trouble*, *Battery trouble*, and (disabled
by default) the other system troubles: outputs OUT1–4, keypad and expander supply, DT1 / DT2 /
DTM, clock, monitoring stations, EEPROM, RAM, restart memory. *Event log* event entity.

## Lovelace card

The integration ships a card and loads it on every dashboard automatically, no resource to add.

```yaml
type: custom:satel-integra-alarm-card
entity: alarm_control_panel.<panel>_all_partitions
title: Alarm              # optional
show_zones: true
show_outputs: true
show_history: true
confirm_outputs: true     # a second tap is needed to switch an output
exclude: []               # entities to leave out
```

A ring with one segment per partition, coloured by its arming mode, and the overall state; buttons
for the four arming modes and disarming, with a keypad when a code is required; partitions with
violated zones and alarm memory; zone tiles (violation, tamper, alarm, bypass button); output
tiles; active troubles; the last event and the recent event log. Partitions, zones and outputs are
found automatically. Polish and English.

## Actions

All actions take an optional `config_entry_id` (needed only with more than one panel) and an
optional `code` (default: the code from the options).

| Action | |
|---|---|
| `satel_integra.arm` | `partitions` (default: all), `mode` 0–3, `force`, `no_bypass` (no bypasses and no exit delay, INT-RS Plus / ETHM-1 Plus 2.19+) |
| `satel_integra.disarm` | `partitions`, `clear_alarm` |
| `satel_integra.clear_alarm` | `partitions` |
| `satel_integra.bypass_zones` | `zones`, `isolate` |
| `satel_integra.unbypass_zones` | `zones` |
| `satel_integra.set_outputs` | `outputs`, `state`: `on` / `off` / `toggle`, all in one command |
| `satel_integra.clear_trouble_memory` | – |
| `satel_integra.read_event_log` | `count` (1–200), returns the events as a response |

```yaml
# force arming of selected partitions in mode 0
action: satel_integra.arm
data:
  partitions: [1, 2, 4]
  mode: 0
  force: true
```

## Events

The panel event log is polled (the protocol has no push for it). Every new record is fired as
`satel_integra_event` and on the *Event log* entity:

```yaml
config_entry_id: 01K...
index: 258
time: "2026-11-01T17:47:00"
class: arming        # zone_alarm, partition_alarm, arming, bypass, access_control, trouble, user_function, system
code: 10
restore: false
text: Disarming      # event text from the panel, in the panel language
partition: 1
partition_name: Ground floor
source: 3
source_name: John    # zone or user name, depending on the event
kind: 2
object: 0
```

## Fixes to `satel-integra` 1.6.0

Applied from the integration (`satel_ext.py`) without forking the library, which is why the
library version is pinned:

- **Encrypted connections:** the encrypted transport read a frame with `StreamReader.read(n)`,
  which may return fewer bytes when TCP splits the frame; the truncated frame fails to decrypt
  and the connection is dropped. Fixed with `readexactly`.
- **INT-RS v1.x / ETHM-1 (not Plus):** the library always sends 32-byte zone/output masks, which
  these modules drop silently. Commands added here send 16 bytes for numbers up to 128; with
  these modules switch outputs with `satel_integra.set_outputs`.
- Commands added on top of the library: 19 more state commands in monitoring, force arming,
  arming without bypasses, zone bypass / unbypass / isolate, outputs on / off / toggle, clearing
  the trouble memory, event log with event texts and device names.

## Releases

Push a tag to publish: `git tag v1.0.1 && git push origin v1.0.1`. The release workflow sets the
version in `manifest.json` and the card, builds `satel_integra.zip` (what HACS installs) and takes
the release notes from [CHANGELOG.md](CHANGELOG.md).

## Credits and license

- Based on the Home Assistant `satel_integra` integration (Apache License 2.0) by @Tommatheussen
  and contributors.
- Uses [satel-integra](https://github.com/c-soft/satel_integra) (MIT).
- Protocol: *INT-RS / ETHM-1 Plus integration protocol description*, SATEL 2023-02-22.
- Not affiliated with SATEL sp. z o.o.

Licensed under the Apache License 2.0.
