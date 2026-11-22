# Brief

Hardware, working conditions and hard constraints are in `CLAUDE.md`. They apply
to every phase.

## Phase 1 — analyzer

Build this fully, with tests.

1. **Bundle format.** One directory or zip per board containing `mcconf.xml`,
   `appconf.xml`, `refloat.xml` and `meta.json` (hardware name, firmware, package
   version, motor, pack S/P and cell, BMS type), plus optional ride logs:
   Float Control `.csv.zip`, Floaty JSON, VESC Tool CSV.
2. **Parsers** for each file type. Parameter names and defaults come from
   upstream source at the pinned versions.
3. **Rule engine** with rules as data (YAML). Each rule has an id, severity,
   rationale and source URL. Seed it from `docs/knowledge-base.md`. Keep
   controller-specific limits in per-hardware profiles (Thor 301, Ubox Single
   100V 100A) and cell limits in per-cell profiles.
4. **Audit report**, Markdown, one per board:
   - red flags first
   - cross-checks: cell rating vs battery current; cutoffs vs LV/HV tiltback;
     duty tiltback vs max duty vs field weakening; IMU type and rate vs bus
     speed; flux linkage vs Refloat's torque normalisation
   - a diff against defaults
5. **Compare mode** for two bundles.

Resolve the "Known gaps" section of the knowledge base from primary sources
where you can, and record what you found and where.

## Phase 2 — capture feasibility

Research and a memo only. Write no capture code.

Read `vedderb/vesc_tool` and `lukash/refloat`, then write
`docs/capture-options.md` covering:

- What a package QML UI can do inside iOS VESC Tool: read mcconf, appconf and
  custom config; run terminal commands (`fwinfo`, `faults`); write files; open
  the share sheet; use the clipboard; make an HTTP POST. Cite file and line for
  each.
- Whether a QML-only change to Refloat's AppUI changes the config signature or
  anything else third-party apps (Floaty, Float Control) check.
- Whether the package system allows a second package beside Refloat.
- Options ranked. Each must work on both boards unless stated:
  1. a QML-only export button in a Refloat fork
  2. a standalone BLE client on this computer using the VESC packet protocol
  3. a Thor-only logger on the onboard VESC Express

Stop there and wait for a decision.

## Phase 3 — capture implementation

Not started. Scope depends on the Phase 2 decision.
