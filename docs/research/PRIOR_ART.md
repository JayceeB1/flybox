# Prior art and reusable lessons

This document records projects studied during FlyBox's inception. It is an architectural/research map, not a statement that their code is incorporated.

## MaleCNS v1.0

Role: canonical anatomical substrate targeted by FlyBox.

Useful properties:

- whole adult male brain + ventral nerve cord in one connected dataset;
- neuron/body annotations;
- weighted directed connections/contact counts;
- neurotransmitter annotations/predictions;
- descending, ascending, VNC intrinsic, sensory and motor populations in one source.

FlyBox lesson: preserve the complete anatomical identity/path whenever possible; keep physiology assumptions outside graph import.

## FlyGym / NeuroMechFly 2.x

Role: target biomechanical body and sensorimotor environment.

Useful properties:

- MuJoCo-based body/contacts;
- articulated legs and adhesion;
- compound-eye and olfactory capabilities;
- mechanosensory/body-state access;
- locomotion controllers accepting descending-like signals;
- headless simulation separate from presentation.

FlyBox lesson: reuse the scientifically developed body instead of rebuilding insect biomechanics in UE5.

## Shiu et al. whole-brain LIF model

Role: scientific precedent for connectome-constrained whole-brain spiking dynamics.

FlyBox lesson: a deliberately simplified LIF model can still test connectome-dependent hypotheses, but uniform cell physiology and contact-count-derived weights are model assumptions, not reconstructed electrophysiology.

## Fly-Brain-AI

Repository: `neilt93/Fly-Brain-AI`

Role: strong architectural prior art for a closed loop between a whole FlyWire brain simulation and FlyGym.

Observed architecture:

```text
FlyGym body
 -> sensory encoder
 -> 139k-neuron FlyWire LIF brain
 -> descending decoder
 -> optional VNC-lite
 -> CPG locomotion bridge
 -> FlyGym body
```

Reusable lesson:

- separate body adapter, sensory encoder, brain runner, descending decoder and locomotion bridge;
- use causal ablations/controls rather than visible movement alone.

Boundary not to copy blindly:

- its sensory/readout population selection and high-level decoder contain project-specific heuristics;
- it predates the integrated MaleCNS brain+VNC dataset and uses legacy FlyGym 1.x.

## DOOMFLY / Stonkfly / Fly-Wirehead

Repositories:

- `nftechie/doomfly`
- `nftechie/stonkfly`
- `mattyhempstead/fly-wirehead`

Role: current MaleCNS whole-graph simulation prior art.

Reusable lessons:

- practical MaleCNS v1.0 acquisition/normalization;
- CSR whole-graph representation;
- native C++ stepping from Python;
- explicit 0.1 ms neural integration profile;
- checkpoint/replay/provenance work;
- visual input experiments and identified-neuron readouts;
- honest separation between reconstructed wiring and approximated physiology.

Important caution:

- neurotransmitter sign, photoreceptor dynamics, retinal projections, reward/plasticity and action mappings are explicit modeling choices;
- game/trading/video behavior must not be mistaken for validated natural behavior.

FlyBox lesson: the whole graph is locally tractable enough to attempt; use their engineering as prior art, but independently validate every bridge needed for embodiment.

## DesktopFly

Repository: `DenisSergeevitch/desktop-fly`

Role: bounded MaleCNS locomotor-path/body prior art.

Useful result:

- extracts anatomically identified descending, VNC, leg motor, leg sensory and ascending populations;
- preserves named motor annotations such as tibia/trochanter flexor/extensor and coxa motor groups;
- demonstrates closed body/joint/contact feedback on a reduced MaleCNS locomotor subgraph.

Critical lesson:

MaleCNS anatomy can identify a motor neuron's muscle/channel, while still lacking the force, moment arm, activation kinetics, or proprioceptor tuning needed for a faithful mechanical interface. FlyBox must expose that gap instead of filling it silently.

## FlyChess and related demonstrations

Role: evidence that MaleCNS is already being used as a fixed dynamical reservoir/readout substrate for abstract tasks.

FlyBox lesson: abstract linear/trained readouts are interesting experiments but should not become the hidden default mechanism for natural locomotion. The primary FlyBox path prefers identified biological populations and explicit engineered bridges.

## What remains distinctive about FlyBox

The target combination is:

```text
full MaleCNS brain + VNC
        <->
explicit provenance-aware sensory/motor bridge
        <->
current FlyGym / NeuroMechFly biomechanics
        +
causal experiment runner
        +
optional UE5 observer
```

The novelty target is not simply "make the connectome control something." It is to close the body loop while preserving a machine-readable boundary between anatomy, inference, physiology models and software interfaces.
