# ADR 0003 — V0 may use a temporary CPG motor bridge

- Status: Accepted with removal target
- Date: 2026-09-12

## Context

MaleCNS contains brain, descending neurons, VNC interneurons, sensory/ascending pathways, and motor neurons, but a biologically calibrated end-to-end mapping from spiking motor output to a free six-legged biomechanical muscle model is not currently available as an off-the-shelf component.

FlyGym already has a tested locomotion controller that accepts high-level descending-like commands and produces stable leg trajectories/adhesion.

Trying to solve the complete neuromuscular problem before validating the FlyBox core would block the project on its hardest scientific unknown.

## Decision

V0 may decode identified MaleCNS descending-neuron activity into an explicit `LocomotionCommand`, then use FlyGym's locomotion/CPG layer to actuate the body.

The decoder is classified `ENGINEERED`. It must be versioned, inspectable, parameterized, and covered by causal tests.

The project must not describe V0 locomotion as native MaleCNS VNC/motor-neuron control.

## Consequences

- V0 can validate data acquisition, neural simulation, body integration, clocks, interventions and causality early.
- The CPG bridge provides a stable baseline for later native-VNC comparisons.
- V2 explicitly targets reducing/removing this bridge by preserving MaleCNS VNC -> motor-neuron pathways.
- Any trained black-box readout is a separate experiment profile, not the default V0 path.
