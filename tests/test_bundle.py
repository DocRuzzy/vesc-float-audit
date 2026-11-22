import json
import shutil
import zipfile

import pytest

from vfa import bundle
import builder


def test_load_directory(tmp_path):
    b = bundle.load(builder.board_a(tmp_path / "a"))
    assert b.hw.id == "thor301" and b.cell.id == "molicel_p45b"
    assert b.mc.values["l_in_current_max"] == 70.0
    assert b.label == "Example A (synthetic)"


def test_load_zip_with_top_folder(tmp_path):
    d = builder.board_b(tmp_path / "boardB")
    z = tmp_path / "boardB.zip"
    with zipfile.ZipFile(z, "w") as zf:
        for p in d.iterdir():
            zf.write(p, f"boardB/{p.name}")
    b = bundle.load(z)
    assert b.hw.id == "ubox_single_100"


def test_missing_file(tmp_path):
    d = builder.board_a(tmp_path / "a")
    (d / "refloat.xml").unlink()
    with pytest.raises(bundle.BundleError, match="missing refloat.xml"):
        bundle.load(d)


@pytest.mark.parametrize("patch,msg", [
    ({"pack": {"s": 20, "p": 0, "cell": "molicel_p45b"}}, "pack.p"),
    ({"package": "Float"}, "only Refloat"),
    ({"hardware": None}, "'hardware' is required"),
    ({"tune_conversions_from_1_2": -1}, "non-negative"),
    ({"firmware_variant": "custom"}, "firmware_variant"),
])
def test_meta_validation(tmp_path, patch, msg):
    d = builder.board_a(tmp_path / "a")
    meta = json.loads((d / "meta.json").read_text())
    meta.update(patch)
    (d / "meta.json").write_text(json.dumps(meta))
    with pytest.raises(bundle.BundleError, match=msg):
        bundle.load(d)


def test_unknown_profile(tmp_path):
    d = builder.board_a(tmp_path / "a")
    meta = json.loads((d / "meta.json").read_text())
    meta["hardware"] = "thor400"
    (d / "meta.json").write_text(json.dumps(meta))
    with pytest.raises(bundle.BundleError, match="no hardware profile 'thor400'"):
        bundle.load(d)


def test_bad_log_is_noted_not_fatal(tmp_path):
    d = builder.board_a(tmp_path / "a", logs={"logs/junk.csv": "a,b\n1,2\n"})
    b = bundle.load(d)
    assert not b.logs and "unrecognised CSV header" in b.load_notes[0]
