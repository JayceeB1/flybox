# ADR 0004 — Apache-2.0 core with explicit third-party boundaries

- Status: Accepted
- Date: 2026-09-12

## Context

FlyBox sits at the junction of open-source software, scientific datasets, papers, game-engine tooling and experimental prior art. A single repository license cannot and must not be interpreted as relicensing all of those inputs.

The project may also adapt code from prior MaleCNS prototypes later. License/provenance debt would be costly to unwind after implementation.

## Decision

Original FlyBox source is Apache-2.0.

Third-party software/data remains under upstream terms and is recorded in `THIRD_PARTY.md`. Raw scientific datasets are downloaded to ignored storage by reproducible tooling rather than committed by default.

Before third-party source code is copied/adapted, the same change must record the exact upstream revision, license, notices and destination files.

Scientific provenance additionally classifies mappings as measured, inferred, modeled, engineered or derived.

## Consequences

- Commercial/open-source reuse of original FlyBox code remains permissive.
- Dataset and engine terms stay visible instead of being accidentally masked by Apache-2.0.
- Source adaptation is reviewable at commit/file granularity.
- Provenance requirements become part of code review and experiment records, not an afterthought.
