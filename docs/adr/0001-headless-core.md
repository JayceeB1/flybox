# ADR 0001 — Headless core is authoritative

- Status: Accepted
- Date: 2026-09-12

## Context

FlyBox ultimately wants a high-quality UE5 vivarium, but scientific reproducibility requires experiments to remain valid when no renderer is running.

Tying neural or body stepping to a render loop would make results depend on frame rate, tab/window state, GPU stalls, or presentation bugs.

## Decision

The FlyBox simulation core runs headlessly and owns experiment sequencing. Viewer clients are optional consumers of versioned telemetry and producers of explicit experiment commands.

The core must continue correctly when no viewer is connected or when a viewer disconnects.

## Consequences

- Rendering cannot be used as an implicit simulation clock.
- UE5 does not become a dependency of V0.
- Runs can be batch-executed faster/slower than wall time.
- Viewer replay can operate on recorded state without recomputing the neural model.
- Core/viewer transport must be versioned and testable independently.
