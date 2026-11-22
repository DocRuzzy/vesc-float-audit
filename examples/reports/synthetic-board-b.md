# Configuration audit — Example B (synthetic)

Generated 2026-11-22 by vesc-float-audit from `examples/synthetic-board-b`.

> This report is generated from exported configuration files and the rule set in `src/vfa/data/rules/`. It does not certify any setting as safe. A rule that did not fire only means that rule's condition did not hold; rules whose inputs are missing or unconfirmed are listed separately, never as passes. Nothing here has been validated on a board.

| | |
|---|---|
| Hardware | Spintend Single Ubox 100V 100A (`ubox_single_100`) |
| Firmware | 7.00 (stock) |
| Package | Refloat 1.3.1 |
| Motor | Onewheel Pint hub (original) (profile `pint_stock`) |
| Pack | 15S1P Molicel INR-21700-P45B |
| BMS | charge-only |

## Summary

- **0 red flag(s)** (critical findings)
- 6 warning(s), 4 info note(s)
- 10 rule(s) not evaluated (missing inputs)
- 22 rule(s) without a finding but resting on unconfirmed inputs
- 55 rule(s) without a finding on confirmed inputs
- 13 rule(s) not applicable

## Red flags

No critical rule fired. Check the *not evaluated* and *unconfirmed* lists before reading this as reassurance.

## Cross-checks

### Cell rating vs battery current

| Quantity | Value | Key | Evidence |
|---|---|---|---|
| Pack | 15 S | `pack.s` | owner-reported |
| Parallel groups | 1 P | `pack.p` | owner-reported |
| Cell continuous discharge | 45 A | `cell.continuous_discharge_a` | UNVERIFIED |
| Pack continuous rating | 45 A | `pack.continuous_a` | derived (rests on UNVERIFIED) |
| Durable figure | 36 A | `pack.durable_a` | derived (rests on Analysis, UNVERIFIED) |
| Battery Current Max | 38 A | `mc.l_in_current_max` | config |
| Cell max charge | 13.5 A | `cell.charge_max_a` | UNVERIFIED |
| Pack rated charge | 13.5 A | `pack.charge_max_a` | derived (rests on UNVERIFIED) |
| Regen pulse allowance | 24.98 A | `pack.regen_pulse_a` | derived (rests on Analysis, UNVERIFIED) |
| Battery Current Max Regen | -22 A | `mc.l_in_current_min` | config |

| Rule | Severity | Outcome | Detail |
|---|---|---|---|
| BAT-001 Battery current max above the pack's continuous rating | critical | no finding (unconfirmed inputs) | unconfirmed: `cell.continuous_discharge_a` |
| BAT-002 Battery current max above the durable figure for this pack | warning | FIRED | Battery Current Max 38 A is above 36 A (80% of the 45 A continuous rating). |
| BAT-003 Regen limit above the pack's pulse allowance | warning | no finding (unconfirmed inputs) | unconfirmed: `cell.charge_max_a`, `cell.regen_pulse_factor` |
| LOG-004 Battery current saturating at its limit | warning | FIRED | Battery current was within 3% of Battery Current Max 38 A in 20.0% of running samples. |
| BAT-004 Regen limit above the cells' rated max charge current | info | FIRED | Regen -22 A is above the rated 13.5 A charge current; acceptable only as short pulses. |

### Voltage cutoffs vs LV/HV tiltback

| Quantity | Value | Key | Evidence |
|---|---|---|---|
| Full charge | 63 V | `pack.full_v` | derived (rests on UNVERIFIED) |
| Empty (cell min) | 37.5 V | `pack.empty_v` | derived (rests on UNVERIFIED) |
| si_battery_cells | 15 | `mc.si_battery_cells` | config |
| Cutoff start | 40.5 V | `mc.l_battery_cut_start` | config |
| Cutoff start per cell | 2.7 V | `thr.l_battery_cut_start_per_cell` | derived |
| Cutoff end | 37.5 V | `mc.l_battery_cut_end` | config |
| Cutoff end per cell | 2.5 V | `thr.l_battery_cut_end_per_cell` | derived |
| tiltback_lv (raw) | 3 V | `rf.tiltback_lv` | config |
| LV is per-cell | yes | `thr.lv_is_per_cell` | Source |
| LV pushback effective | 45 V | `thr.lv_v` | Source |
| LV per cell | 3 V | `thr.lv_v_per_cell` | derived |
| tiltback_hv (raw) | 4.2 V | `rf.tiltback_hv` | config |
| HV is per-cell | yes | `thr.hv_is_per_cell` | Source |
| HV pushback effective | 63 V | `thr.hv_v` | Source |
| Undervoltage fault (l_min_vin) | 12 V | `mc.l_min_vin` | config |
| Overvoltage fault (l_max_vin) | 93 V | `mc.l_max_vin` | config |
| Controller max operating | — | `hw.vendor.max_operating_v` | UNVERIFIED |
| Firmware Vin limit | 95 V | `hw.fw_limits.vin_max` | Source |

| Rule | Severity | Outcome | Detail |
|---|---|---|---|
| BAT-005 Voltage cutoff end below the cell minimum | critical | no finding (unconfirmed inputs) | unconfirmed: `cell.v_min` |
| BAT-006 Voltage cutoffs left at the setup wizard's cautious values | critical | no finding |  |
| BAT-008 Cutoff start is not above cutoff end | critical | no finding |  |
| BAT-009 LV pushback at or below the cutoff start | critical | no finding |  |
| BAT-010 LV pushback effectively disabled | critical | no finding (unconfirmed inputs) | unconfirmed: `cell.v_min` |
| BAT-012 HV pushback above the controller's maximum operating voltage | critical | NOT EVALUATED | missing: `hw.vendor.max_operating_v` |
| BAT-013 HV pushback at or above the firmware overvoltage fault | critical | no finding |  |
| BAT-015 HV pushback effectively disabled | critical | no finding |  |
| BAT-016 Undervoltage fault above the cutoff range | critical | no finding |  |
| ID-002 Battery cell count in mcconf differs from the pack | critical | no finding |  |
| LOG-006 Logged voltage near the overvoltage fault | critical | no finding (unconfirmed inputs) | unconfirmed: `log.v_max` |
| BAT-007 Cutoff start high enough to fold back current under sag | warning | no finding |  |
| BAT-011 LV pushback below 3.0 V/cell with a charge-only BMS | warning | no finding (unconfirmed inputs) | unconfirmed: `cell.v_min` |
| BAT-014 HV pushback below full-charge voltage | warning | no finding (unconfirmed inputs) | unconfirmed: `cell.v_max` |
| BAT-017 Cutoff end below the controller's recommended minimum voltage | warning | NOT EVALUATED | missing: `hw.vendor.min_recommended_v` |
| BAT-019 Overvoltage fault raised above the hardware default | warning | no finding (unconfirmed inputs) | unconfirmed: `hw.default_overrides.l_max_vin` |
| BAT-020 Full charge at the controller's maximum operating voltage | warning | NOT EVALUATED | missing: `hw.vendor.max_operating_v` |
| LOG-005 Logged voltage reached the cutoff start | warning | no finding (unconfirmed inputs) | unconfirmed: `log.v_min` |
| LOG-007 Logged voltage above HV pushback | warning | no finding (unconfirmed inputs) | unconfirmed: `log.v_max` |

### Duty tiltback vs max duty vs field weakening

| Quantity | Value | Key | Evidence |
|---|---|---|---|
| Max duty | 0.95 | `mc.l_max_duty` | config |
| Max duty − 0.05 | 0.9 | `duty.margin_point` | Analysis |
| Duty pushback threshold | 0.78 | `rf.tiltback_duty` | config |
| Duty current limit start | 1 | `mc.l_duty_start` | config |
| FW current max | 0 A | `mc.foc_fw_current_max` | config |
| FW duty start | 0.8 | `mc.foc_fw_duty_start` | config |
| FW / motor max | 0 | `fw.fraction_of_motor_max` | derived |
| Worst-case sag at battery max | 8.55 V | `duty.sag_v` | derived (rests on UNVERIFIED) |
| Sag / full charge | 0.1357 | `duty.sag_fraction` | derived (rests on UNVERIFIED) |

| Rule | Severity | Outcome | Detail |
|---|---|---|---|
| CUR-009 Duty-cycle current limit start below 100% | critical | no finding |  |
| DUTY-002 Duty pushback threshold within 5% of max duty | critical | no finding (unconfirmed inputs) | unconfirmed: `duty.margin_point` |
| DUTY-004 Field weakening above 50 A with duty pushback at 85% or higher | critical | no finding |  |
| DUTY-011 Duty pushback has no effect | critical | no finding |  |
| LOG-002 Logged duty within 5% of max duty | critical | no finding (unconfirmed inputs) | unconfirmed: `duty.margin_point`, `log.duty_max` |
| DUTY-001 Max duty differs from the firmware default 95% | warning | no finding |  |
| DUTY-003 Duty pushback above 85% | warning | no finding (unconfirmed inputs) | unconfirmed: `duty.margin_point` |
| DUTY-010 High-sag pack with duty pushback above 80% | warning | no finding (unconfirmed inputs) | unconfirmed: `cell.dcr_ohm_max`, `cell.v_max` |
| LOG-001 Logged duty above the duty pushback threshold | warning | FIRED | Logged duty reached 83%, above the 78% pushback threshold. |
| DUTY-009 Field weakening values need re-validation on 7.00 | info | no finding |  |

### IMU type and rate vs bus speed

| Quantity | Value | Key | Evidence |
|---|---|---|---|
| IMU part | BMI160 | `imu.part` | Source |
| Firmware variant | stock | `imu.variant` | owner-reported |
| Bus | i2c_bitbang | `imu.bus_kind` | Source |
| Bus speed | 400 kHz | `imu.bus_khz` | Source |
| Configured sample rate | 832 Hz | `app.imu_conf.sample_rate_hz` | config |
| Firmware rate cap | 1000 Hz | `imu.bus_max_rate_hz` | Source |
| Effective loop rate | 832 Hz | `imu.effective_rate_hz` | Source |
| Measured control loop | — | `meta.measured.control_loop_hz` | owner-reported |
| Zero vector frequency | 25000.0 Hz | `mc.foc_f_zv` | config |
| App Mahony KP | 0.2 | `app.imu_conf.mahony_kp` | config |
| App Mahony KI | 0 | `app.imu_conf.mahony_ki` | config |
| Accel/gyro filter | 0 | `app.imu_conf.filter` | config |

| Rule | Severity | Outcome | Detail |
|---|---|---|---|
| ID-009 IMU is not the internal IMU | warning | no finding |  |
| IMU-003 Configured IMU rate above the firmware's cap for this IMU | warning | no finding |  |
| IMU-004 IMU rate below 400 Hz | warning | no finding |  |
| IMU-008 Switching frequency outside 25-30 kHz | warning | no finding |  |
| IMU-009 High switching frequency combined with a high IMU rate | warning | no finding |  |
| IMU-013 IMU bus for this firmware variant is not characterised | warning | no finding |  |
| IMU-005 IMU rate is not one of the long-proven settings | info | no finding |  |
| IMU-011 Control-loop frequency not measured | info | FIRED | No measured control-loop frequency in meta.json. Read "Control Loop Frequency" from Refloat's realtime data and record it as measured.control_loop_hz. |

### Flux linkage vs Refloat torque normalisation

| Quantity | Value | Key | Evidence |
|---|---|---|---|
| Motor poles | 30 | `mc.si_motor_poles` | config |
| Flux linkage | 0.024 Wb | `mc.foc_motor_flux_linkage` | config |
| k = poles·λ / (30 · 0.027) | 0.8889 | `torque.k` | Source |
| Phase amps per configured amp (1/k) | 1.125 | `torque.amps_per_ref_amp` | Source |
| Times converted from 1.2 | — | `meta.tune_conversions_from_1_2` | owner-reported |

Torque-scaled Refloat parameters. *1.2-equivalent* is the value a 1.2 tune would have needed for the same phase current (value ÷ k, or × k for strengths); if this tune was converted exactly once, that column is the original 1.2 tune.

| Parameter | Value | Default | 1.2-equivalent |
|---|---|---|---|
| `kp` | 20 | 20 | 22.5 |
| `kp2` | 0.6 | 0.6 | 0.675 |
| `ki` | 0.005 | 0.005 | 0.005625 |
| `ki_limit` | 30 | 30 | 33.75 |
| `booster_current` | 0 | 0 | 0 |
| `brkbooster_current` | 0 | 0 | 0 |
| `torquetilt_start_current` | 15 | 15 | 16.88 |
| `atr_amps_accel_ratio` | 9 | 9 | 10.12 |
| `atr_amps_decel_ratio` | 8 | 8 | 9 |
| `torquetilt_strength` | 0.1 | 0.1 | 0.08889 |
| `torquetilt_strength_regen` | 0.1 | 0.1 | 0.08889 |

| Rule | Severity | Outcome | Detail |
|---|---|---|---|
| ID-001 Motor pole count differs from the motor profile | critical | no finding (unconfirmed inputs) | unconfirmed: `motor.poles` |
| ID-003 Flux linkage is zero or missing; Refloat skips torque normalisation | critical | no finding |  |
| ID-004 Flux linkage outside the motor profile's range | warning | NOT EVALUATED | missing: `motor.flux_wb_max`, `motor.flux_wb_min` |
| VER-007 Tune conversion history unknown on a motor where it matters | warning | FIRED | k = 0.889 on this motor, and meta.json does not record whether this tune was converted from 1.2. If it was made on 1.2 and never converted, torque-scaled gains act 1.12x as strong (in phase amps) as on 1.2. If it was converted twice, they are k^2 off. |
| TUNE-001 Torque normalisation factor away from 1 | info | FIRED | k = 0.889 (30 poles, flux 0.02400 Wb). At runtime each configured "amp" of kp/kp2/ki/ki_limit/booster/torque-tilt start/ATR ratio commands 1.125 phase amps on this motor (the same torque as 1 A on the reference motor). A tune copied from a board with a different k feels 1.12x as strong in current. |

## Other findings

### Warnings (6)

#### BAT-002 — Battery current max above the durable figure for this pack
*warning* · rule basis **[Analysis]** · category battery

Battery Current Max 38 A is above 36 A (80% of the 45 A continuous rating).

Why: The knowledge base treats about 75-83% of the continuous rating as durable; the rest is a short-peak allowance.

Rests on unconfirmed inputs: `cell.continuous_discharge_a` [UNVERIFIED], `cell.durable_derate` [Analysis].

Sources: `docs/knowledge-base.md §2`

#### LOG-001 — Logged duty above the duty pushback threshold
*warning* · rule basis **[Analysis]** · category log

Logged duty reached 83%, above the 78% pushback threshold.

Why: The rider rode through pushback, or pushback is too slow to hold them back.

Rests on unconfirmed inputs: `log.duty_max` [UNVERIFIED].

Sources: `docs/knowledge-base.md §7.9`

#### LOG-004 — Battery current saturating at its limit
*warning* · rule basis **[Analysis]** · category log

Battery current was within 3% of Battery Current Max 38 A in 20.0% of running samples.

Why: Battery current max binds at high duty.

Rests on unconfirmed inputs: `log.frac_batt_at_limit` [UNVERIFIED].

Sources: `docs/knowledge-base.md §2`

#### LOG-010 — Footpad readings below threshold while riding
*warning* · rule basis **[Analysis]** · category log

1 running samples had a footpad ADC below its threshold (ADC1 2 V, ADC2 2 V). Check for dropouts or a marginal threshold.

Why: Random disengages trace back to ADC thresholds against real voltages.

Rests on unconfirmed inputs: `log.footpad_low_while_running` [UNVERIFIED].

Sources: `docs/knowledge-base.md §8`

#### THM-006 — Battery temperature unmonitored
*warning* · rule basis **[Analysis]** · category thermal

Nothing on file reads battery temperature (meta.battery_temp_monitored is not true). With a charge-only BMS a hot pack is not detected.

Why: Neither stock firmware nor stock Refloat reads an ADC3 thermistor as battery temperature; Refloat's BMS temperature checks only work with BMS integration (bms.enabled), which needs a CAN BMS.

Sources: `docs/knowledge-base.md §2`; [src/conf/settings.xml](https://github.com/lukash/refloat/blob/a2b55d96f508653b0436b21410100aaf91f14b04/src/conf/settings.xml)

#### VER-007 — Tune conversion history unknown on a motor where it matters
*warning* · rule basis **[Analysis]** · category versions

k = 0.889 on this motor, and meta.json does not record whether this tune was converted from 1.2. If it was made on 1.2 and never converted, torque-scaled gains act 1.12x as strong (in phase amps) as on 1.2. If it was converted twice, they are k^2 off.

Why: The config itself cannot show whether a conversion happened. Ask the owner and record tune_conversions_from_1_2 in meta.json.

Sources: [ui.qml.in#L1430-L1458](https://github.com/lukash/refloat/blob/a2b55d96f508653b0436b21410100aaf91f14b04/ui.qml.in#L1430-L1458); [src/pid.c#L61-L69](https://github.com/lukash/refloat/blob/a2b55d96f508653b0436b21410100aaf91f14b04/src/pid.c#L61-L69)

### Infos (4)

#### BAT-004 — Regen limit above the cells' rated max charge current
*info* · rule basis **[Analysis]** · category battery

Regen -22 A is above the rated 13.5 A charge current; acceptable only as short pulses.

Why: Short regen pulses above the rated charge current are usually tolerated; sustained descents are not.

Rests on unconfirmed inputs: `cell.charge_max_a` [UNVERIFIED], `cell.regen_pulse_factor` [Analysis].

Sources: `docs/knowledge-base.md §2`

#### CUR-012 — Phases not shorted at zero duty
*info* · rule basis **[Comm]** · category current

Short Low-Side FETs on Zero Duty is off (firmware default). The community setting is on; Refloat's own parking brake is 1 (0 Always, 1 Idle, 2 Never).

Why: Holds the board at standstill.

Sources: `docs/knowledge-base.md §3`

#### IMU-011 — Control-loop frequency not measured
*info* · rule basis **[Source]** · category imu

No measured control-loop frequency in meta.json. Read "Control Loop Frequency" from Refloat's realtime data and record it as measured.control_loop_hz.

Why: The rate rules check configuration only; whether the loop achieves it is visible only on the board.

Sources: `docs/knowledge-base.md §1 item 3`

#### TUNE-001 — Torque normalisation factor away from 1
*info* · rule basis **[Source]** · category tune

k = 0.889 (30 poles, flux 0.02400 Wb). At runtime each configured "amp" of kp/kp2/ki/ki_limit/booster/torque-tilt start/ATR ratio commands 1.125 phase amps on this motor (the same torque as 1 A on the reference motor). A tune copied from a board with a different k feels 1.12x as strong in current.

Why: pid.c multiplies gains by TORQUE_CONSTANT_COMPAT (1.5 x 15 x 0.027) to get torque; motor_data.c converts torque to current with 1 / (1.5 x pole_pairs x flux). The ratio is 1/k. The 1.2 -> 1.3 conversion multiplies those gains by k to keep the old current.

Sources: [src/lib/utils.h#L37-L38](https://github.com/lukash/refloat/blob/a2b55d96f508653b0436b21410100aaf91f14b04/src/lib/utils.h#L37-L38); [src/pid.c#L61-L69](https://github.com/lukash/refloat/blob/a2b55d96f508653b0436b21410100aaf91f14b04/src/pid.c#L61-L69); [src/motor_data.c#L102-L109](https://github.com/lukash/refloat/blob/a2b55d96f508653b0436b21410100aaf91f14b04/src/motor_data.c#L102-L109); [src/motor_data.c#L190-L195](https://github.com/lukash/refloat/blob/a2b55d96f508653b0436b21410100aaf91f14b04/src/motor_data.c#L190-L195); [ui.qml.in#L1430-L1458](https://github.com/lukash/refloat/blob/a2b55d96f508653b0436b21410100aaf91f14b04/ui.qml.in#L1430-L1458)

## Not evaluated

These rules could not run because an input is missing (no vendor figure, no reference value for this motor, no log, or a parameter absent from the export). Each is an open question, not a pass.

| Rule | Severity | Missing |
|---|---|---|
| BAT-012 HV pushback above the controller's maximum operating voltage | critical | `hw.vendor.max_operating_v` |
| CUR-003 Absolute max current above the controller's recommended limit | critical | `hw.vendor.phase_current_recommended` |
| BAT-017 Cutoff end below the controller's recommended minimum voltage | warning | `hw.vendor.min_recommended_v` |
| BAT-020 Full charge at the controller's maximum operating voltage | warning | `hw.vendor.max_operating_v` |
| ID-004 Flux linkage outside the motor profile's range | warning | `motor.flux_wb_max`, `motor.flux_wb_min` |
| ID-005 Motor resistance outside the motor profile's range | warning | `motor.r_ohm_max`, `motor.r_ohm_min` |
| ID-006 Motor inductance outside the motor profile's range | warning | `motor.l_h_max`, `motor.l_h_min` |
| ID-007 Motor inductance below the controller's minimum | warning | `hw.vendor.min_inductance_h` |
| ID-010 Switching frequency outside the controller's stated PWM range | warning | `hw.vendor.pwm_max_hz`, `hw.vendor.pwm_min_hz` |
| CUR-007 Motor current max well above where the stator saturates | info | `motor.saturation_current` |

## No finding, but unconfirmed

These rules did not fire, but at least one input is UNVERIFIED or a community/analysis figure. Confirm the inputs before relying on them.

| Rule | Severity | Unconfirmed inputs |
|---|---|---|
| BAT-001 Battery current max above the pack's continuous rating | critical | `cell.continuous_discharge_a` [UNVERIFIED] |
| BAT-005 Voltage cutoff end below the cell minimum | critical | `cell.v_min` [UNVERIFIED] |
| BAT-010 LV pushback effectively disabled | critical | `cell.v_min` [UNVERIFIED] |
| CUR-010 Wattage limit below battery voltage x battery current | critical | `cell.v_max` [UNVERIFIED] |
| CUR-011 ERPM limit within reach | critical | `cell.v_max` [UNVERIFIED], `erpm.no_load_max` [Analysis] |
| DUTY-002 Duty pushback threshold within 5% of max duty | critical | `duty.margin_point` [Analysis] |
| ID-001 Motor pole count differs from the motor profile | critical | `motor.poles` [UNVERIFIED] |
| LOG-002 Logged duty within 5% of max duty | critical | `duty.margin_point` [Analysis], `log.duty_max` [UNVERIFIED] |
| LOG-006 Logged voltage near the overvoltage fault | critical | `log.v_max` [UNVERIFIED] |
| BAT-003 Regen limit above the pack's pulse allowance | warning | `cell.charge_max_a` [UNVERIFIED], `cell.regen_pulse_factor` [Analysis] |
| BAT-011 LV pushback below 3.0 V/cell with a charge-only BMS | warning | `cell.v_min` [UNVERIFIED] |
| BAT-014 HV pushback below full-charge voltage | warning | `cell.v_max` [UNVERIFIED] |
| BAT-018 Regen is cut at high battery voltage | warning | `cell.v_max` [UNVERIFIED] |
| BAT-019 Overvoltage fault raised above the hardware default | warning | `hw.default_overrides.l_max_vin` [UNVERIFIED] |
| CUR-005 Absolute max current above the firmware default for this controller | warning | `hw.default_overrides.l_abs_current_max` [UNVERIFIED], `hw.vendor.phase_current_recommended` [UNVERIFIED] |
| DUTY-003 Duty pushback above 85% | warning | `duty.margin_point` [Analysis] |
| DUTY-010 High-sag pack with duty pushback above 80% | warning | `cell.dcr_ohm_max` [UNVERIFIED], `cell.v_max` [UNVERIFIED] |
| LOG-003 Motor current saturating at its limit | warning | `log.frac_motor_at_limit` [UNVERIFIED] |
| LOG-005 Logged voltage reached the cutoff start | warning | `log.v_min` [UNVERIFIED] |
| LOG-007 Logged voltage above HV pushback | warning | `log.v_max` [UNVERIFIED] |
| LOG-008 Fault codes in the log | warning | `log.fault_count` [UNVERIFIED] |
| LOG-009 MOSFET temperature reached Refloat's temperature pushback | warning | `log.temp_mos_max` [UNVERIFIED] |

## No finding on confirmed inputs

BAT-006, BAT-008, BAT-009, BAT-013, BAT-015, BAT-016, CUR-001, CUR-004, CUR-008, CUR-009, DUTY-004, DUTY-011, FP-001, FP-004, ID-002, ID-003, ID-008, THM-001, THM-002, THM-003, TUNE-008, VER-001, BAT-007, CFG-001, CFG-002, CFG-003, CFG-004, CUR-002, CUR-006, DUTY-001, FP-002, FP-003, ID-009, IMU-003, IMU-004, IMU-007, IMU-008, IMU-009, IMU-013, THM-004, TUNE-002, TUNE-003, TUNE-004, TUNE-006, VER-003, VER-004, VER-005, DUTY-009, IMU-005, IMU-006, TUNE-005, TUNE-007, TUNE-009, TUNE-010, VER-008

## Diff against defaults

Defaults are what a freshly flashed controller holds: `motor/mcconf_default.h` and `applications/appconf_default.h` from bldc `release_7_00`, overlaid with this hardware's hwconf overrides, and `src/conf/settings.xml` from Refloat v1.3.1. The vesc_tool `res/config` XML defaults are a snapshot from one board and are only used where the header value is not numeric (enums).

### Motor config (11 changed)

| Parameter | Name | Value | Default | Default from |
|---|---|---|---|---|
| `foc_f_zv` | Zero Vector Frequency | 25 kHz | 30 kHz | ubox_single_100 hwconf |
| `l_battery_cut_end` | Battery Voltage Cutoff End | 37.5 V | 8 V | firmware header |
| `l_battery_cut_start` | Battery Voltage Cutoff Start | 40.5 V | 10 V | firmware header |
| `l_current_max` | Motor Current Max | 110 A | 60 A | firmware header |
| `l_current_min` | Motor Current Max Brake | -110 A | -60 A | firmware header |
| `l_in_current_max` | Battery Current Max | 38 A | 84 A | ubox_single_100 hwconf |
| `l_in_current_min` | Battery Current Max Regen | -22 A | -65 A | ubox_single_100 hwconf |
| `l_temp_accel_dec` | Acceleration Temperature Decrease | 0 % | 15 % | firmware header |
| `si_battery_ah` | Battery Capacity | 4.5 Ah | 6 Ah | firmware header |
| `si_battery_cells` | Battery Cells Series | 15 | 3 | firmware header |
| `si_motor_poles` | Motor Poles | 30 | 14 | firmware header |

<details><summary>3 detection / calibration values (expected to differ)</summary>

| Parameter | Value | Default |
|---|---|---|
| `foc_motor_flux_linkage` | 24 mWb | 2.45 mWb |
| `foc_motor_l` | 250 µH | 7 µH |
| `foc_motor_r` | 140 mΩ | 15 mΩ |

</details>

### App config (3 changed)

| Parameter | Name | Value | Default | Default from |
|---|---|---|---|---|
| `app_to_use` | APP to Use | No App (0) | UART (3) | firmware header |
| `imu_conf.mahony_kp` | Mahony KP | 0.2 | 0.3 | firmware header |
| `imu_conf.sample_rate_hz` | Sample Rate | 832 Hz | 200 Hz | firmware header |

### Refloat config (5 changed)

| Parameter | Name | Value | Default | Default from |
|---|---|---|---|---|
| `fault_delay_switch_full` | Full Switch Fault Delay | 300 ms | 250 ms | settings.xml |
| `fault_delay_switch_half` | Half Switch Fault Delay | 500 ms | 250 ms | settings.xml |
| `meta.is_default` | Config is Default | false | true | settings.xml |
| `tiltback_duty` | Duty Cycle Threshold | 0.78 | 0.8 | settings.xml |
| `tiltback_hv` | High Voltage Threshold | 4.2 V | 4.3 V | settings.xml |

## Ride logs

- `logs/ride.csv`: float_control, 5 samples, format evidence [UNVERIFIED]

| Metric | Value |
|---|---|
| `log.duty_max` | 0.83 |
| `log.fault_codes` | none |
| `log.fault_count` | 0 |
| `log.footpad_low_while_running` | 1 |
| `log.frac_batt_at_limit` | 0.2 |
| `log.frac_motor_at_limit` | 0 |
| `log.i_batt_max` | 37.9 |
| `log.i_batt_min` | 4 |
| `log.i_motor_abs_max` | 92 |
| `log.running_samples` | 5 |
| `log.samples` | 5 |
| `log.temp_mos_max` | 47 |
| `log.temp_motor_max` | 50 |
| `log.v_max` | 61.8 |
| `log.v_min` | 54.1 |
| `log.v_min_under_load` | 54.1 |

## Parse notes

- mcconf: ConfigVersion 4
- appconf: ConfigVersion 4
- refloat: ConfigVersion 4

## Provenance

Parameter catalogs:

- vedderb/bldc `release_7_00` @ `e877eaead23e`
- vedderb/vesc_tool `release_7_00` @ `6528c4e2a963`
- lukash/refloat `v1.3.1` @ `a2b55d96f508`

Profiles: hardware `ubox_single_100`, cell `molicel_p45b`, motor `pint_stock` (`src/vfa/data/profiles/`). Evidence labels: Source = confirmed in pinned upstream source; Dev = documented by an author or vendor, not re-read; Comm = community rule of thumb; Analysis = engineering reasoning; UNVERIFIED = not confirmed from a primary source.
