# VESC onewheel tuning knowledge base

Condensed from the research report of 2026-11-22. Intended as the seed for the
`vesc-float-audit` rule engine: every range and cross-check here should become a rule
with an id, severity, rationale and source.

Evidence labels used throughout:

- **[Dev]** documented by the Refloat author, the firmware author or the controller vendor
- **[Comm]** community rule of thumb (mostly pev.dev guides, many older than fw 6.06 / Refloat 1.3)
- **[Analysis]** engineering reasoning, not documented anywhere
- **[UNVERIFIED]** not confirmed from a primary source; confirm before turning into a hard rule

---

## 1. Version baseline

| Component | State as of Nov 2026 | Audit relevance |
|---|---|---|
| VESC firmware | 7.00 stable (May 2026); 7.01 in development | Field weakening moved to the fast loop; FW and MTPA currents now combine as max, not sum; new optional overspeed/underspeed/encoder-slip faults |
| Onewheel firmware fork | lukash/bldc `v7.00-rflt-xtras-0.5` (Sep 2026) | Faster LSM6DS3 sampling and bus, Data Recording, `crash_diag`, option to disable the temperature fault |
| Refloat | 1.3.1 (2026-11-06) is the latest release found; owner reports "1.3.1.1" — confirm the tag | 1.3.1 fixes a nosehunting / rough-motor bug in 1.3.0 and a sample-rate dependence in the Mahony filter |
| Float package (legacy) | v2.0 (Jan 2024) | Refloat 1.0 forked from Float 1.3 |

### Version traps that change what the numbers mean

1. **Torque normalisation (fw 6.06+, Refloat 1.3) [Dev].** Gains are converted to torque
   using flux linkage, normalised to 27 mWb. With `k = λ / 27`:
   - multiplied by k: Angle P, Rate P, Angle I, I-term limit, booster current,
     torque-tilt start current, ATR amps ratio
   - divided by k: torque tilt strength
   - `si_motor_poles` must be 30
2. **"Convert from 1.2" button (1.3.1)** can be applied repeatedly. A tune must be
   converted exactly once. A twice-converted tune is a red flag.
3. **Loop Hertz is gone.** The PID runs in the IMU callback, so IMU sample rate is the
   control-loop rate. Verify with Control Loop Frequency in realtime data.
4. **Setpoint smoothing (1.3)** applies to all tilts. Turn Tilt Max Tiltback Speed and
   Remote Tiltback Speed were replaced by time constants; ATR Response Boost was removed.
5. **Fw 6.06 "Calibration Modes"** is re-enabled by default even after a config restore.
6. **Fw 6.02 → 6.05** changed speed tracking; motor detection must be re-run.
7. **Darkride** has a serious bug in Refloat 1.1.0 through 1.2-beta2.

---

## 2. Board profiles

### Board A — Thor 301

| Item | Value |
|---|---|
| Controller | Fungineers Thor 301, onboard ESP32 VESC Express |
| IMU | LSM6DS3 [Dev] |
| Pack | 20S2P Molicel P45B, charge-only BMS, no CAN BMS data |
| Extras | 10k NTC (B3950) on ADC3; footpads on ADC1/ADC2 |

Controller limits [Dev, Fungineers]:

- 84 V absolute maximum operating voltage; 45 V recommended minimum
- Battery current 100 A max
- Phase current 300 A absolute max, 250 A recommended limit
- PWM 10–60 kHz; minimum motor inductance 10 µH
- Thermal foldback above 80 °C, cutoff at 100 °C
- Connect XT60 before CAN: an unevenly seated XT60 can route current through the CAN transceiver

Derived settings:

| Setting | Value | Basis |
|---|---|---|
| Battery current max | 65–75 A durable; 90 A only as a short-peak ceiling | 2 × 45 A cell rating [Analysis] |
| Regen max | about −40 to −50 A | 2 × 13.5 A = 27 A rated charge; short pulses tolerated [Analysis] |
| Cutoff start / end | 54 / 50 V | 2.7 / 2.5 V per cell [Comm] |
| LV tiltback | 60 V | 3.0 V per cell [Comm] |
| HV tiltback | 84 V | Controller ceiling overrides the 4.3 V/cell community rule (86 V) [Analysis from Dev spec] |
| Absolute max current | ≤ 250 A, and ≥ about 1.3 × motor max | [Dev] + [Analysis] |

### Board B — Spintend Single Ubox 100V 100A

| Item | Value |
|---|---|
| Controller | Spintend Single Ubox 100V 100A; firmware-compatible with the VESC 100V/250A target [Dev] |
| IMU | BMI160 [UNVERIFIED for this exact model; Spintend lists it on the sibling single Ubox] |
| Bluetooth | Via NRF module/port; no ESP32 VESC Express found [UNVERIFIED] |
| Motor | Original Onewheel Pint hub motor |
| Pack | 15S1P Molicel P45B, original BMS modified to charge-only |

Open items for this profile:

- Phase and absolute current limits for the Ubox 100V 100A are not confirmed. Read
  them from the hardware config in the firmware source or Spintend's documentation.
- No reference R / L / λ values were found for the Pint motor. Record the detection
  output and compute `k` from the measured λ. Do not borrow Hypercore numbers.
- With a BMI160 the rflt-xtras IMU improvements do not apply [Dev, by analogy with
  the BMI160-based ADV200].

Derived settings:

| Setting | Value | Basis |
|---|---|---|
| Battery current max | about 35–40 A durable; 45 A is the datasheet ceiling | 1 × 45 A cell rating [Analysis] |
| Regen max | about −20 to −25 A | 13.5 A rated charge, same pulse allowance as Board A [Analysis] |
| Cutoff start / end | 40.5 / 37.5 V | 2.7 / 2.5 V per cell [Comm] |
| LV tiltback | 45 V | 3.0 V per cell [Comm] |
| HV tiltback | 63 V (4.2 V/cell); 64.5 V is the community 4.3 V/cell figure | Controller voltage is not the constraint here [Comm] |

**This is the headroom-critical board [Analysis].** A 1P pack has roughly
15 × 7–15 mΩ ≈ 105–225 mΩ of series resistance, so a 40 A draw sags the pack by
about 4–9 V on a ~55 V nominal bus. Battery current max also binds early, and it
binds at high duty, which is exactly where recovery torque is needed. Expect
conservative duty tiltback, no or minimal field weakening, and LV tiltback set to
tolerate sag without masking a genuinely low pack.

### Charge-only BMS (both boards) [Analysis]

1. The VESC voltage cutoffs and LV pushback are the entire over-discharge protection.
   Cutoffs must not be set "off".
2. Cell imbalance is invisible. Pack voltage ÷ S hides a weak group, so LV pushback
   should be conservative.
3. Nothing interrupts regen. HV pushback is the only overcharge guard; a long
   descent straight off the charger is the risk case.
4. Board A's ADC3 thermistor is not read by stock firmware or stock Refloat as a
   battery temperature. Unless a script or fork reads it, battery temperature is
   unmonitored.

### Cell data — Molicel P45B

4.5 Ah; 45 A continuous discharge; charge 4.5 A standard, 13.5 A maximum;
2.5–4.2 V; DC resistance under 15 mΩ at 10 s.

---

## 3. Motor config (mcconf) reference

| XML parameter | Role | Expected | Failure mode if wrong |
|---|---|---|---|
| `l_current_max` / `l_current_min` | Phase current limit; the balance loop's torque ceiling | ≥ 100 A for adult riders [Comm]; Hypercore ~120 A, Superflux HS ~160 A [Comm] | Too low: soft nosedive. Too high on a saturating motor: crunch |
| `l_abs_current_max` | Instantaneous trip; cuts the motor | ≥ ~1.3 × motor max and ≤ controller rating | Too close to motor max: fault on bumps or hard braking |
| `l_in_current_max` / `l_in_current_min` | Battery and regen limits; bind at high duty | From cell data, section 2 | Nose dips when accelerating at speed or climbing |
| `l_battery_cut_start` / `_end` | Linear current foldback | 2.7 / 2.5 V per cell [Comm] | Wizard (esk8) defaults cause nosedives at low charge |
| `l_max_duty` | Modulation ceiling | 0.95 (firmware default [Dev]) | — |
| `foc_fw_current_max`, `foc_fw_duty_start`, `foc_fw_ramp_time` | Field weakening | Off by default. Community: 30 A / 60% / 500 ms [Comm] | See section 6 |
| `foc_observer_gain`, `foc_sensorless_mode` | Flux observer | About half the detected gain [Comm] | Growl, crunch, poor hall→sensorless handover |
| `foc_motor_r`, `foc_motor_l`, `foc_motor_ld_lq_diff`, `foc_motor_flux_linkage` | Plant model; λ also drives Refloat's `k` | Within the motor's expected range; R often raised ×1.2–1.25 against crunch [Comm] | Wrong λ skews torque normalisation and observer |
| `foc_current_kp` / `foc_current_ki` | Current PI | KP = L/1000, KI = R after any hand-edit of R or L [Comm] | Whine, oscillation |
| `foc_f_zv` | Switching frequency; major driver of loop jitter | 25–30 kHz; 25 kHz gave the most stable timing in the Refloat author's tests [Dev] | Noise, nose hunting; very high values with a high IMU rate have reset controllers [Dev] |
| `foc_sl_erpm`, `foc_hall_interp_erpm` | Hall handover and interpolation | 1500–2000 sensorless ERPM; interpolation ~250 [Comm] | Low-speed cogging, transition jerk |
| `l_temp_fet_start/end`, `l_temp_motor_start/end` | Thermal foldback | Wide gap between start and end | Abrupt foldback mid-ride |
| `l_temp_accel_dec` | Lowers temp limits during acceleration | **0** for balance vehicles [Comm] | Power loss before reaching over-temperature. Default is non-zero [UNVERIFIED: 0.15] |
| `si_motor_poles` | Used for torque conversion | **30** [Dev] | Wrong torque normalisation |
| Wattage limits, max ERPM, fw 7.00 overspeed faults | Hidden caps | Unlimited / disabled / far above reachable speed [Analysis] | Any cap that engages at speed is a nosedive |
| Short phases at 0 duty (6.05+) | Standstill hold | On [Comm] | Board rolls away |

### Motor reference values [Comm, FloatHub]

| Motor | Current max | R (mΩ) | L (µH) | λ (mWb) | k |
|---|---|---|---|---|---|
| Hypercore | 120 A | 80–105 | 190–230 | 26–30 | 0.96–1.11 |
| Superflux Mk2 HS | 160 A | 33–43 | 120–144 | 24.5–26.5 | 0.91–0.98 |
| Superflux Mk3 HS | 160 A | 33–40 | 105–125 | 23–25 | 0.85–0.93 |
| Superflux 5" HT | 140 A | 65–85 | 160–200 | 29–31 | 1.07–1.15 |
| Pint (original) | not found | not found | not found | not found | compute from detection |

---

## 4. IMU and app config (appconf) reference

- **IMU type by controller [Dev]:** LSM6DS3 on Thor 300/301/400, Little FOCer 3.1/4,
  ADV500, Tronic 250R. BMI160 on ADV200 and most others.
- **Sample rate:** 416 or 833 Hz are the long-proven settings.
- **LSM6DS3 bus/rate matrix on rflt-xtras [Dev]:**

  | I²C bus | Sample rate | Status |
  |---|---|---|
  | 400 kHz | 900 Hz | safe |
  | 400 kHz | 1200 Hz | **dangerous — spurious resets** |
  | 700 kHz | 1200 Hz | expected safe after an initial test |
  | 700 kHz | 1600 Hz | unknown |

  The 700 kHz bus is selected by setting "Use magnetometer" to false.
  IMU_FILTER_LOW is recommended with the fast bus.
- **App Config Mahony:** KP 0.2, KI 0. Refloat 1.3 resets a high KP to 0.2 at startup.
  This filter only feeds true pitch, fault checks, quickstop and the booster.
- **Refloat's own balance filter:** Pitch KP, Roll KP, Yaw KP, Accelerometer Confidence
  Decay live in the Refloat config, not appconf.
- **Calibration:** the IMU wizard can leave a high Mahony KP in appconf. If calibration
  is suspect: back up, read defaults on App Cfg, write, recalibrate [Comm].

---

## 5. Refloat config reference

Exact 1.3 defaults were not retrieved. Take them from `src/conf/settings.xml` at the
pinned tag.

| Group | Parameters | Guidance |
|---|---|---|
| Core PID | Angle P, Angle I, Rate P, braking multipliers, I-term limit | Angle P 10–35; I-term limit 20–30 A, 0 disables [Dev help text]. All ×k on fw 6.06+ |
| ATR | Strength up/down, amps ratio (×k), transition boost, filter, on/off speed limits and time constants | Tail drag or nose lift is usually strength vs amps ratio vs time constant |
| Torque tilt | Strength and regen strength (÷k), start current (×k), on/off speeds and time constants | 1.3.0 final fixed previews applying only ~37% strength |
| Turn tilt | Strength, start angle, start ERPM, yaw aggressiveness, speed boost, time constant | Twitchy turns: strength or time constant; also Roll KP |
| Booster | Angle, ramp, current (×k) | Uses App Config true pitch |
| Pushbacks | Duty threshold/angle/speed; HV and LV thresholds; temp alerts; haptic buzz | HV/LV can sit at effectively-off values (200 V / 0 V seen in one build). Community: angle 6°, speed 3°/s |
| Faults / stop | Pitch and roll fault angles and delays; ADC1/ADC2 thresholds; half/full switch delays; Reverse Stop; quickstop | Community: full-switch delay 300 ms, half 500 ms or more. An ADC threshold of 0 enables single-sensor mode |
| Darkride | Inverted riding | Version check, section 1 |

New or renamed XML tags in 1.3 [UNVERIFIED, third-party schema comparison]:
`atr.filter.{on,off}_speed_limit`, `torque_tilt.filter.{on,off}_speed_limit`,
`time_constant` fields under `atr.filter` and `torque_tilt.filter`,
`turn_tilt.filter.time_constant`, `remote.filter.time_constant`, `atr.transition_boost`.

---

## 6. Headroom and safety

- **Duty headroom.** Recovering pitch means accelerating the wheel, which needs spare
  voltage: roughly `(1 − duty) × V_bus`. Near 95% duty the board can cruise but cannot
  recover. Duty depends on speed and on the sagging bus, not on any setting.
  Community minimum margin: duty pushback at 80–85% [Comm/Analysis].
- **Sag raises duty at a given speed.** Low charge + hill + speed is the dangerous
  corner, and battery current max binds there too [Analysis].
- **Field weakening [Analysis unless marked]:**
  1. Duty stops being a faithful headroom indicator once −Id is injected.
  2. Id consumes part of the current budget, leaving less q-axis torque for recovery.
  3. If FW is withdrawn suddenly (fault, reset, foldback), back-EMF above bus voltage
     forces uncontrolled regen. Worst at full charge with a charge-only BMS.
  4. Fw 7.00 changed FW behaviour; values carried over from 6.0x need re-validation [Dev].
  5. Capping ERPM to limit FW speed itself causes a nosedive at that speed [Comm].
  Community practice: start FW around 60–65% duty and lower duty pushback to ~80% [Comm].
- **rflt-xtras temperature fault:** setting Temp Cutoff End ≥ 100 °C disables the
  firmware fault so a sensor failure cannot cut power; the rider then relies on
  package alerts [Dev].

---

## 7. Audit rules

### Cross-checks, in order

1. **Versions.** Firmware, package tag, whether the tune was converted from 1.2 (once).
2. **Identity.** Poles = 30; S count, wheel diameter; λ in range for the motor; compute k.
3. **Battery.**
   - battery max ≤ P × cell continuous rating × derate
   - regen ≤ about P × cell max charge × 1.5–1.85
   - cutoff end ≥ controller minimum
   - cutoff end < cutoff start < LV pushback
   - HV pushback ≥ full-charge voltage and ≤ controller maximum
4. **Current.** Motor max ≥ 100 A; abs max ≤ controller rating and ≥ ~1.3 × motor max;
   battery limit consistent with motor limit at expected duty.
5. **Duty and FW.** Max duty 0.95; duty pushback 80–85%, lower with FW; FW current
   ≤ ~30–50% of motor max; FW duty start below pushback threshold.
6. **Thermal.** Accel decrease = 0; wide start/end gaps; is battery temperature monitored?
7. **IMU and timing.** IMU type vs bus speed vs sample rate; ZVF 25–30 kHz; measured
   Control Loop Frequency matches the target; App Mahony KP 0.2.
8. **Refloat tune.** The ×k and ÷k parameters; time constants; footpad thresholds against
   logged ADC voltages; switch delays; Reverse Stop; Darkride.
9. **Log.** Any limit saturating before an event; duty with sag; setpoint contributors;
   ADC dropouts; fault codes.

### Red flags (severity: critical)

- HV / LV tiltback at 200 V / 0 V or otherwise unset
- Voltage cutoffs left at wizard defaults
- Absolute max current above the controller's recommended limit (250 A on Thor 301)
- HV tiltback above the controller's maximum operating voltage (84 V on Thor 301)
- Motor current max below 100 A
- `l_temp_accel_dec` above 0
- Temperature cutoff end close to start
- Field weakening above ~50 A with duty pushback at 85% or higher
- 1200 Hz IMU sampling on the 400 kHz bus
- Very high ZVF combined with a high IMU rate
- Refloat 1.3.0 (upgrade to 1.3.1); Darkride enabled on 1.1.0–1.2-beta2
- Battery current max above the pack's datasheet ceiling (45 A on Board B)

---

## 8. Symptom → cause → check

| Symptom | Usual causes | Check |
|---|---|---|
| Loose or mushy | Low Angle P / Rate P; low Pitch KP; unconverted tune on a low-λ motor | Apply k once; Control Loop Frequency |
| Too stiff or buzzy | Gains too high; high IMU rate on 1.3.0 | Upgrade; reduce Rate P |
| Nose dips on acceleration | Motor or battery current saturating; weak torque tilt | Current traces flat at a limit; battery max |
| Wobble at speed | Rate P too high; timing jitter; 1.3.0 bug | ZVF, dt jitter, version |
| Vibration at standstill | Jitter; Rate P; filter stale after a rate change | Reboot after changing rate |
| Growl or crunch | Observer gain; R or L off; motor saturation | Halve observer gain; R ×1.2; lower current |
| Harsh braking | R too low; brake-tilt smoothing; regen limit | R; Rate P Braking multiplier |
| Surging | ATR / torque tilt feedback with fast smoothing | Lengthen time constants; ATR amps ratio |
| Tail drag or nose lift on hills | ATR strength vs amps ratio; HV pushback downhill at full charge | Tune up/down separately; HV threshold |
| Twitchy turns | Turn tilt strength or time constant; Roll KP | Slower time constant |
| Low-speed cogging | Hall interpolation ERPM; hall table | ~250; re-run hall detection |
| Random disengage / won't disengage | ADC thresholds vs real voltages; pinout mismatch; switch delays | Plot ADC1/ADC2 against thresholds |
| ABS overcurrent / DRV | Abs max too close to motor max; bad offsets; wiring | Margin; Measure FOC Offsets |
| Overvoltage | Regen at full charge; FW collapse | HV pushback; reduce regen and FW |
| Undervoltage or soft cut | Wizard cutoffs; sag | Per-cell cutoffs; LV pushback |
| Pushback too early or late | Duty threshold vs FW; thresholds scaled by the wrong S | Section 6 |
| Thermal throttling | Accel decrease; narrow start/end gap | Set 0; widen |
| Drifting nose angle | IMU calibration; high App Mahony KP | Recalibrate; KP 0.2 |
| Feel changed after upgrade | 1.3 normalisation and smoothing; 6.06 calibration modes | Convert once; re-detect; re-check offsets |

---

## 9. Capture: files and fields

Per board:

| Artifact | Format | How |
|---|---|---|
| Motor config | VESC Tool `ConfigParams` XML | Motor Cfg → "…" → Save XML; desktop CLI `--getMcConf` |
| App config (includes IMU) | same | App Cfg → "…" → Save XML; `--getAppConf` |
| Refloat config | `<CustomConfiguration>` XML carrying the `RefloatConfig` signature | Refloat Cfg → "…" → Save XML; `--getCustomConf` |
| All three at once | XML | Float Control 3.3+ export [UNVERIFIED on current version] |
| Versions | text | Terminal `fwinfo`; Packages page |
| Fault history | text | Terminal `faults`; `crash_diag` on rflt-xtras |
| Detection baseline | values | R, L, Ld−Lq, λ, observer gain, hall table as the wizard reported them |

Ride data:

| Source | Format | Notes |
|---|---|---|
| Float Control | `.csv.zip` per session | ~10 Hz |
| Floaty | JSON (`schemaVersion: 2`) or CSV | Field names from reverse engineering [UNVERIFIED] |
| VESC Tool RT data / VESC Express | CSV | Motor-side quantities |
| Refloat Data Recording | In-app plot | Loop-rate capture into controller RAM, starts on engage; needs rflt-xtras |

Log fields in priority order: duty, ERPM and speed with battery voltage; motor and
battery current against their limits; pitch, true pitch, setpoint and each setpoint
contributor; ADC1/ADC2 and switch state; control-loop dt and frequency; temperatures
and fault codes; roll and yaw rate.

---

## 10. Sources, ranked

1. `github.com/lukash/refloat` — releases, README, `src/conf/settings.xml`. Authoritative for parameters and version changes.
2. `github.com/vedderb/vesc_tool` (firmware CHANGELOG, `res/config`) and `github.com/vedderb/bldc`. Authoritative for firmware behaviour and defaults.
3. `github.com/lukash/bldc` rflt-xtras releases and the pev.dev announcement. Authoritative for the IMU bus/rate matrix.
4. Fungineers help centre (Thor 301 article). Authoritative for Thor hardware limits.
5. Spintend product pages and firmware blog. Hardware limits for the Ubox — still to be read in detail.
6. Molicel P45B datasheet. Cell limits.
7. pev.dev guides: Battery Voltage Configuration – Best Practices; How to troubleshoot nosedives / crashes; Motor crunch troubleshooting; Motor Wizard Guide; Field Weakening 101; VESCTool Configuration Guide; Float Hub documentation; Dangerous temperature cutoffs. Community heuristics of mixed age.
8. Float Control and Floaty app listings; `acheronfail/float-view`. Export formats.

---

## 11. Known gaps

- Exact Refloat 1.3 default values
- Firmware defaults for `foc_fw_current_max` and `l_temp_accel_dec` from a primary source
- Spintend Single Ubox 100V 100A: phase/absolute current limits, IMU part, I²C bus speed
- Pint motor reference R / L / λ and a sensible motor current max
- Whether the 1.3 on/off speed limits are truly independent per direction (release notes and a third-party analysis disagree)
- Units of the 1.3 smoothing time constants (seconds is inferred, not documented)
- Whether "Refloat 1.3.1.1" is a real tag
