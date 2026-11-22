# vesc-float-audit

Tooling to capture and audit the configuration of VESC-based self-balancing
boards running the Refloat package.

Given a board's motor config, app config and Refloat config (and optionally a
ride log), the analyzer checks them against controller, cell and firmware
limits and reports settings that are unsafe, inconsistent or far from the
expected range.

**Status:** not yet implemented. This repository currently holds the brief and
the reference material.

- [`docs/brief.md`](docs/brief.md) — what is being built, in phases
- [`docs/knowledge-base.md`](docs/knowledge-base.md) — tuning reference and audit rules, with evidence labels
- [`CLAUDE.md`](CLAUDE.md) — hardware and constraints for AI-assisted development

The reference material mixes developer documentation with community rules of
thumb and some unverified items; each is labelled. It is not a substitute for
the upstream documentation, and nothing here has been validated on a board.
