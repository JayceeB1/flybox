## Summary

What changes, and why?

## Scope

- [ ] Code only / no scientific mapping change
- [ ] Dataset/provenance
- [ ] Neural model
- [ ] Sensory bridge
- [ ] Motor bridge
- [ ] Body/physics
- [ ] Experiment/validation
- [ ] Viewer/presentation only

## Scientific boundary

If this PR changes behavior or a biological mapping, answer all of the following. Use `N/A` only when truly not applicable.

**Biological source(s):**

**Evidence class(es):** `MEASURED` / `INFERRED` / `MODELED` / `ENGINEERED` / `DERIVED`

**New assumptions/parameters:**

**Expected model/run hash changes:**

**Assay that can fail if this is wrong:**

**Control that distinguishes mechanism from artifact:**

## Third-party / licensing

- [ ] No third-party source/data added or redistributed
- [ ] `THIRD_PARTY.md` updated with exact revision/license/notices
- [ ] Dataset manifests/attribution updated as required

## Validation

Commands/results:

```text
# paste concise results
```

## Claim check

- [ ] README/docs/UI wording does not claim more biological validity than the evidence supports
- [ ] Performance optimizations do not silently alter the scientific model
- [ ] Biological IDs remain lossless across serialization boundaries
