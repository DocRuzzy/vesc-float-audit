import pytest

from vfa import configxml
from builder import defaults, to_xml


def test_roundtrip_defaults():
    vals = defaults("mcconf", "thor301")
    cfg = configxml.parse_bytes(to_xml("mcconf", vals).encode(), "mcconf")
    assert cfg.config_version == 4
    assert cfg.values["l_abs_current_max"] == 250.0
    assert cfg.values["si_motor_poles"] == 14
    assert not cfg.unknown and not cfg.missing and not cfg.out_of_range


def test_six_significant_digits():
    xml = b"<MCConfiguration><foc_motor_flux_linkage>0.0284567</foc_motor_flux_linkage></MCConfiguration>"
    cfg = configxml.parse_bytes(xml, "mcconf")
    assert cfg.values["foc_motor_flux_linkage"] == pytest.approx(0.0284567)
    assert "l_current_max" in cfg.missing


def test_wrong_root_and_definition_file():
    with pytest.raises(configxml.ConfigError, match="expected <APPConfiguration>"):
        configxml.parse_bytes(b"<MCConfiguration/>", "appconf")
    with pytest.raises(configxml.ConfigError, match="parameter definition file"):
        configxml.parse_bytes(b"<ConfigParams><Params/></ConfigParams>", "mcconf")
    with pytest.raises(configxml.ConfigError, match="not well-formed"):
        configxml.parse_bytes(b"<MCConfiguration>", "mcconf")


def test_unknown_bad_and_out_of_range():
    xml = (b"<APPConfiguration><bogus>1</bogus><imu_conf.sample_rate_hz>abc</imu_conf.sample_rate_hz>"
           b"<imu_conf.mahony_kp>5000</imu_conf.mahony_kp></APPConfiguration>")
    cfg = configxml.parse_bytes(xml, "appconf")
    assert cfg.unknown == ["bogus"]
    assert cfg.bad_values[0][0] == "imu_conf.sample_rate_hz"
    assert cfg.out_of_range[0][0] == "imu_conf.mahony_kp"


def test_refloat_signature_checked():
    with pytest.raises(configxml.ConfigError, match="RefloatConfig"):
        configxml.parse_bytes(b"<CustomConfiguration><config_name>FloatConfig</config_name>"
                              b"</CustomConfiguration>", "refloat")
    cfg = configxml.parse_bytes(b"<CustomConfiguration><config_name>RefloatConfig</config_name>"
                                b"<kp>22.5</kp></CustomConfiguration>", "refloat")
    assert cfg.values["kp"] == 22.5
