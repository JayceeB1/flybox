# FlyBox V0 specification

## 1. Objective

V0 proves that FlyBox can run a reproducible **headless closed loop** between a versioned MaleCNS whole-graph neural model and a FlyGym 2.x biomechanical body, while making every non-biological interface explicit.

V0 is successful if it establishes a trustworthy experimental substrate. It is not judged by whether the fly looks intelligent or biologically natural.

## 2. In scope

- MaleCNS v1.0 acquisition and deterministic normalization.
- Whole retained graph available to one named neural backend profile.
- FlyGym 2.x / NeuroMechFly body running headlessly through MuJoCo.
- Explicit high-level motor bridge from identified descending-neuron activity to FlyGym locomotion controls.
- Minimal sensory/body feedback sufficient for controlled closed-loop tests.
- Multi-clock scheduler.
- Checkpoint, event log, state replay and re-execution checks.
- Causal experiments: baseline, targeted intervention, control.
- Machine-readable provenance for datasets, models, mappings and run artifacts.
- CPU performance benchmark on one-fly runs.

## 3. Explicitly out of scope

- Unreal Engine viewer.
- A calibrated MaleCNS compound-eye mapping.
- Full olfactory physiology.
- Claiming the LIF backend reproduces real membrane dynamics.
- Removing FlyGym's CPG/hybrid locomotion layer.
- Direct six-leg motor-neuron-to-muscle physiology.
- Learning, reward, addiction, pleasure, consciousness, or emergent-intelligence claims.
- Multi-fly simulation.

## 4. V0 reference data boundary

The graph importer must treat biological data and physiology separately.

### Required raw inputs

The acquisition implementation must use the official MaleCNS v1.0 distribution and pin at least:

- body annotations;
- body neurotransmitter annotations/predictions;
- weighted connectome edges.

The exact upstream filenames/URLs and hashes belong in a generated manifest, not hard-coded only in documentation.

### Node policy

The implementation issue must define and test an explicit retained-node policy. At minimum:

- biological body IDs are losslessly preserved;
- non-neural/glial rows are not silently converted into neurons;
- every excluded row has an accounted exclusion reason;
- duplicate IDs fail preparation;
- JSON uses decimal strings for biological IDs.

### Edge policy

- no invented edges;
- published source weights/contact counts remain recoverable;
- any additional simulation threshold is a separate model profile, not part of raw normalization;
- excluded edge/contact totals are reported;
- autapse policy is explicit.

## 5. Neural backend contract

A V0 neural backend must implement conceptually:

```python
class NeuralBackend(Protocol):
    def reset(self, seed: int) -> None: ...
    def step(self, drives: Sequence[SensoryDrive], duration_ms: float) -> NeuralReadout: ...
    def read(self, neuron_ids: Sequence[str]) -> NeuralReadout: ...
    def silence(self, neuron_ids: Sequence[str], enabled: bool) -> None: ...
    def checkpoint(self, path: Path) -> CheckpointManifest: ...
    def restore(self, path: Path) -> None: ...
```

The initial backend profile may be a whole-graph LIF approximation. Its manifest must record every physiology assumption including timestep, resting/reset/threshold potentials, refractory period, synaptic delay, synaptic scaling/sign policy, tonic drives, neuromodulator handling and optimization/pruning choices.

A backend is not called `validated` merely because software tests pass.

## 6. Body backend contract

The FlyGym adapter must expose a stable FlyBox boundary independent of FlyGym's native observation dictionary.

Minimum body observation:

- thorax position/orientation;
- linear/angular velocity;
- named joint angles and velocities required by V0 locomotion;
- contact/load information required by the selected locomotion controller;
- body simulation time.

Minimum actions:

- reset;
- apply V0 locomotion command;
- advance exact requested simulation steps;
- snapshot state needed for replay/diagnostics.

All values crossing into FlyBox contracts use documented units. Conversions are tested.

## 7. V0 motor bridge

The V0 motor bridge is allowed to use biologically identified descending-neuron populations feeding an engineered decoder and FlyGym's existing locomotion controller.

Candidate functional channels to validate from MaleCNS annotations/literature before implementation include:

- DNa01 / DNa02 — steering-related descending activity;
- DNp09 — forward locomotion-related activity;
- MDN — backward locomotion-related activity.

The implementation must not assume a candidate mapping is correct merely because it produces movement. Each mapping receives:

- exact MaleCNS IDs/types/sides;
- evidence reference;
- aggregation window;
- normalization;
- transfer function;
- saturation/dead-zone values;
- evidence class (`MEASURED`, `INFERRED`, `MODELED`, `ENGINEERED`).

The decoder output is the temporary `LocomotionCommand` contract.

## 8. Scheduler

V0 uses one authoritative scheduler. The scheduler configuration includes:

```yaml
neural_window_ms: ...
body_control_interval_ms: ...
body_physics_substeps: ...
seed: ...
```

Invariants:

1. no render/viewer clock participates;
2. every accepted interval increments a global sequence;
3. neural and body time are recorded independently;
4. wall time is diagnostic only;
5. a paused run advances no simulated clock;
6. intervention start/end boundaries are recorded exactly.

## 9. Run directory

A V0 run should be self-describing:

```text
runs/<run-id>/
  run.json                 immutable configuration + source revisions
  provenance.json          dataset/model/bridge provenance graph
  events.jsonl             append-only synchronized events
  metrics.json             derived validation metrics
  checkpoints/
  replay/                  compact body/neural telemetry for visualization
  logs/
```

Large raw MaleCNS inputs remain in a shared ignored data cache and are referenced by hash.

## 10. Acceptance tests

### A0 — clean bootstrap

On a supported clean environment:

- project installs;
- unit tests run without MaleCNS downloads;
- commands that require external data fail with a precise acquisition instruction.

### A1 — dataset integrity

- official files download to ignored storage;
- every source hash is verified;
- corrupt/mismatched data fails closed;
- a manifest records URL, bytes, SHA-256, version, license and retrieval metadata.

### A2 — deterministic normalization

Two normalizations from identical inputs produce identical graph/manifest hashes.

The report accounts for all node rows, edge rows and synaptic/contact counts as retained or excluded.

### A3 — neural engine mechanism check

From a fixed graph, model profile and seed/checkpoint:

- identical stimulation re-executes to an identical or explicitly tolerance-bounded result;
- a documented stimulus changes activity relative to a matched control;
- identified readouts can be extracted by biological ID;
- targeted silencing changes the targeted population without changing graph topology.

### A4 — FlyGym baseline

- one NeuroMechFly body starts on a flat world;
- fixed scripted locomotion moves it in the expected direction;
- reset reproduces the initial state within documented numerical tolerance;
- observation units/names pass contract tests.

### A5 — brain-to-body command path

A controlled neural/readout fixture drives the V0 motor bridge and causes the expected forward/left/right/backward command signs. This test validates plumbing before claiming connectome causality.

### A6 — closed-loop causal experiment

Run at least:

1. intact baseline;
2. targeted descending-population silencing;
3. a matched control that preserves non-target conditions.

Success requires a predeclared directional metric effect, not merely visible movement. Raw and derived metrics are preserved.

### A7 — checkpoint and replay

- checkpoint captures synchronized clocks and backend state;
- state replay reconstructs the recorded body trajectory without running the brain;
- deterministic re-execution is compared from a checkpoint and reports exact hashes or numerical tolerances.

### A8 — provenance completeness

A validator rejects a run whose active dataset, neural profile, motor bridge, or intervention lacks a provenance record/evidence class.

### A9 — performance report

For one-fly canonical V0:

- record simulated neural seconds / wall second;
- record simulated body seconds / wall second;
- record full closed-loop ratio;
- CPU/RAM and optional accelerator use are reported;
- performance optimizations never silently change the scientific graph/profile.

## 11. Definition of done

V0 is done only when all acceptance tests are automated or have a versioned reproducible assay, the V0 limitation statement is current, and no README claim exceeds the evidence produced by the assays.
