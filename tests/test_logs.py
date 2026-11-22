import io
import json
import zipfile

import pytest

from vfa import logs

FC_HEADER = ("Time(s),State,Distance(km),Speed(km/h),Duty%,Voltage,I-Battery,I-Motor,I-FldWeak,"
             "Requested Amps,Pitch,Roll,Setpoint,SP-ATR,SP-Carve,T-Mosfet,T-Mot,ADC1,ADC2,Motor-Fault,"
             "Ah,Ah Charged,Wh,Wh Charged,ERPM,Altitude(m),State(num),True Pitch")


def fc_csv(rows, header=FC_HEADER):
    return "\n".join([header] + rows + ["Upgrade to Float Control Pro for complete ride logs"]) + "\n"


ROW = "0.10,RIDING,0.0,20.0,62%,76.0,30.1,60.3,0.0,61,-0.1,3.4,0.0,0.0,0.0,45.2,51.7,3.04,3.06,0,0,0,0,0,9000,135,1,-0.10"


def test_float_control_csv():
    lg = logs.parse_float_control(fc_csv([ROW, ROW]))
    assert len(lg.rows) == 2 and lg.evidence == "UNVERIFIED"
    r = lg.rows[0]
    assert r["duty"] == pytest.approx(0.62) and r["i_motor"] == 60.3 and r["state"] == "RIDING"
    assert r["speed_kmh"] == 20.0
    assert "skipped 1" in lg.notes[0]


def test_float_control_imperial_and_zip():
    header = FC_HEADER.replace("Speed(km/h)", "Speed(mph)")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("ride.csv", fc_csv([ROW], header))
    lg = logs.parse_named("ride.csv.zip", buf.getvalue())
    assert lg.source == "float_control"
    assert lg.rows[0]["speed_kmh"] == pytest.approx(20.0 * 1.609344)


def test_floaty_json():
    doc = {"id": "x", "logs": [
        {"timestamp": 1000, "dutyCycle": 0.5, "batteryVolts": 70.0, "motorCurrent": 40, "state": 1,
         "controllerTemp": 0, "adc1": 3.0, "adc2": 3.1},
        {"timestamp": 1500, "dutyCycle": 0.6, "batteryVolts": 69.0, "motorCurrent": 50, "state": 1,
         "controllerTemp": 40},
    ]}
    lg = logs.parse_named("ride.json", json.dumps(doc).encode())
    assert lg.source == "floaty" and lg.rows[1]["t"] == 0.5
    assert lg.rows[0]["temp_mos"] is None        # Floaty writes 0 on read failure
    assert lg.rows[1]["duty"] == 0.6


def test_vesc_tool_csv():
    text = ("ms_today;input_voltage;current_motor;current_in;erpm;duty_cycle;fault_code;speed_meters_per_sec\n"
            "1000;70.1;50;20;8000;0.55;0;5\n2000;69.9;60;25;8500;0.60;0;6\n")
    lg = logs.parse_named("rt.csv", text.encode())
    assert lg.source == "vesc_tool" and lg.evidence == "Source"
    assert lg.rows[1]["t"] == 1.0 and lg.rows[1]["speed_kmh"] == pytest.approx(21.6)
    assert lg.rows[0]["duty"] == 0.55


def test_rejects_unknown():
    with pytest.raises(logs.LogError):
        logs.parse_named("x.csv", b"foo,bar\n1,2\n")
    with pytest.raises(logs.LogError):
        logs.parse_named("x.json", b'{"nologs": 1}')
