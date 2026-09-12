# Third-party software, data, and references

This file records FlyBox's third-party boundaries. It is **not legal advice** and does not replace upstream license text. Before code or data is distributed by FlyBox, the corresponding upstream license and attribution must be revalidated against the exact pinned version.

## Inclusion states

- **dependency** — used through its public package/library interface; source is not vendored unless separately recorded.
- **data** — downloaded or derived scientific data with its own data license.
- **adapted-code** — third-party source copied or modified in FlyBox; requires preserved notices and exact source revision.
- **reference-only** — studied as prior art; no source is incorporated.
- **tooling** — required to build or view FlyBox but not covered by the FlyBox Apache-2.0 grant.

## Current registry

| Project / dataset | Role | State in FlyBox | Upstream terms | FlyBox rule |
|---|---|---|---|---|
| MaleCNS v1.0 | whole male brain + VNC connectome data | planned `data` | CC BY 4.0 for the published dataset/derived data as stated by the MaleCNS distribution | Raw data stays outside Git. Acquisition must pin URLs + SHA-256. Derived artifacts must retain attribution and provenance. |
| FlyGym / NeuroMechFly 2.x | biomechanical fly simulation | planned `dependency` | Apache-2.0 (verified from upstream `LICENSE`) | Prefer package dependency; pin the exact release/commit when introduced. Do not vendor without adding exact notices/version here. |
| MuJoCo | physics backend used by FlyGym | transitive/planned `dependency` | Apache-2.0 (verified from upstream `google-deepmind/mujoco` `LICENSE`) | Treat as external dependency; pin the exact installed release when introduced and preserve upstream notices in distributable bundles when required. |
| Unreal Engine 5 | optional V0.5+ viewer/runtime | planned `tooling` | Epic Games Unreal Engine license/EULA; not open-source Apache-2.0 | UE project/plugin must remain clearly separated from FlyBox core licensing. No Epic proprietary code/assets are relicensed by FlyBox. |
| Shiu et al. Drosophila brain model | scientific architecture/reference | `reference-only` at bootstrap | verify repository/source license before any code reuse | Reimplementation from papers is distinct from source copying; source adaptation requires a registry update first. |
| Fly-Brain-AI (`neilt93/Fly-Brain-AI`) | prior closed-loop FlyWire <-> FlyGym bridge | `reference-only` | repository states MIT | No code currently incorporated. If reused, pin commit and preserve MIT notice. |
| DOOMFLY (`nftechie/doomfly`) | prior MaleCNS whole-graph simulator | `reference-only` | repository states MIT for original DOOMFLY code; third-party data/components retain separate terms | No code currently incorporated. Any kernel adaptation requires commit-level provenance + notices. |
| Stonkfly (`nftechie/stonkfly`) | MaleCNS neural backend prior art | `reference-only` | repository states MIT | No code currently incorporated. |
| Fly-Wirehead (`mattyhempstead/fly-wirehead`) | MaleCNS neural/visual experiment prior art | `reference-only` | repository contains code adapted from Stonkfly with preserved MIT notice, but FlyBox must re-check the exact reusable component before copying | No code currently incorporated. Do not assume a blanket repository license. |
| DesktopFly (`DenisSergeevitch/desktop-fly`) | MaleCNS locomotor extraction prior art | `reference-only` | repository states MIT for code; datasets retain their own licenses | Anatomical extraction ideas may be reimplemented; source copying requires exact commit + notice registration. |

## Mandatory rule before third-party source enters the repository

A PR that adds or adapts third-party source must update this file in the same PR with:

1. upstream repository/project;
2. exact commit/tag/release;
3. source file(s) reused;
4. upstream license identifier and preserved notice location;
5. FlyBox destination file(s);
6. whether the code is copied, modified, translated, or clean-room reimplemented;
7. any data/assets bundled by that change.

If these fields are missing, the third-party source must not merge.

## Dataset policy

Large or mutable upstream datasets are not committed by default. FlyBox acquisition tooling should instead emit a versioned manifest containing at least:

```json
{
  "dataset": "malecns_v1",
  "source_url": "...",
  "sha256": "...",
  "bytes": 0,
  "license": "CC-BY-4.0",
  "retrieved_at": "...",
  "transform": "raw"
}
```

Every normalized/derived dataset must link back to the raw manifests and record the deterministic transform version.
