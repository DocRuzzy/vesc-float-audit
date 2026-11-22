# vesc-float-audit

Tooling to capture and audit the configuration of VESC-based self-balancing
boards running the Refloat package.

Given a board's motor config, app config and Refloat config (and optionally a
ride log), the analyzer checks them against controller, cell and firmware
limits and reports settings that are unsafe, inconsistent or far from the
expected range.

**Status:** Phase 1 (analyzer) implemented. Phase 2 (capture feasibility memo)
not started. Nothing here has been validated on a board.

The analyzer only reads exported files. It does not connect to a controller
and never writes a configuration.

## Quick start

```bash
pip install -e '.[test]'
vfa audit path/to/board-a            # Markdown report to stdout
vfa audit board-a.zip -o board-a.md --fail-on critical
vfa compare board-a board-b -o compare.md
vfa rules                            # list the rule set
pytest
```

A bundle is a directory or zip holding `mcconf.xml`, `appconf.xml`,
`refloat.xml` (VESC Tool "Save XML" exports) and `meta.json`, plus optional
ride logs. See [`docs/bundle-format.md`](docs/bundle-format.md). Synthetic
example bundles and their reports are in [`examples/`](examples/).

## What the report contains

1. **Red flags**: every critical finding, first.
2. **Cross-checks**: cell rating vs battery current; voltage cutoffs vs LV/HV
   tiltback; duty tiltback vs max duty vs field weakening; IMU type and rate vs
   bus speed; flux linkage vs Refloat's torque normalisation. Each shows the
   numbers used and the evidence behind each number.
3. Other warnings and info notes.
4. **Not evaluated**: rules whose inputs are missing, such as a vendor
   rating that could not be confirmed or a motor with no reference values.
   These are open questions, not passes.
5. **No finding, but unconfirmed**: rules that did not fire but rest on an
   UNVERIFIED or community figure.
6. **Diff against defaults** for all three configs. The defaults are what a
   freshly flashed controller of that hardware holds.
7. Ride-log metrics, parse notes and provenance.

## Evidence policy

Every rule and every profile value carries a label: **Source** (confirmed in
pinned upstream source), **Dev** (documented by an author or vendor, not
re-read), **Comm** (community rule of thumb), **Analysis** (engineering
reasoning) or **UNVERIFIED**. A rule based on an UNVERIFIED claim cannot be
critical. A rule whose inputs are weak is never reported as a plain pass.

Parameter names and defaults are generated from pinned upstream sources by
`tools/gen_catalog.py`:

| Source | Pin |
|---|---|
| `lukash/refloat` | tag `v1.3.1` (`a2b55d9`). There is no `v1.3.1.1` tag |
| `vedderb/vesc_tool` | branch `release_7_00` (`6528c4e`) |
| `vedderb/bldc` | branch `release_7_00` (`e877eae`) |

## Layout

```
src/vfa/
  configxml.py  bundle.py  logs.py      parsers
  catalog.py    profiles.py             upstream catalogs, hardware/cell/motor profiles
  derived.py    expr.py     engine.py   namespace, safe expression language, rule engine
  report.py     compare.py  cli.py      output
  data/upstream/    generated parameter catalogs (do not edit by hand)
  data/rules/       rules as YAML
  data/profiles/    hardware (thor301, ubox_single_100), cells, motors
tools/            catalog generator, example generator
tests/            pytest suite and synthetic bundle builder
docs/
```

- [`docs/brief.md`](docs/brief.md): what is being built, in phases
- [`docs/knowledge-base.md`](docs/knowledge-base.md): tuning reference and audit rules, with evidence labels
- [`docs/upstream-findings.md`](docs/upstream-findings.md): known gaps resolved from source, and corrections to the knowledge base
- [`docs/bundle-format.md`](docs/bundle-format.md): bundle and `meta.json` format
- [`docs/firmware-updates.md`](docs/firmware-updates.md): what a firmware flash does to stored settings, and the procedure to follow
- [`CLAUDE.md`](CLAUDE.md): hardware and constraints for AI-assisted development

The reference material mixes developer documentation with community rules of
thumb and some unverified items; each is labelled. It is not a substitute for
the upstream documentation.
