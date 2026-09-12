# MaleCNS source acquisition

FlyBox treats upstream connectome bytes as scientific inputs, not ordinary package downloads.

## Official v1.0 sources

The `malecns_v1` dataset profile points to the MaleCNS v1.0 flat-connectome bulk files published from the official MaleCNS download page:

- neuron annotations;
- aggregate neurotransmitter predictions;
- full segment-to-segment connection weights.

The MaleCNS download page links the dataset license to Creative Commons Attribution 4.0 International (CC BY 4.0).

## Two-stage pinning

A newly registered source is deliberately unusable in normal acquisition until both its exact byte count and SHA-256 are pinned.

### 1. Bootstrap audit

```bash
python -m flybox.connectome.acquire malecns_v1 --bootstrap-hashes
```

This is an explicit audit mode. It:

1. downloads each reviewed registry URL to `*.partial`;
2. computes SHA-256 while streaming;
3. atomically installs the completed file;
4. writes `source-manifest.json`;
5. writes `bootstrap-lock-candidate.json` marked `UNREVIEWED_BOOTSTRAP_CANDIDATE`.

The candidate is **not** automatically trusted. A reviewer must compare its URLs/files with the versioned dataset registry and then deliberately copy the accepted `expected_sha256` and `expected_bytes` values into `config/datasets/malecns_v1.yaml`.

The GitHub workflow `MaleCNS hash bootstrap` performs the same operation only when manually dispatched with the confirmation token `BOOTSTRAP-MALECNS-V1`. It uploads only the small manifest/lock candidate as an artifact, never the raw dataset.

### 2. Normal verified acquisition

Once hashes are committed:

```bash
python -m flybox.connectome.acquire malecns_v1
python -m flybox.connectome.acquire malecns_v1 --verify-only
```

Normal mode refuses any unpinned source. Existing cache files are re-hashed before reuse. A wrong cached or downloaded file fails closed; it is never silently replaced or accepted under the same logical release.

## Storage boundary

Raw sources live below `data/<dataset>/raw/`, which is ignored by Git. The source manifest records URL, bytes, SHA-256, license ID, retrieval time, FlyBox code revision, and the resolved dataset-profile hash.

Later normalized datasets must reference this source manifest rather than treating their inputs as anonymous local files.
