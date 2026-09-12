# FlyBox roadmap

The roadmap is organized by **scientific fidelity boundary**, not by visual polish.

## V0 — headless closed loop

Goal: prove the core architecture and causal experiment workflow.

Deliverables:

- reproducible MaleCNS v1.0 acquisition + normalization;
- whole-graph neural backend profile;
- FlyGym 2.x body adapter;
- identified descending-neuron -> explicit engineered locomotion bridge;
- scheduler, run records, checkpoints, replay;
- baseline/ablation/control assays;
- performance and provenance validation.

Exit criterion: `docs/SPEC_V0.md` acceptance tests pass.

## V0.5 — UE5 observer / experiment console

Goal: make validated headless runs observable without changing simulation truth.

Deliverables:

- versioned core/viewer protocol;
- UE5 vivarium scene mirroring MuJoCo state;
- fly skeletal/pose mapping;
- camera modes and slow-motion replay;
- neural telemetry overlays;
- inspect/stimulate/silence controls routed as explicit experiment commands;
- viewer disconnect/reconnect tests proving core independence.

Non-goal: Chaos Physics replacing MuJoCo.

## V1 — compound-eye visual loop

Goal: replace generic/artificial visual stimulation with a documented body-centered visual interface.

Work:

- characterize FlyGym 2.x compound-eye output and coordinate conventions;
- characterize MaleCNS R1-R6/R7/R8 identities and optic-column annotations;
- build and version a FlyGym-ommatidium <-> MaleCNS receptor mapping;
- separate spatial mapping from phototransduction/dynamics assumptions;
- add spectral/luminance profiles without fabricating unsupported receptor channels;
- validate with controlled visual stimuli.

First target assay: **looming response**.

Required controls:

- intact;
- retinal input disabled;
- targeted visual-pathway lesion/silencing;
- shuffled or otherwise predeclared topology control where computationally practical.

## V2 — native VNC / motor-neuron loop

Goal: progressively remove the external locomotion CPG from the scientific path.

Work:

- classify MaleCNS descending, VNC intrinsic, ascending, sensory and motor populations needed for locomotion;
- retain native MaleCNS connectivity through VNC;
- identify named leg motor-neuron output channels;
- map body joint/contact feedback to explicitly modeled sensory populations;
- compare CPG-bridge and native-VNC experiment profiles side by side;
- add lesion assays at DN, premotor/VNC and motor-neuron levels.

The V0 CPG bridge remains available as a baseline profile; it is not silently replaced.

## V3 — neuromuscular loop

Goal: motor-neuron output reaches explicit muscle/tendon mechanics instead of high-level joint control.

Gate: six-leg muscle support and mappings must be scientifically adequate. FlyBox should not invent missing anatomy merely to complete this milestone.

Work:

- pin muscle identity mapping from MaleCNS motor annotations;
- integrate available Hill-type muscle/tendon model(s);
- model activation dynamics with parameter provenance;
- close proprioceptive feedback;
- validate force, gait, lesion and stability behavior against published measurements where available.

## Later research tracks

These are intentionally not milestones until the foundation is validated:

- olfaction and plume environments;
- mechanosensory/haltere loops;
- grooming and flight;
- neuromodulation and plasticity;
- multiple flies / social behaviors;
- parameter ensembles rather than one guessed physiology;
- GPU neural kernels;
- accelerated batch experiments;
- model comparison against electrophysiology/behavior datasets.

## Rule for roadmap promotion

A feature moves into the primary scientific path only when:

1. its source/mapping provenance is recorded;
2. its assumptions are explicit;
3. there is an assay that can fail;
4. a control distinguishes mechanism from presentation;
5. its limitations are documented next to the result.
