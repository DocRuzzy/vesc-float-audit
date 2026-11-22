# vesc-float-audit

Capture and audit tooling for VESC self-balancing ("onewheel"-style) boards.
The task description is in `docs/brief.md`. The tuning reference that seeds the
rule engine is in `docs/knowledge-base.md`.

## Hardware

All boards run VESC firmware 7.00 and Refloat 1.3.1.x. The owner reports the
package as "1.3.1.1": check the tags on `lukash/refloat`, pin to the one that
exists, and say so if 1.3.1.1 is not a real release.

- **Board A:** Fungineers Thor 301, 5" hub motor with N52 magnets (make and
  model not yet confirmed), 20S2P Molicel P45B, charge-only BMS (no CAN
  BMS data), 10k NTC on ADC3, footpads on ADC1/ADC2.
- **Board B:** Spintend Single Ubox 100V 100A, original Onewheel Pint hub motor,
  15S1P Molicel P45B, original BMS modified to charge-only (no BMS data).

## Working conditions

- You run on the owner's computer but cannot reach the boards.
- The only reliable link to the boards is iOS VESC Tool over BLE.
- Every on-device test is run by hand by the owner. Minimise test cycles: read
  the upstream source before proposing anything that needs a board.

## Hard constraints

- Do not modify Refloat's C code, control loop or `settings.xml`.
- Capture is read-only. Never write a configuration to a controller.
- Any export must refuse to run unless the board is disengaged and stationary.
- Take parameter names and defaults from upstream source at the pinned versions
  (`vedderb/vesc_tool` `res/config` for 7.00, `lukash/refloat`
  `src/conf/settings.xml`). Do not guess names.
- Mark anything you could not confirm from source as UNVERIFIED. The knowledge
  base uses the same label; treat its UNVERIFIED and [Comm] entries as
  heuristics to check, not facts.
- These boards carry a rider. A wrong "this setting is fine" is worse than a
  missing rule: when evidence is thin, report it as a warning with the
  uncertainty stated.
