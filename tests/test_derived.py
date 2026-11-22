import pytest

from helpers import audit


def test_per_cell_thresholds(tmp_path):
    _, ns, _ = audit(tmp_path)
    assert ns.values["thr.lv_is_per_cell"] is True
    assert ns.values["thr.lv_v"] == pytest.approx(60.0)     # 3.0 x 20
    assert ns.values["thr.hv_v"] == pytest.approx(84.0)     # 4.2 x 20


def test_absolute_thresholds(tmp_path):
    _, ns, _ = audit(tmp_path, rf={"tiltback_lv": 62.0, "tiltback_hv": 83.0})
    assert ns.values["thr.lv_is_per_cell"] is False
    assert ns.values["thr.lv_v"] == 62.0 and ns.values["thr.hv_v"] == 83.0


def test_cell_count_mismatch_moves_thresholds(tmp_path):
    _, ns, res = audit(tmp_path, mc={"si_battery_cells": 3})   # firmware default
    assert ns.values["thr.lv_v"] == pytest.approx(9.0)
    assert res["ID-002"].fired and res["BAT-010"].fired


def test_torque_constant_ratio(tmp_path):
    _, ns, _ = audit(tmp_path)
    assert ns.values["torque.k"] == pytest.approx(30 * 0.0295 / (30 * 0.027))
    assert ns.values["torque.amps_per_ref_amp"] == pytest.approx(0.027 / 0.0295)
    _, ns2, _ = audit(tmp_path, name="c", mc={"si_motor_poles": 28})
    assert ns2.values["torque.k"] == pytest.approx(28 * 0.0295 / 0.81)


def test_version_not_a_tag(tmp_path):
    _, ns, res = audit(tmp_path, meta={"package_version": "1.3.1.1"})
    assert ns.values["ver.package_is_tag"] is False
    assert ns.values["ver.package_pinned"] == "1.3.1"
    assert res["VER-003"].fired and not res["VER-004"].fired


def test_thermal_accel_window(tmp_path):
    _, ns, _ = audit(tmp_path, mc={"l_temp_accel_dec": 0.15})
    # bldc mc_interface.c: start' = map(0.15, 0..1, 85..25) = 76
    assert ns.values["thm.fet_accel_start"] == pytest.approx(76.0)


def test_footpad_modes(tmp_path):
    _, ns, _ = audit(tmp_path, rf={"fault_adc1": 0.0, "fault_adc2": 2.0})
    assert ns.values["footpad.mode"] == "single"


def test_imu_bus_resolved_per_variant(tmp_path):
    _, ns, _ = audit(tmp_path)
    assert (ns.values["imu.part"], ns.values["imu.bus_kind"], ns.values["imu.bus_khz"]) == ("LSM6DS3", "i2c_bitbang", 400)
    _, ns2, _ = audit(tmp_path, name="x", meta={"firmware_variant": "rflt-xtras-0.5"})
    assert ns2.values["imu.bus_kind"] == "spi_hw"
    _, ns3, _ = audit(tmp_path, board="b", name="u", app={"imu_conf.sample_rate_hz": 1600})
    assert ns3.values["imu.effective_rate_hz"] == 1000
