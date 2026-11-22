# Configuration comparison — Example A (synthetic) vs Example B (synthetic)

Generated 2026-11-22 by vesc-float-audit.

> The bundles are for different hardware (Fungineers Thor 301 vs Spintend Single Ubox 100V 100A). Limits and defaults differ; a difference below is not by itself a problem on either board.

| | Example A (synthetic) | Example B (synthetic) |
|---|---|---|
| Hardware | Fungineers Thor 301 | Spintend Single Ubox 100V 100A |
| Firmware | 7.00 | 7.00 |
| Refloat | 1.3.1 | 1.3.1 |
| Pack | 20S2P | 15S1P |
| Motor | Hypercore stator, TFL MTE 5" hub, N52 | Onewheel Pint hub motor (original) |

## Findings

| | Example A (synthetic) | Example B (synthetic) |
|---|---|---|
| critical fired | 1 | 0 |
| warning fired | 4 | 6 |
| info fired | 4 | 4 |
| not evaluated | 0 | 10 |

Rules that fired on either board:

| Rule | Severity | Example A (synthetic) | Example B (synthetic) |
|---|---|---|---|
| BAT-012 HV pushback above the controller's maximum operating voltage | critical | FIRED | NOT EVALUATED |
| BAT-002 Battery current max above the durable figure for this pack | warning | no finding (unconfirmed inputs) | FIRED |
| BAT-020 Full charge at the controller's maximum operating voltage | warning | FIRED | NOT EVALUATED |
| LOG-001 Logged duty above the duty pushback threshold | warning | n/a | FIRED |
| LOG-004 Battery current saturating at its limit | warning | n/a | FIRED |
| LOG-010 Footpad readings below threshold while riding | warning | n/a | FIRED |
| THM-005 MOSFET temperature limits above the controller's foldback figures | warning | FIRED | n/a |
| THM-006 Battery temperature unmonitored | warning | FIRED | FIRED |
| VER-007 Tune conversion history unknown on a motor where it matters | warning | FIRED | FIRED |
| BAT-004 Regen limit above the cells' rated max charge current | info | FIRED | FIRED |
| CUR-012 Phases not shorted at zero duty | info | FIRED | FIRED |
| IMU-011 Control-loop frequency not measured | info | FIRED | FIRED |
| TUNE-001 Torque normalisation factor away from 1 | info | FIRED | FIRED |

## Key quantities

### Cell rating vs battery current

| Quantity | Example A (synthetic) | Example B (synthetic) |
|---|---|---|
| Pack | 20 S | 15 S |
| Parallel groups | 2 P | 1 P |
| Cell continuous discharge | 45 A | 45 A |
| Pack continuous rating | 90 A | 45 A |
| Durable figure | 72 A | 36 A |
| Battery Current Max | 70 A | 38 A |
| Cell max charge | 13.5 A | 13.5 A |
| Pack rated charge | 27 A | 13.5 A |
| Regen pulse allowance | 49.95 A | 24.98 A |
| Battery Current Max Regen | -45 A | -22 A |

### Voltage cutoffs vs LV/HV tiltback

| Quantity | Example A (synthetic) | Example B (synthetic) |
|---|---|---|
| Full charge | 84 V | 63 V |
| Empty (cell min) | 50 V | 37.5 V |
| si_battery_cells | 20 | 15 |
| Cutoff start | 54 V | 40.5 V |
| Cutoff start per cell | 2.7 V | 2.7 V |
| Cutoff end | 50 V | 37.5 V |
| Cutoff end per cell | 2.5 V | 2.5 V |
| tiltback_lv (raw) | 3 V | 3 V |
| LV is per-cell | yes | yes |
| LV pushback effective | 60 V | 45 V |
| LV per cell | 3 V | 3 V |
| tiltback_hv (raw) | 4.3 V | 4.2 V |
| HV is per-cell | yes | yes |
| HV pushback effective | 86 V | 63 V |
| Undervoltage fault (l_min_vin) | 40 V | 12 V |
| Overvoltage fault (l_max_vin) | 92 V | 93 V |
| Controller max operating | 84 V | — |
| Firmware Vin limit | 97 V | 95 V |

### Duty tiltback vs max duty vs field weakening

| Quantity | Example A (synthetic) | Example B (synthetic) |
|---|---|---|
| Max duty | 0.95 | 0.95 |
| Max duty − 0.05 | 0.9 | 0.9 |
| Duty pushback threshold | 0.8 | 0.78 |
| Duty current limit start | 1 | 1 |
| FW current max | 0 A | 0 A |
| FW duty start | 0.8 | 0.8 |
| FW / motor max | 0 | 0 |
| Worst-case sag at battery max | 10.5 V | 8.55 V |
| Sag / full charge | 0.125 | 0.1357 |

### IMU type and rate vs bus speed

| Quantity | Example A (synthetic) | Example B (synthetic) |
|---|---|---|
| IMU part | LSM6DS3 | BMI160 |
| Firmware variant | stock | stock |
| Bus | i2c_bitbang | i2c_bitbang |
| Bus speed | 400 kHz | 400 kHz |
| Configured sample rate | 832 Hz | 832 Hz |
| Firmware rate cap | — | 1000 Hz |
| Effective loop rate | 832 Hz | 832 Hz |
| Measured control loop | — | — |
| Zero vector frequency | 25000.0 Hz | 25000.0 Hz |
| App Mahony KP | 0.2 | 0.2 |
| App Mahony KI | 0 | 0 |
| Accel/gyro filter | 0 | 0 |

### Flux linkage vs Refloat torque normalisation

| Quantity | Example A (synthetic) | Example B (synthetic) |
|---|---|---|
| Motor poles | 30 | 30 |
| Flux linkage | 0.0295 Wb | 0.024 Wb |
| k = poles·λ / (30 · 0.027) | 1.093 | 0.8889 |
| Phase amps per configured amp (1/k) | 0.9153 | 1.125 |
| Times converted from 1.2 | — | — |

## Config differences

### Motor config (17 differ)

| Parameter | Example A (synthetic) | Example B (synthetic) |
|---|---|---|
| `foc_current_ki` | 92 | 50 |
| `foc_current_kp` | 0.21 | 0.03 |
| `foc_motor_flux_linkage` | 29.5 mWb | 24 mWb |
| `foc_motor_l` | 210 µH | 250 µH |
| `foc_motor_r` | 92 mΩ | 140 mΩ |
| `foc_observer_gain` | 1.1 | 90 |
| `l_abs_current_max` | 200 A | 160 A |
| `l_battery_cut_end` | 50 V | 37.5 V |
| `l_battery_cut_start` | 54 V | 40.5 V |
| `l_current_max` | 120 A | 110 A |
| `l_current_min` | -120 A | -110 A |
| `l_in_current_max` | 70 A | 38 A |
| `l_in_current_min` | -45 A | -22 A |
| `l_max_vin` | 92 V | 93 V |
| `l_min_vin` | 40 V | 12 V |
| `si_battery_ah` | 9 Ah | 4.5 Ah |
| `si_battery_cells` | 20 | 15 |

### App config (0 differ)

Identical.

### Refloat config (2 differ)

| Parameter | Example A (synthetic) | Example B (synthetic) |
|---|---|---|
| `tiltback_duty` | 0.8 | 0.78 |
| `tiltback_hv` | 4.3 V | 4.2 V |
