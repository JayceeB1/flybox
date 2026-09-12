# Scientific provenance policy

FlyBox's central scientific rule is simple:

> **A value that came from biology must remain distinguishable from a value that came from our model.**

The project therefore treats provenance as runtime data, not just documentation.

## 1. Evidence classes

### `MEASURED`

Directly supplied by a biological dataset or experiment.

Examples:

- MaleCNS body ID;
- a published directed connection between two retained bodies;
- source contact/synapse count;
- explicit published cell type, side, nerve or muscle annotation.

A prediction published as part of a dataset is not automatically `MEASURED` physiology. Preserve whether the upstream field is measured, predicted, consensus, or curated.

### `INFERRED`

Deterministically inferred from measured data by a documented algorithm.

Examples:

- optic-column assignment inferred from a photoreceptor's weighted downstream contacts;
- left/right grouping inferred from explicit anatomical side fields;
- a derived shortest anatomical path through published edges.

The inference code/version and confidence/ambiguity must be recordable.

### `MODELED`

A physiological, sensory, neural, or mechanical model assumption.

Examples:

- LIF threshold/resting potential;
- contact-count -> synaptic efficacy scale;
- transmitter -> excitatory/inhibitory sign assumption;
- proprioceptor angle tuning;
- motor-neuron activity -> actuator gain;
- Hill-muscle parameters not present in MaleCNS.

### `ENGINEERED`

A software/control choice made to connect systems or make an experiment operable.

Examples:

- V0 DN population -> `{forward, turn}` decoder;
- FlyGym CPG used as a temporary motor bridge;
- interpolation/smoothing used only for a viewer;
- transport batching.

An engineered mapping can be biologically motivated; it remains engineered until evidence supports a stronger classification.

### `DERIVED`

A reproducible transformation/aggregate of recorded inputs.

Examples:

- firing rate calculated from spike count/window length;
- path length;
- run-level mean speed;
- normalized contact count;
- plotting/replay data.

Derived data records what it derives from and the transform version.

## 2. Provenance record minimum

Every active model component must be representable by a record containing:

```yaml
id: motor-bridge-dna02-v0
kind: motor_bridge
version: 0.1.0
evidence: engineered
source:
  project: MaleCNS
  release: v1.0
  locators:
    - type:DNa02
references:
  - doi-or-url
parameters:
  aggregation_window_ms: 50
  transfer: "..."
code_revision: <git-sha>
notes: "Temporary V0 bridge to FlyGym CPG"
```

Dataset artifacts additionally carry:

- exact source URL;
- retrieval timestamp;
- byte count;
- SHA-256;
- upstream license identifier;
- local transform and transform code revision.

## 3. Identity rules

Biological IDs can exceed JavaScript's exact integer range.

Rules:

- keep IDs as integer types internally where safe;
- serialize biological IDs as **decimal strings** in JSON/JS/UE boundaries;
- never round-trip IDs through float/double;
- fail closed on non-decimal, negative, duplicate, or lossy identifiers.

## 4. Dataset lineage

A derived artifact must form a chain back to exact raw inputs:

```text
official MaleCNS file
  URL + SHA256 + license
          |
          v
normalized graph
  transform version + output SHA256
          |
          v
simulation graph/profile
  signs/scales/thresholds + SHA256
          |
          v
experiment run
  exact model/bridge/config/code revisions
```

Raw biological structure and simulation-specific structure must not share an ambiguous filename such as simply `connectome.npy`.

## 5. Model profile rule

Any choice that can alter neural/body behavior creates or updates a named model profile, including:

- node/edge filtering;
- edge thresholding;
- sign convention;
- synaptic scale;
- neural constants;
- tonic stimulation;
- bridge population selection;
- transfer functions;
- body actuator mapping;
- random seeds where stochasticity is present.

Performance modes must be model profiles too if they change graph or dynamics. A mode called `fast` cannot silently prune edges.

## 6. Experiment interventions

Silencing, stimulation, lesions, rewards, forced actions and external sensory injections are all experiment events.

Every intervention records:

- target biological IDs/types;
- start/end simulated time;
- amplitude/mechanism;
- evidence class;
- source/reason;
- whether topology, weights, drive, state or body controls were changed.

A UI button is only a command creator; it cannot bypass this event log.

## 7. Claims policy

Documentation and UI labels must match evidence.

Preferred:

- `PAM11 firing rate` when plotting simulated PAM11 spikes;
- `modeled synaptic efficacy` for a simulation weight;
- `connectome-constrained` when anatomy is real but physiology is modeled.

Avoid without direct evidence:

- `dopamine level` when only a DAN spike rate is simulated;
- `pleasure`, `pain`, `addiction`, `attention`, `preference`;
- `the fly learned` when only a weight changed;
- `digital twin` without a qualification of modeled/inferred boundaries;
- `biological real time` unless wall-time and simulated-time requirements are actually demonstrated.

## 8. Review requirement

A PR that changes a scientific mapping must answer in its description:

1. What biological source changed?
2. What evidence class is each new mapping?
3. Which assumptions are new?
4. Which run/model hashes change?
5. What assay can fail if the mapping is wrong?
6. What control distinguishes mechanism from a software artifact?

A mapping without these answers is incomplete even if the code works.
