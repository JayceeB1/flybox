# FlyBox architecture

## 1. System intent

FlyBox is a headless scientific simulation core with optional presentation clients. The core couples a connectome-constrained neural model to a biomechanical body while recording enough provenance to distinguish biological measurements from inferred/modelled interfaces.

The architectural unit is **an experiment run**, not a rendered frame.

## 2. Authority boundaries

```text
                         ┌───────────────────────────┐
                         │      experiment runner    │
                         │ config / clocks / record  │
                         └─────────────┬─────────────┘
                                       │
             ┌─────────────────────────┼────────────────────────┐
             │                         │                        │
             v                         v                        v
   ┌──────────────────┐      ┌──────────────────┐     ┌──────────────────┐
   │ neural backend   │      │ body backend     │     │ provenance/store │
   │ MaleCNS model    │      │ FlyGym / MuJoCo  │     │ events/checkpoint│
   └────────┬─────────┘      └────────┬─────────┘     └──────────────────┘
            ^                         │
            │ sensory bridge          │ body observations
            │                         v
            └───────────────── bridge layer
                              │
                              └── motor bridge ──> body actions

                                      │ read-only state / commands
                                      v
                            ┌──────────────────────┐
                            │ optional clients     │
                            │ CLI / plots / UE5    │
                            └──────────────────────┘
```

### Authoritative components

- **Neural time/state:** neural backend.
- **Body pose/collisions/contact physics:** MuJoCo through FlyGym.
- **Experiment sequencing/checkpoints:** FlyBox runner.
- **Scientific provenance:** append-only FlyBox run record.
- **Rendering:** never authoritative.

UE5 may display a wall, but whether the fly contacted that wall must come from the MuJoCo world state for a scientific run.

## 3. Planned modules

### `connectome`

Responsibilities:

- acquire exact versioned MaleCNS inputs;
- verify SHA-256 before use;
- normalize neuron IDs and edges deterministically;
- retain raw biological IDs as decimal strings at JSON boundaries;
- emit graph and provenance manifests;
- never infer physiology during graph import.

### `brain`

Responsibilities:

- load a normalized graph;
- implement one named/versioned neural-dynamics profile;
- accept `SensoryDrive` windows;
- expose identified-neuron `NeuralReadout` values;
- checkpoint every mutable state required for exact replay where supported;
- publish simulation time and wall-clock compute time separately.

The first backend may adapt/reimplement a whole-graph LIF approach, but the backend API must not assume LIF forever.

### `body`

Responsibilities:

- own FlyGym/NeuroMechFly lifecycle;
- convert backend-native units to FlyBox SI contracts;
- expose joints, pose, velocity, contact and later retinal/olfactory observations;
- apply a versioned motor command;
- provide deterministic reset from an experiment seed/configuration where supported.

### `bridge`

Two independent directions:

- **sensory bridge:** body/environment -> neural drive;
- **motor bridge:** neural readout -> body action.

Every bridge mapping has its own version and provenance. Replacing a bridge creates a different experiment model even when brain and body versions are unchanged.

### `experiments`

Responsibilities:

- immutable run configuration;
- run IDs and seeds;
- causal interventions (silence/stimulate/lesion/control);
- synchronized scheduling;
- event log, metrics, checkpoint/replay;
- acceptance/validation protocols.

### `viewer`

Post-V0. It receives versioned state snapshots and sends explicit experiment commands. It cannot mutate hidden core state.

## 4. Clocks

FlyBox must never equate render FPS with neural or physics time.

At minimum a run records:

- `neural_time_ms` — simulated neural time;
- `body_time_s` — MuJoCo simulation time;
- `wall_time_s` — elapsed host time;
- `sequence` — accepted cross-component boundary number.

Expected internal rates are backend-specific. A candidate whole-graph neural kernel may integrate at 0.1 ms while MuJoCo uses its own smaller physics step and the bridge exchanges state at a lower control interval.

V0 scheduler invariant:

```text
for each control interval:
    observe authoritative body state
    encode configured sensory channels
    advance neural backend exactly N neural ticks
    decode configured identified DN readout
    apply one body control command
    advance body exactly M physics ticks
    append one synchronized record
```

No component is allowed to advance an unrecorded extra interval.

## 5. Determinism and replay

A checkpoint must include or reference:

- exact code revision;
- dependency versions;
- dataset manifests and normalized graph hash;
- neural model profile and mutable neural state;
- body model/config and restorable body state where available;
- bridge versions and parameters;
- experiment seed/interventions;
- synchronized clock values.

`replay` has two meanings and must be explicit:

1. **state replay** — render/inspect a previously recorded trajectory without recomputing the experiment;
2. **deterministic re-execution** — rerun from a checkpoint and compare hashes/metrics.

A viewer replay only requires (1). Scientific reproducibility aspires to (2) within documented numerical limits.

## 6. V0 motor boundary

V0 intentionally permits an engineered high-level command:

```text
identified MaleCNS descending populations
           |
           v
 documented decoder
           |
           v
{forward, turn, reverse, frequency, stance}
           |
           v
FlyGym hybrid locomotion / CPG
```

This is a bootstrap bridge, **not** the final biological claim. It must be labelled `ENGINEERED`, and experiments must keep the neural populations and decoder parameters visible.

V2 targets:

```text
MaleCNS brain -> native descending neurons -> native VNC -> native motor neurons
                                                    |
                                                    v
                                           actuator/muscle model
```

## 7. V0 sensory boundary

V0 may begin with explicit controlled stimulation needed to validate the neural/body loop. It must not pretend that a generic frame is a calibrated fly retina.

V1 target is a separately validated mapping between FlyGym's compound-eye observations and MaleCNS visual receptor/optic-column identities.

## 8. IPC / UE5 boundary

The transport is intentionally undecided at bootstrap. Requirements before selection:

- cross-language C++/Python compatibility;
- schema versioning;
- local low-latency 60-120 Hz state streaming;
- loss-tolerant viewer telemetry separated from reliable control commands;
- no 64-bit biological ID round-trip through IEEE-754 JSON numbers;
- viewer disconnect must not alter the experiment.

The core contracts in `src/flybox/contracts.py` are transport-independent so the transport can be evaluated empirically in V0.5.
