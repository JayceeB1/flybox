# ADR 0002 — MuJoCo owns scientific body physics

- Status: Accepted
- Date: 2026-09-12

## Context

FlyGym/NeuroMechFly is built on MuJoCo and already provides the biomechanical body, joints, contacts, adhesion, sensors, and locomotion abstractions needed by FlyBox.

UE5/Chaos could independently simulate collisions and dynamics, but two physics engines would inevitably diverge.

## Decision

For scientific runs, MuJoCo through FlyGym is the sole authority for body pose, dynamics, collision/contact state and environment interaction.

A future UE5 client mirrors authoritative transforms and experiment state. Visual-only interpolation is allowed but cannot feed unrecorded physics results back into the core.

Any future alternative body backend must implement the same FlyBox body contract and identify itself as a distinct experiment profile.

## Consequences

- No duplicated hidden collision truth in UE5.
- The V0 core can be validated without UE5.
- Scientific environment objects must exist in the authoritative MuJoCo world even when a higher-fidelity visual counterpart exists in UE5.
- Viewer interpolation must be clearly separated from recorded body state.
