# Changelog

## 1.0.0

- Extended version of the built-in Satel Integra integration (same domain, existing entry,
  partitions, zones, outputs and entity IDs are kept); satel-integra 1.6.0.
- "All partitions" alarm panel: arm / disarm all (or selected) partitions with one command.
- All four Satel arming modes on the alarm panels: away = 0 (full), custom bypass = 1
  (full + bypasses), home = 2 (no interior zones), night = 3 (no interior zones, no entry delay);
  option to keep the original behaviour.
- Zones: tamper, alarm, alarm memory, isolate, masked, no / long violation troubles; bypass switch.
- Partitions: violated zones, alarm memory and other flags; system status and troubles.
- Event log: event entity and `satel_integra_event` for every new panel event (with texts,
  partition, zone and user names).
- Actions: arm (modes, force, no bypass), disarm, clear alarm, bypass / unbypass zones,
  set outputs (on / off / toggle), clear trouble memory, read event log.
- Panel results are checked (wrong code, no access, cannot arm / force possible, no response).
- Lovelace card `custom:satel-integra-alarm-card` served by the integration.
- Library fixes: encrypted transport read the PDU partially when TCP split it; 16-byte zone /
  output masks for INT-RS v1.x / ETHM-1.
