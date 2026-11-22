# Audit bundle format

One bundle per board: a directory, or a zip of that directory (a single
top-level folder inside the zip is accepted).

```
board-a/
  mcconf.xml      Motor Cfg  → "…" → Save XML       (root <MCConfiguration>)
  appconf.xml     App Cfg    → "…" → Save XML       (root <APPConfiguration>)
  refloat.xml     Refloat Cfg → "…" → Save XML      (root <CustomConfiguration>, config_name RefloatConfig)
  meta.json       hardware and version facts (below)
  logs/           optional ride logs, any of:
    *.csv.zip       Float Control session export
    *.csv           Float Control CSV, or VESC Tool RT log (detected from the header)
    *.json          Floaty JSON export
```

The XML files are VESC Tool's own "Save XML" output, as written by
`ConfigParams::getXML` (`vedderb/vesc_tool` `configparams.cpp:1024-1060`). Each
parameter is a child element holding its raw, unscaled value, written as an
integer, a 6-significant-digit double or text. The desktop CLI's
`--getMcConf`, `--getAppConf` and `--getCustomConf` write the same format
(`main.cpp:1293, 1332, 1371`). A `ConfigParams` file, which is a parameter
definition file rather than a saved configuration, is rejected.

## meta.json

```json
{
  "board_name": "Board A",
  "hardware": "thor301",
  "firmware": "7.00",
  "firmware_variant": "stock",
  "package": "Refloat",
  "package_version": "1.3.1",
  "motor": {"name": "Hypercore stator, TFL MTE 5in hub, N52", "profile": "hypercore_mte5_n52"},
  "pack": {"s": 20, "p": 2, "cell": "molicel_p45b"},
  "bms": "charge-only",
  "tune_conversions_from_1_2": 0,
  "battery_temp_monitored": false,
  "measured": {"control_loop_hz": 832}
}
```

| Field | Required | Meaning |
|---|---|---|
| `hardware` | yes | hardware profile id: `thor301`, `ubox_single_100` |
| `firmware` | yes | as shown by `hw_status`, e.g. `7.00` |
| `firmware_variant` | no | `stock` (default) or `rflt-xtras-0.5`. Selects the IMU bus data |
| `package`, `package_version` | yes | `Refloat` and the version shown on the Packages page. A version that is not a release tag is audited as the nearest tag, with a warning |
| `motor.profile` | yes | motor profile id: `hypercore_mte5_n52`, `hypercore_stock`, `pint_stock` |
| `pack.s`, `pack.p`, `pack.cell` | yes | series count, parallel count, cell profile id (`molicel_p45b`) |
| `bms` | yes | `charge-only`, `can`, `none` or free text. `charge-only` enables the charge-only rules |
| `tune_conversions_from_1_2` | no | how many times "Convert from 1.2" was applied to this tune; `null` if unknown |
| `battery_temp_monitored` | no | `true` only if something actually reads pack temperature |
| `measured.control_loop_hz` | no | Control Loop Frequency from Refloat's realtime data |
| `export_source` | no | `vesc_tool` (default) or `float_control`. Anything but VESC Tool's Save XML raises CFG-004 |

Profiles live in `src/vfa/data/profiles/{hardware,cells,motors}/`. Add one by
copying an existing file. Give every value an `evidence` label and a `source`.

## Log formats

| Source | Evidence | Notes |
|---|---|---|
| VESC Tool RT log | Source | `;`-separated, header from `vescinterface.cpp:1772-1830`; `duty_cycle` is a fraction; IMU columns are not used |
| Float Control | UNVERIFIED | Column names from the third-party `acheronfail/float-view` parser; `Duty%` is in percent; `Speed(mph)` is converted to km/h; non-matching lines (ads) are skipped |
| Floaty JSON | UNVERIFIED | `logs[]` field names from float-view; `dutyCycle` is a fraction, `timestamp` is in ms; speed units are undocumented |

Floaty CSV is not supported. Export Floaty logs as JSON.

## Float Control config exports

Float Control can export each config as XML. These files load, but they are
not VESC Tool's format. The files seen so far have ConfigVersion 2, about 131
of 211 mcconf and 41 of 122 appconf parameters, 6.05-era mcconf names, a
pre-1.3 Refloat name, no `config_name` signature, and
`haptic.duty_solid_offset` apparently in percent. Set `export_source` to
`float_control`; the report then carries CFG-004, and rules that need missing
parameters are reported as not evaluated. Prefer VESC Tool exports.
