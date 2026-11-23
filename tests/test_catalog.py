from vfa import catalog as cat

PINS = {
    "vesc_tool": "6528c4e2a963e86ae4104737ddf7c76ffc987d84",
    "bldc": "e877eaead23e23cc0e160302d75554eaeb2c98d0",
    "refloat": "a2b55d96f508653b0436b21410100aaf91f14b04",
}


def test_catalogs_load_and_are_pinned():
    for kind in ("mcconf", "appconf", "refloat"):
        c = cat.load(kind)
        assert len(c.params) > 100
        for name, p in c.provenance.items():
            assert p["commit"] == PINS[name]


def test_firmware_defaults_from_headers():
    mc = cat.load("mcconf")
    # Known gaps resolved from bldc motor/mcconf_default.h.
    assert mc.default("l_temp_accel_dec") == 0.15
    assert mc.default("foc_fw_current_max") == 0.0
    assert mc.default("l_battery_cut_start") == 10.0
    assert mc.default("l_battery_cut_end") == 8.0
    assert mc.default("l_max_duty") == 0.95
    # The vesc_tool XML snapshot differs from the compiled default here.
    assert mc.get("foc_motor_flux_linkage")["xml_default"] != mc.default("foc_motor_flux_linkage")


def test_enum_header_defaults_resolved_by_name():
    # appconf_default.h: APPCONF_IMU_FILTER IMU_FILTER_MEDIUM; the vesc_tool XML says LOW.
    app = cat.load("appconf")
    assert app.default("imu_conf.filter") == 1
    assert app.get("imu_conf.filter")["xml_default"] == 0
    assert app.default("imu_conf.sample_rate_hz") == 200


def test_sentinel_header_default_not_used():
    app = cat.load("appconf")
    p = app.get("controller_id")
    assert p["min"] <= p["default"] <= p["max"]


def test_refloat_defaults():
    rf = cat.load("refloat")
    assert rf.default("tiltback_hv") == 4.3       # per cell
    assert rf.default("tiltback_lv") == 3.0       # per cell
    assert rf.default("kp") == 20.0
    assert rf.default("ki_limit") == 30.0
    assert rf.default("tiltback_duty") == 0.8
    assert rf.default("atr.filter.time_constant") == 0.3
    assert rf.get("atr.filter.time_constant")["suffix"] == "s"
    assert rf.default("config_name") == "RefloatConfig"


def test_describe_value():
    mc = cat.load("mcconf")
    assert mc.describe_value("foc_motor_flux_linkage", 0.0295) == "29.5 mWb"
    assert mc.describe_value("motor_type", 2) == "FOC (2)"
    assert mc.describe_value("l_temp_accel_dec", 0.15) == "15 %"
