# FlyBox

**An open, embodied MaleCNS experimentation platform.**

FlyBox aims to couple a whole-connectome model of the adult male *Drosophila melanogaster* central nervous system to a biomechanical fly body, then make the resulting closed-loop experiments inspectable, reproducible, and eventually observable in a UE5 vivarium.

FlyBox is **not** a claim of a complete digital fly, consciousness, or biologically exact physiology. The connectome supplies anatomy; neural dynamics, sensory transfer functions, motor mappings, muscles, and many physiological parameters still require explicit models. FlyBox treats those boundaries as first-class data rather than hiding them.

## Status

**Foundation / V0 specification. No behavioral claim has been made yet.**

The first milestone is a headless closed-loop prototype:

```text
MaleCNS v1.0
  166.7k retained neurons
  whole brain + VNC
        |
        v
connectome-constrained neural model
        |
        v
identified descending-neuron readout
        |
        v
FlyGym 2.x locomotion controller (temporary V0 bridge)
        |
        v
NeuroMechFly / MuJoCo body
        |
        +---- body state / sensory feedback ----+
                                                |
                                                +--> next neural step
```

UE5 is deliberately **not** the simulation authority. It is planned as an optional high-quality observer, experiment UI, and replay client after the headless core is validated.

## Principles

1. **Measured, inferred, modeled, and engineered are never conflated.** Every scientific mapping must declare its evidence class and provenance.
2. **MuJoCo owns body physics.** A future UE5 client mirrors authoritative state; it does not silently run a second physics truth.
3. **The nervous system remains inspectable.** No hidden policy or LLM may replace the connectome in the primary experimental path.
4. **V0 may use a temporary motor bridge, but the target architecture preserves MaleCNS brain -> VNC -> motor-neuron pathways.**
5. **Experiments are deterministic where the model permits it, checkpointable, replayable, and auditable.**
6. **Raw upstream datasets are not relicensed.** FlyBox code and third-party data/code remain under their own terms.

## Planned repository layout

```text
src/flybox/             stable core contracts and runtime
flybox_core/            headless orchestration (planned)
connectome/              MaleCNS acquisition/normalization (planned)
brain/                   neural engine adapters (planned)
body/                    FlyGym/NeuroMechFly adapters (planned)
experiments/             reproducible experiment definitions (planned)
viewer/ue5/              optional UE5 client (post-V0)
docs/                    architecture, science boundaries, ADRs
```

The layout is intentionally modular: the MaleCNS engine, body backend, sensory bridge, motor bridge, experiment runner, and viewer must be replaceable without changing the scientific record format.

## V0 target

V0 succeeds when a clean checkout can:

- acquire and hash the exact MaleCNS v1.0 inputs without committing the raw dataset;
- deterministically normalize the retained graph and emit a machine-readable manifest;
- run a documented whole-graph neural baseline locally;
- launch FlyGym 2.x headlessly and expose normalized body observations;
- drive locomotion from biologically identified descending-neuron populations through an explicitly temporary CPG bridge;
- record synchronized neural/body telemetry, checkpoints, provenance, and replay metadata;
- demonstrate causal validation with baseline, targeted ablation, and control experiments;
- report wall-clock performance separately from simulated neural and body time.

See [docs/SPEC_V0.md](docs/SPEC_V0.md).

## Roadmap

- **V0 — Headless closed loop:** MaleCNS + FlyGym 2.x, documented DN-to-CPG bridge, checkpoint/replay, causal validation.
- **V0.5 — UE5 observer:** authoritative-state mirror, experiment controls, neural telemetry, replay.
- **V1 — Retinal loop:** FlyGym compound-eye samples mapped to MaleCNS visual inputs; looming is the first validation target.
- **V2 — VNC/motor loop:** reduce/remove the external CPG; preserve MaleCNS VNC -> motor-neuron dynamics and body feedback.
- **V3 — Neuromuscular loop:** motor neurons drive explicit muscle models when six-leg muscle support is scientifically and technically adequate.

See [docs/ROADMAP.md](docs/ROADMAP.md).

## Scientific provenance

FlyBox uses five evidence classes:

- `MEASURED` — directly present in an upstream biological dataset or experiment.
- `INFERRED` — derived from measured data by a documented algorithm.
- `MODELED` — a physiological/mechanical model parameter or transfer function.
- `ENGINEERED` — a software/control interface chosen for the experiment.
- `DERIVED` — deterministic transformation or aggregate of other recorded data.

No interface may silently promote one class to another. See [docs/science/PROVENANCE_POLICY.md](docs/science/PROVENANCE_POLICY.md).

## Prior art and upstream projects

FlyBox is informed by, but is not currently a code fork of:

- MaleCNS v1.0 — the whole male brain + VNC connectome dataset.
- NeuroMechFly / FlyGym 2.x — biomechanical body and sensorimotor simulation.
- Shiu et al. whole-brain LIF work — connectome-constrained neural simulation.
- Fly-Brain-AI — an earlier FlyWire <-> FlyGym brain-body bridge.
- DOOMFLY / Stonkfly / Fly-Wirehead — recent MaleCNS whole-graph simulation experiments.
- DesktopFly — a recent bounded MaleCNS locomotor-circuit/body experiment.

Reference does not imply code incorporation. Any copied or adapted source must be registered in `THIRD_PARTY.md` before merge.

## License

Original FlyBox source is licensed under the **Apache License 2.0**. See [LICENSE](LICENSE) and [NOTICE](NOTICE).

That license does **not** relicense MaleCNS data, FlyGym, MuJoCo, Unreal Engine, datasets, models, papers, assets, or code from other projects. Their status and inclusion rules are tracked in [THIRD_PARTY.md](THIRD_PARTY.md).
