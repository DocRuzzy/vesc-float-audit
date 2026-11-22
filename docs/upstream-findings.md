# Upstream findings

Phase 1 research, 2026-11-22. This file records what was resolved from primary
sources before the rules were written, where each fact came from, and where the
source contradicts `docs/knowledge-base.md`.

Line numbers refer to the pinned commits below.

## Pins

| Component | Repository | Ref | Commit | Note |
|---|---|---|---|---|
| Refloat | `lukash/refloat` | tag `v1.3.1` | `a2b55d96f508` (2026-11-06) | no `v1.3.1.1` tag exists, see gap 8 |
| VESC Tool 7.00 | `vedderb/vesc_tool` | branch `release_7_00` | `6528c4e2a963` (2026-07-01) | no 7.00 tag exists; branch head pinned |
| Firmware 7.00 | `vedderb/bldc` | branch `release_7_00` | `e877eaead23e` (2026-11-05) | no 7.00 tag exists; branch head pinned |
| rflt-xtras | `lukash/bldc` | tag `v7.00-rflt-xtras-0.5` | `ddf18711a6b9` (2026-09-28) | read only for the Thor 301 IMU bus |
| Package store | `vedderb/vesc_pkg` | `master` | `71922b1e4f50` (2026-11-19) | store copy of Refloat reports `1.3.1` |
| Log formats | `acheronfail/float-view` | `master` | `fae12e58cc3c` (2026-11-05) | third-party; no licence, so no fixtures copied |

The catalogs in `src/vfa/data/upstream/` are generated from these checkouts by
`tools/gen_catalog.py`, which refuses to run against any other commit.

**Not reachable from the build environment:** fungineers.us, spintend.com and
molicel.com. Every vendor figure in the profiles (Thor 301 ratings, Ubox
ratings, P45B datasheet) is therefore labelled UNVERIFIED and carries the
knowledge-base value. Rules that depend on them report "no finding
(unconfirmed inputs)" or "not evaluated", never a plain pass.

## Known gaps: status

| # | Gap | Status |
|---|---|---|
| 1 | Exact Refloat 1.3 defaults | **Resolved** |
| 2 | Firmware defaults for `foc_fw_current_max`, `l_temp_accel_dec` | **Resolved** |
| 3 | Ubox 100V 100A phase/abs limits, IMU, bus speed | **Resolved for firmware limits, IMU part and bus.** Vendor ratings unresolved |
| 4 | Pint motor R / L / λ and current max | **Unresolved.** No primary source |
| 5 | Board A detected R / L / λ | **Unresolved by nature.** Comes from the board's own `mcconf.xml` |
| 6 | Are the 1.3 on/off speed limits independent per direction? | **Resolved** |
| 7 | Units of the 1.3 smoothing time constants | **Resolved: seconds** |
| 8 | Is "1.3.1.1" a real tag? | **Resolved: no** |

### 1. Refloat 1.3 defaults

All 174 parameters, with defaults, ranges, units and enum names, are in
`src/vfa/data/upstream/refloat_1.3.1.json`, generated from
`src/conf/settings.xml`. The ones the rules use:

| Parameter | Default | Unit |
|---|---|---|
| `kp` (Angle P) | 20 | help text: 10–35 |
| `kp2` (Rate P) | 0.6 | |
| `ki` (Angle I) | 0.005 | help text: 0.005–0.08 |
| `ki_limit` | 30 | A, help text: 20–30, 0 disables |
| `mahony_kp` / `mahony_kp_roll` (Refloat's filter) | 2.0 / 1.4 | |
| `tiltback_duty` / `_angle` / `_speed` | 0.80 / 5 / 3 | – / ° / °/s |
| `tiltback_hv` / `tiltback_lv` | 4.3 / 3.0 | **V per cell** (see correction A) |
| `fault_adc1` / `fault_adc2` | 2.0 / 2.0 | V |
| `fault_delay_switch_full` / `_half` | 250 / 250 | ms |
| `atr.filter.time_constant` / `on_speed_` / `off_speed_` | 0.30 / 0.10 / 0.01 | s |
| `torque_tilt.filter.time_constant` / `on_speed_` / `off_speed_` | 0.20 / 0.08 / 0.16 | s |
| `atr.filter.on/off_speed_limit`, `torque_tilt.filter.on/off_speed_limit` | 24 / 24 | °/s |
| `turn_tilt.filter.time_constant`, `remote.filter.time_constant` | 0.2 / 0.2 | s |
| `atr.transition_boost` | 2.0 | × |
| `atr_amps_accel_ratio` / `atr_amps_decel_ratio` | 9 / 8 | |
| `torquetilt_start_current` / `torquetilt_strength` / `_regen` | 15 / 0.1 / 0.1 | A / °/A |
| `parking_brake_mode` | 1 (Idle) | |

The knowledge base's "new or renamed XML tags in 1.3" list is confirmed: all of
`atr.filter.{time_constant,on_speed_time_constant,off_speed_time_constant,on_speed_limit,off_speed_limit}`,
the same five under `torque_tilt.filter`, `turn_tilt.filter.time_constant`,
`remote.filter.time_constant` and `atr.transition_boost` exist in v1.3.1.

### 2. Firmware defaults

From `motor/mcconf_default.h` in bldc `release_7_00`:

- `l_temp_accel_dec` = **0.15** (`MCCONF_L_LIM_TEMP_ACCEL_DEC`, line 114). The knowledge base's UNVERIFIED 0.15 is correct.
- `foc_fw_current_max` = **0.0** (line 491). Field weakening is off by default.

Found in passing:

- `foc_fw_duty_start` defaults to 0.8 and `foc_fw_ramp_time` to 0 in the
  header, while the vesc_tool XML shows 0.9 / 0.2 s.
- `foc_short_ls_on_zero_duty` defaults to **false**.
- Mechanism of `l_temp_accel_dec`: `mc_interface.c:2390-2420` maps the
  acceleration current limit's temperature window towards 25 °C by this
  fraction, so 0.15 makes acceleration current start folding back at
  85 − 0.15 × 60 = 76 °C instead of 85 °C. Braking keeps the full window.

**The vesc_tool `res/config/7.00` XML defaults are not the firmware defaults.**
They differ for 28 mcconf parameters (e.g. flux linkage 4.014 mWb vs 2.45 mWb,
`l_abs_current_max` 150 vs 130 A); they look like a snapshot of one board.
The "diff against defaults" therefore uses the firmware headers plus each
board's hwconf overrides.

### 3. Spintend Single Ubox 100V 100A

From `hwconf/Ubox/100v/hw_ubox_100_core.h`, target `HW_UBOX_SINGLE_100`
(HW name `UBOX_SINGLE_100`):

| Item | Value | Line |
|---|---|---|
| Motor current setting limit (`HW_LIM_CURRENT`) | ±135 A | 278 |
| Battery current setting limit (`HW_LIM_CURRENT_IN`) | ±135 A | 279 |
| Absolute current setting limit (`HW_LIM_CURRENT_ABS`) | 0–180 A | 280 |
| Input voltage limit | 11–95 V | 288 |
| Max duty limit | 0.99 | 293 |
| FET temperature limit | 110 °C | 294 |
| Default `l_abs_current_max` | 160 A | 256 |
| Default `l_in_current_max` / `_min` | 84 / −65 A | 262 / 265 |
| Default `l_min_vin` / `l_max_vin` | 12 / 93 V | 244 / 247 |
| Default ZVF | 30 kHz | 253 |
| IMU | **BMI160** (`BMI160_SDA_GPIO`), `IMU_FLIP` | 216–220 |
| Bluetooth | permanent UART for an NRF52 module; no ESP32 found | 159 |

The IMU bus is bit-banged I²C at **400 kHz** (`imu/imu.c:265`), and the BMI160
I²C driver caps the sample rate at **1000 Hz** (`imu/bmi160_wrapper.c:36-40`). A
configured 1600 Hz silently runs at 1000 Hz.

These are firmware setting limits (what VESC Tool accepts), not vendor ratings.
The same core file also builds `UBOX_SINGLE_80` (±150 A, abs 210 A, 85 V) and
`UBOX_SINGLE_85_200` (±300 A, abs 420 A, 85 V). **Which target the owner's
unit runs is UNVERIFIED.** Confirm with `hw_status` (HW name) before relying on
the Ubox limits. The knowledge base's "BMI160 [UNVERIFIED]" is confirmed for
this target.

### 4. Pint motor reference values

No primary source has R, L, λ or a current rating for the original Onewheel
Pint motor. The `pint_stock` motor profile leaves them null, so ID-004/005/006
and CUR-007 report **not evaluated** on Board B. The pole count is assumed to be 30
and marked UNVERIFIED. Once the board's `mcconf.xml` is captured, the detected
values and `k` come straight from it.

### 5. Board A detected values

These need the board. The bundle's `mcconf.xml` carries them
(`foc_motor_r`, `foc_motor_l`, `foc_motor_ld_lq_diff`, `foc_motor_flux_linkage`),
and the report computes `k` from them. The `hypercore_mte5_n52` profile uses
the stock Hypercore R/L range [Comm] and a flux window of 26–32 mWb (the upper
bound is UNVERIFIED).

### 6. Independence of the 1.3 on/off speed limits

`filters/smooth_setpoint.c` supports four speed limits: on/off for "up" and
on/off for "down", where "up" means the setpoint moving with the direction of
travel (`is_up = (value >= 0) == forward`). But both ATR (`atr.c:60-70`) and
torque tilt (`torque_tilt.c:37-47`) pass `on_speed_limit, off_speed_limit,
on_speed_limit, off_speed_limit`.

So in 1.3.1 **on and off are independent of each other, but up and down share
them**. No config field sets them per direction. Both readings in the gap are
partly right: the filter can do it, the config cannot.

Turn tilt uses fixed 20 °/s limits and its time constant × 0.5 for on/off
(`turn_tilt.c:47-58`). Remote uses fixed 100 °/s and × 0.25 (`remote.c:46-58`).

### 7. Units of the smoothing time constants

The units are **seconds**. `ema_calculate_alpha_time_constant(tau, f)` converts τ to a
cutoff of 1/(2πτ) Hz against the update frequency in Hz (`filters/ema.c`).
`settings.xml` gives every `*.time_constant` the suffix ` s` and the range
0.01–0.5. The main smoother is a second-order EMA; its alpha is scaled by
2.146 to keep the stated time constant (`smooth_setpoint.c:56-58`).

### 8. "Refloat 1.3.1.1"

`git ls-remote --tags` on `lukash/refloat` lists 56 tags. The 1.3.1 line is
`v1.3.1-beta1..3` and `v1.3.1`, and there is **no `v1.3.1.1`**. The `version`
file at `v1.3.1` reads `1.3.1`, and so does the package-store copy in
`vedderb/vesc_pkg`, whose source matches the tag apart from icons and
`pkgdesc.qml`. The audit pins **v1.3.1**. A bundle reporting `1.3.1.1` gets
VER-003 (warning) and is audited against 1.3.1. The installed version should be
confirmed on the Packages page or in the Refloat AppUI.

## Corrections to the knowledge base

Each item below is a place where the pinned source says something different from,
or more precise than, `docs/knowledge-base.md`. The rules follow the source.

**A. LV/HV tiltback are per-cell values.** `motor_data.c:78-90`: a
`tiltback_lv`/`tiltback_hv` below 10 V is multiplied by `si_battery_cells`;
10 V or more is used as absolute volts. The defaults are 3.0 and 4.3 V/cell, and
the help text recommends per-cell values on firmware ≥ 6.05. Consequences:

- The board tables' "LV tiltback 60 V / 45 V" are correct as pack voltages.
  Enter them as 3.0 V/cell (or as 60 V / 45 V absolute).
- **Refloat's default HV of 4.3 V/cell is 86 V on Board A's 20S pack, above the
  Thor 301's 84 V maximum operating voltage** (vendor figure, UNVERIFIED).
  BAT-012 flags this.
- A wrong `si_battery_cells` moves both pushbacks silently. With the firmware
  default of 3 cells, LV pushback lands at 9 V (ID-002, BAT-010).
- "HV/LV at 200 V / 0 V" is still an effectively-off setting: 200 V is
  absolute, and 0 V is per-cell zero.

**B. Torque normalisation factor.** The UI's conversion ratio is
`k = poles × λ / (30 × 0.027)` (`ui.qml.in:1449-1458`), not `λ / 27`. The two agree
only at 30 poles. "`si_motor_poles` must be 30" is better read as "must be the
real pole count": Refloat uses it in the ratio (`motor_data.c:106`). 30 is
the expected value for FM hub motors [Comm].

**C. Conversion lists.** Multiplied by k: `kp, kp2, ki, ki_limit,
booster_current, brkbooster_current, torquetilt_start_current,
atr_amps_accel_ratio, atr_amps_decel_ratio`. Divided by k:
`torquetilt_strength, torquetilt_strength_regen` (`ui.qml.in:1436-1444`). The
knowledge base omits the braking booster and lists the ATR ratio once.

**D. Direction at runtime.** `pid.c:61-69` turns gains into torque with
`TORQUE_CONSTANT_COMPAT = 1.5 × 15 × 0.027`. `motor_data.c:194` turns torque
into current with `1 / (1.5 × pole_pairs × λ)`. A configured gain therefore
commands **1/k** phase amps per "reference amp". On Board A's higher-λ motor
the same numbers give *less* current than on 1.2, which is why the conversion
multiplies by k. The conversion does not record that it ran, so a twice-converted
tune cannot be detected from the config. `meta.json` records
`tune_conversions_from_1_2`, and VER-006/007 use it.

**E. Mahony reset.** Refloat 1.3.1 resets App Config Mahony KP only when it is
**> 1**, setting KP 0.2, KI 0 and accel confidence decay 0.1
(`main.c:205-214`). A KP between 0.2 and 1 is left alone (IMU-007).

**F. Thor 301 IMU bus.** On stock 7.00 the Thor 301 hwconf defines the
LSM6DS3 SPI pins but not `LSM6DS3_USE_SPI`, so `imu.c:173-180` drives the chip
as **bit-banged I²C on the SPI pins at 400 kHz**. The 700 kHz rate is a
compile-time flag (`LSM6DS3_SPEED_700KHZ`) that this target does not set. On
rflt-xtras 0.5 the Thor 301 uses **hardware SPI** instead
(`hw_Thor301_core.h:176-188` in `lukash/bldc`). So the knowledge base's I²C
bus/rate matrix applies to stock 7.00 and not to rflt-xtras 0.5. **The claim
"the 700 kHz bus is selected by setting Use magnetometer to false" was not
found in either tree.** It is UNVERIFIED and may describe an earlier rflt-xtras
release.

**G. LSM6DS3 rate handling (stock).** The sampling thread runs at the
configured rate (`lsm6ds3.c:379`) with no cap. The gyro ODR rounds up to the
next of 416 / 833 / 1660 Hz (`lsm6ds3.c:139-156`).

**H. Setup wizard cutoffs.** `Utility::setBatteryCutCanFromCurrentConfig`
(`utility.cpp:825-862`) writes **3.4 / 3.0 V per cell** in "cautious" mode and
2.7 / 2.5 V per cell otherwise. The mobile wizard uses cautious mode for
Generic, E-Skate and Propeller and non-cautious only for **Balance**
(`SetupWizardFoc.qml:121-132`). The desktop detect-all dialog always uses
cautious mode (`detectallfocdialog.cpp:306`). The E-Skate preset also sets
`l_duty_start = 0.85`, which limits current above 85% duty (CUR-009). The
firmware's own defaults are 10 / 8 V, which is effectively off for these packs.

**I. Footpad thresholds.** `footpad_sensor.c:33-46`: a threshold of 0 marks
that sensor as always on. With one at 0 the board uses single-sensor mode. With
**both** at 0 the state is permanently "both pressed", so a footpad fault never
disengages the board (FP-001).

**J. Duty margin.** Refloat computes `l_max_duty − 0.05` (`motor_data.c:100`)
but uses it only in the wheelslip / traction-control path (`main.c:502, 652`),
not as a pushback. Duty pushback is `tiltback_duty` alone (`main.c:510`).
Refloat's temperature alerts start 3 °C below `l_temp_fet_start` /
`l_temp_motor_start` (`motor_data.c:98-99`).

## What remains open

- Vendor ratings for both controllers and the P45B datasheet values. Reading
  them needs network access to the vendor sites, or the owner pasting the pages.
- Which Ubox firmware target is installed (`hw_status`).
- Pint motor detection values (from Board B's `mcconf.xml`).
- Measured Control Loop Frequency on both boards.
- Float Control and Floaty log field names and units: these come only from a third-party parser.
- Firmware 6.06 "Calibration Modes" re-enabling after restore (knowledge base §1
  item 5). Not yet traced in source, so there is no rule for it.
