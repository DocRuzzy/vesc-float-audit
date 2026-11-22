# Firmware updates: what they do to stored settings

## What happened on 2026-11-22

Both boards were flashed from stock 7.00 to `lukash/bldc` v7.00-rflt-xtras-0.5
with VESC Tool's "Update firmware on the connected VESC", over the phone's
Bluetooth bridge. The upload completed on both. Afterwards:

| Stored data | Result |
|---|---|
| Motor config (mcconf) | **Reset to firmware defaults**: detected R/L/flux, hall table and limits gone |
| App config (appconf) | **Reset to firmware defaults**: IMU rotation, IMU offsets and sample rate (200 Hz) gone |
| Odometer / runtime | Reset |
| Refloat config | **Survived** (stored by the package, not in the firmware's config area) |

Neither board rode; the Thor 301 squealed with default motor parameters. Writing
the morning motor and app exports back fixed both.

Matching config signatures (`MCCONF_SIGNATURE`/`APPCONF_SIGNATURE`, identical in
stock 7.00 and rflt-xtras 0.5) only mean stored configs are *readable* by the new
firmware. They do not mean the configs survive the upload. bldc's own source says
stored data can be missing "as a result of programming" (`conf_general.c:113-115`),
and only odometer/runtime have a RAM fallback, which a power-on reset clears.

The analyzer now flags configs left at defaults: CFG-008 (motor detection values)
and CFG-009 (IMU orientation and calibration).

## Procedure for any firmware change

1. Save XML of motor, app **and** Refloat configs; run `hw_status`. Keep the files.
2. Make a VESC Tool *Backup Configuration* as well (stored on the computer/phone).
3. Flash with "Update firmware on the connected VESC", **never "All"** on a board
   with other CAN devices (Board A has a VESC Express on CAN).
4. After it reboots: Read motor and app configs. If they are at defaults, load the
   saved XMLs and press **Write** for each (Load XML alone changes nothing on the
   board). Power-cycle with the wheel still.
5. Read all three back, Save XML, run `hw_status`, and audit before the first
   bench test. Bench-test with the wheel off the ground before riding.
6. Change one thing at a time. Do not combine a firmware change with tune changes.
