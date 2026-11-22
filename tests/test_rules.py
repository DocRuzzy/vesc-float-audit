import pytest

from vfa import engine, expr
from vfa.engine import RuleError, load_rules_from
from helpers import audit, fired
import builder


def test_rule_set_loads_and_is_well_formed():
    rules = engine.load_rules()
    assert len(rules) > 80
    ids = [r.id for r in rules]
    assert len(ids) == len(set(ids))
    for r in rules:
        assert r.sources and r.rationale
        if r.evidence == "UNVERIFIED":
            assert r.severity != "critical"
    # Every cross-check named in the brief has rules.
    for key in engine.CROSSCHECKS:
        assert any(r.crosscheck == key for r in rules), key


def test_every_rule_name_resolves(tmp_path):
    """Catch typos: every dotted name a rule reads must be a key the namespace can produce."""
    log = ("ms_today;input_voltage;current_motor;current_in;erpm;duty_cycle;fault_code;temp_mos_max\n"
           "1000;80;50;20;8000;0.55;0;40\n")
    _, ns, _ = audit(tmp_path, logs={"rt.csv": log},
                     meta={"measured": {"control_loop_hz": 830}, "tune_conversions_from_1_2": 1,
                           "battery_temp_monitored": False})
    known = set(ns.values)
    for r in engine.load_rules():
        unknown = r.inputs() - known
        assert not unknown, f"{r.id} reads unknown names {unknown}"


def test_validation_rejects_bad_rules():
    base = """
- id: X-1
  title: t
  severity: critical
  evidence: UNVERIFIED
  category: battery
  fail: mc.a > 1
  message: m
  rationale: r
  sources: [s]
"""
    with pytest.raises(RuleError, match="cannot be critical"):
        load_rules_from({"t.yaml": base})
    with pytest.raises(RuleError, match="not allowed"):
        load_rules_from({"t.yaml": base.replace("UNVERIFIED", "Source").replace("mc.a > 1", "__import__('os')")})
    with pytest.raises(RuleError, match="lacks 'sources'"):
        load_rules_from({"t.yaml": base.replace("UNVERIFIED", "Source").replace("  sources: [s]\n", "")})


def test_reasonable_examples_have_no_red_flags(tmp_path):
    for board in ("a", "b"):
        _, _, res = audit(tmp_path, board=board, name=board)
        crit = {k for k, r in res.items() if r.fired and r.rule.severity == "critical"}
        assert not crit, (board, crit)


def test_missing_input_is_not_a_pass(tmp_path):
    # Board B has no vendor voltage rating and no Pint reference values.
    _, _, res = audit(tmp_path, board="b")
    for rid in ("BAT-012", "ID-004", "ID-005", "CUR-003"):
        assert res[rid].outcome == "not_evaluated", rid
    # A parameter missing from the export also yields not_evaluated.
    _, _, res2 = audit(tmp_path, name="m", drop=("l_temp_accel_dec",))
    assert res2["THM-001"].outcome == "not_evaluated"
    assert "mc.l_temp_accel_dec" in res2["THM-001"].missing


def test_pass_on_unverified_input_is_marked(tmp_path):
    _, _, res = audit(tmp_path)
    r = res["BAT-001"]          # cell rating is UNVERIFIED
    assert r.outcome == "passed_unverified"
    assert r.weak_inputs.get("cell.continuous_discharge_a") == "UNVERIFIED"


SCENARIOS = [
    # (board, overrides, expected rule)
    ("a", {"rf": {"tiltback_hv": 4.3}}, "BAT-012"),                    # Refloat default HV on 20S: 86 V > 84 V
    ("a", {"rf": {"tiltback_hv": 200.0}}, "BAT-015"),
    ("a", {"rf": {"tiltback_lv": 0.0}}, "BAT-010"),
    ("a", {"rf": {"tiltback_lv": 2.7}}, "BAT-009"),                    # 54 V == cutoff start
    ("a", {"mc": {"l_battery_cut_start": 68.0, "l_battery_cut_end": 60.0}}, "BAT-006"),
    ("a", {"mc": {"l_battery_cut_start": 10.0, "l_battery_cut_end": 8.0}}, "BAT-005"),
    ("a", {"mc": {"l_battery_cut_start": 50.0, "l_battery_cut_end": 50.0}}, "BAT-008"),
    ("a", {"mc": {"l_min_vin": 52.0}}, "BAT-016"),
    ("a", {"mc": {"l_battery_regen_cut_start": 83.0, "l_battery_regen_cut_end": 85.0}}, "BAT-018"),
    ("b", {"mc": {"l_in_current_max": 50.0}}, "BAT-001"),
    ("b", {"mc": {"l_in_current_min": -35.0}}, "BAT-003"),
    ("a", {"mc": {"l_current_max": 80.0}}, "CUR-001"),
    ("a", {"mc": {"l_abs_current_max": 260.0}}, "CUR-003"),
    ("b", {"mc": {"l_abs_current_max": 175.0}}, "CUR-005"),
    ("a", {"mc": {"l_abs_current_max": 140.0}}, "CUR-006"),
    ("a", {"mc": {"l_current_max_scale": 0.8}}, "CUR-008"),
    ("a", {"mc": {"l_duty_start": 0.85}}, "CUR-009"),
    ("a", {"mc": {"l_watt_max": 3000.0}}, "CUR-010"),
    ("a", {"mc": {"l_max_erpm": 12000.0}}, "CUR-011"),
    ("a", {"rf": {"tiltback_duty": 0.92}}, "DUTY-002"),
    ("a", {"rf": {"tiltback_duty": 0.88}}, "DUTY-003"),
    ("a", {"mc": {"foc_fw_current_max": 60.0}, "rf": {"tiltback_duty": 0.85}}, "DUTY-004"),
    ("a", {"mc": {"foc_fw_current_max": 30.0, "foc_fw_duty_start": 0.85}}, "DUTY-006"),
    ("a", {"mc": {"foc_fw_current_max": 30.0}}, "DUTY-008"),
    ("a", {"rf": {"tiltback_duty_angle": 0.0}}, "DUTY-011"),
    ("b", {"rf": {"tiltback_duty": 0.84}}, "DUTY-010"),              # 1P sag
    ("a", {"mc": {"l_temp_accel_dec": 0.15}}, "THM-001"),
    ("a", {"mc": {"l_temp_fet_start": 95, "l_temp_fet_end": 98}}, "THM-002"),
    ("a", {"app": {"imu_conf.sample_rate_hz": 1200}}, "IMU-001"),
    ("a", {"app": {"imu_conf.sample_rate_hz": 1000}}, "IMU-002"),
    ("b", {"app": {"imu_conf.sample_rate_hz": 1600}}, "IMU-003"),
    ("a", {"app": {"imu_conf.sample_rate_hz": 200}}, "IMU-004"),
    ("a", {"app": {"imu_conf.mahony_kp": 2.0}}, "IMU-006"),
    ("a", {"app": {"imu_conf.mahony_kp": 0.5}}, "IMU-007"),
    ("a", {"mc": {"foc_f_zv": 40000.0}, "app": {"imu_conf.sample_rate_hz": 1660}}, "IMU-009"),
    ("a", {"meta": {"measured": {"control_loop_hz": 700}}}, "IMU-010"),
    ("a", {"mc": {"si_motor_poles": 28}}, "ID-001"),
    ("a", {"mc": {"foc_motor_flux_linkage": 0.0}}, "ID-003"),
    ("a", {"mc": {"foc_motor_flux_linkage": 0.020}}, "ID-004"),
    ("a", {"rf": {"fault_adc1": 0.0, "fault_adc2": 0.0}}, "FP-001"),
    ("a", {"rf": {"fault_adc1": 0.0}}, "FP-002"),
    ("a", {"app": {"app_to_use": 2}}, "FP-004"),
    ("a", {"rf": {"kp": 40.0}}, "TUNE-002"),
    ("a", {"rf": {"ki_limit": 0.0}}, "TUNE-004"),
    ("a", {"rf": {"fault_moving_fault_disabled": 1}}, "TUNE-006"),
    ("a", {"rf": {"disabled": 1}}, "TUNE-008"),
    ("a", {"meta": {"package_version": "1.3.0"}}, "VER-001"),
    ("a", {"meta": {"tune_conversions_from_1_2": 2}}, "VER-006"),
    ("a", {"meta": {"firmware": "6.06"}}, "VER-005"),
]


@pytest.mark.parametrize("board,over,rule", SCENARIOS, ids=[s[2] + "-" + str(i) for i, s in enumerate(SCENARIOS)])
def test_scenario_fires(tmp_path, board, over, rule):
    _, _, res = audit(tmp_path, board=board, **over)
    assert res[rule].fired, (rule, res[rule].outcome, res[rule].missing)


def test_refloat_default_hv_flagged_only_where_it_exceeds(tmp_path):
    # 4.3 V/cell on 15S is 64.5 V, well inside the Ubox's firmware limits: no BAT-012 basis,
    # and BAT-012 stays NOT EVALUATED (no vendor rating), never "passed".
    _, _, res = audit(tmp_path, board="b", rf={"tiltback_hv": 4.3})
    assert res["BAT-012"].outcome == "not_evaluated"
    assert not res["BAT-013"].fired


def test_log_rules(tmp_path):
    header = ("Time(s),State,Speed(km/h),Duty%,Voltage,I-Battery,I-Motor,Pitch,True Pitch,Setpoint,"
              "T-Mosfet,T-Mot,ADC1,ADC2,Motor-Fault")
    rows = [f"{i/10:.1f},RIDING,25,{d}%,{v},{ib},{im},0,0,0,50,60,{a1},3.0,{f}"
            for i, (d, v, ib, im, a1, f) in enumerate([
                (60, 80, 20, 40, 3.0, 0), (91, 53, 69, 119, 3.0, 0), (70, 83.5, -30, -90, 1.0, 5)])]
    csv = "\n".join([header] + rows) + "\n"
    _, ns, res = audit(tmp_path, logs={"ride.csv": csv})
    f = fired(res)
    for rid in ("LOG-001", "LOG-002", "LOG-003", "LOG-005", "LOG-008", "LOG-010"):
        assert rid in f, rid
    assert res["LOG-001"].weak_inputs     # Float Control format is UNVERIFIED
    assert ns.values["log.fault_codes"] == (5,)
