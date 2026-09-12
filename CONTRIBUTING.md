# Contributing to FlyBox

FlyBox is pre-alpha. During the foundation phase, correctness of scientific boundaries matters more than feature count.

## Development rules

- Keep the core headless and transport/viewer agnostic.
- Do not commit raw MaleCNS or other large external datasets.
- Do not silently prune/threshold the scientific graph for performance.
- Do not introduce a neural/body mapping without an evidence class and provenance.
- Do not describe software tests as biological validation.
- Keep biological IDs lossless; JSON-facing IDs are decimal strings.
- Keep viewer/presentation state out of the authoritative experiment state.

## Third-party code

Before copying or adapting external source, update `THIRD_PARTY.md` in the same PR with exact upstream revision, files, license, notices and destination paths.

Reference implementations may be studied without becoming dependencies. Reimplementation from a paper or public interface should not copy protected source text/code unless its terms are explicitly handled.

## Scientific mapping changes

A PR that changes a sensory, neural, motor or biomechanical mapping must state:

1. biological source(s);
2. evidence class for every new mapping (`MEASURED`, `INFERRED`, `MODELED`, `ENGINEERED`, `DERIVED`);
3. new assumptions/parameters;
4. expected run/model hash changes;
5. an assay that can fail;
6. a control distinguishing mechanism from software/presentation artifacts.

## Tests

At minimum:

```bash
python -m pip install -e '.[dev]'
pytest
ruff check .
mypy src/flybox
```

Tests requiring downloaded datasets must be opt-in and clearly marked so the unit suite remains runnable from a clean checkout.

## Commits and PRs

Prefer small vertical changes with evidence and tests in the same PR. Architecture decisions that constrain multiple modules belong in `docs/adr/`.

A feature is not complete merely because a fly visibly moves. The relevant acceptance metric and control must pass.
