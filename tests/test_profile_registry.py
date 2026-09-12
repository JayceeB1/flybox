from __future__ import annotations

import json
from pathlib import Path

import pytest

from flybox.config import CanonicalConfigError, ProfileKind, ProfileRegistry, ProfileRegistryError
from flybox.config.resolve import resolved_profile_dict, write_resolved_profile


PROFILE_HEADER = "schema: flybox.profile/v1\n"


def write_profile(root: Path, relative: str, body: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(PROFILE_HEADER + body, encoding="utf-8")
    return path


def test_semantically_equivalent_yaml_has_same_hash(tmp_path: Path) -> None:
    write_profile(
        tmp_path,
        "a.yaml",
        "kind: brain\nid: brain-a\nversion: 1\nconfig:\n  threshold_mv: -45\n  tau_ms: 20\n",
    )
    first = ProfileRegistry.from_directory(tmp_path).resolve("brain-a")

    (tmp_path / "a.yaml").write_text(
        PROFILE_HEADER
        + "version: 1\nid: brain-a\nkind: brain\nconfig:\n  tau_ms: 20\n  threshold_mv: -45\n",
        encoding="utf-8",
    )
    second = ProfileRegistry.from_directory(tmp_path).resolve("brain-a")
    assert first.profile_hash == second.profile_hash


def test_behavior_parameter_change_changes_hash(tmp_path: Path) -> None:
    path = write_profile(
        tmp_path,
        "brain.yaml",
        "kind: brain\nid: brain-a\nversion: 1\nconfig:\n  threshold_mv: -45\n",
    )
    first = ProfileRegistry.from_directory(tmp_path).resolve("brain-a")
    path.write_text(
        PROFILE_HEADER + "kind: brain\nid: brain-a\nversion: 1\nconfig:\n  threshold_mv: -44\n",
        encoding="utf-8",
    )
    second = ProfileRegistry.from_directory(tmp_path).resolve("brain-a")
    assert first.profile_hash != second.profile_hash


def test_defaults_are_expanded_before_hashing(tmp_path: Path) -> None:
    write_profile(
        tmp_path,
        "runtime.yaml",
        "kind: scheduler\nid: scheduler-v0\nversion: 1\n"
        "defaults:\n  control_ms: 20\n  nested:\n    a: 1\n    b: 2\n"
        "config:\n  nested:\n    b: 3\n",
    )
    resolved = ProfileRegistry.from_directory(tmp_path).resolve("scheduler-v0")
    assert resolved.config == {"control_ms": 20, "nested": {"a": 1, "b": 3}}


def test_references_are_resolved_and_hashed(tmp_path: Path) -> None:
    write_profile(
        tmp_path,
        "brain.yaml",
        "kind: brain\nid: brain-a\nversion: 1\nconfig:\n  threshold_mv: -45\n",
    )
    write_profile(
        tmp_path,
        "experiment.yaml",
        "kind: experiment\nid: exp-a\nversion: 1\nreferences:\n  brain: brain-a\nconfig:\n  duration_s: 1\n",
    )
    registry = ProfileRegistry.from_directory(tmp_path)
    brain = registry.resolve("brain-a")
    experiment = registry.resolve("exp-a")
    assert experiment.references[0].profile_id == "brain-a"
    assert experiment.references[0].profile_hash == brain.profile_hash


def test_unknown_key_fails_closed(tmp_path: Path) -> None:
    write_profile(
        tmp_path,
        "bad.yaml",
        "kind: brain\nid: brain-a\nversion: 1\nconfig: {}\nsecret_default: 12\n",
    )
    with pytest.raises(ProfileRegistryError, match="unknown top-level keys"):
        ProfileRegistry.from_directory(tmp_path)


def test_missing_reference_and_cycle_fail(tmp_path: Path) -> None:
    write_profile(
        tmp_path,
        "a.yaml",
        "kind: experiment\nid: a\nversion: 1\nreferences:\n  other: b\nconfig: {}\n",
    )
    registry = ProfileRegistry.from_directory(tmp_path)
    with pytest.raises(ProfileRegistryError, match="unknown profile id 'b'"):
        registry.resolve("a")

    write_profile(
        tmp_path,
        "b.yaml",
        "kind: experiment\nid: b\nversion: 1\nreferences:\n  other: a\nconfig: {}\n",
    )
    registry = ProfileRegistry.from_directory(tmp_path)
    with pytest.raises(ProfileRegistryError, match="profile reference cycle"):
        registry.resolve("a")


def test_environment_changes_do_not_affect_frozen_profile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    write_profile(
        tmp_path,
        "body.yaml",
        "kind: body\nid: body-a\nversion: 1\nconfig:\n  timestep_s: 0.0001\n",
    )
    registry = ProfileRegistry.from_directory(tmp_path)
    first = registry.resolve("body-a")
    monkeypatch.setenv("FLYBOX_TIMESTEP", "999")
    second = registry.resolve("body-a")
    assert first.profile_hash == second.profile_hash
    assert first.config == second.config


def test_biological_ids_must_be_decimal_strings(tmp_path: Path) -> None:
    write_profile(
        tmp_path,
        "bridge.yaml",
        "kind: motor_bridge\nid: motor-a\nversion: 1\nconfig:\n  neuron_ids: [720575940000000001]\n",
    )
    with pytest.raises(CanonicalConfigError, match="biological IDs must be decimal strings"):
        ProfileRegistry.from_directory(tmp_path).resolve("motor-a")


def test_all_v0_profile_kinds_are_supported(tmp_path: Path) -> None:
    for kind in ProfileKind:
        write_profile(
            tmp_path,
            f"{kind.value}.yaml",
            f"kind: {kind.value}\nid: {kind.value}-v0\nversion: 1\nconfig: {{}}\n",
        )
    resolved = ProfileRegistry.from_directory(tmp_path).resolve_all()
    assert {item.kind for item in resolved} == set(ProfileKind)


def test_resolved_profile_can_be_persisted(tmp_path: Path) -> None:
    write_profile(
        tmp_path,
        "brain.yaml",
        "kind: brain\nid: brain-a\nversion: 1\nconfig:\n  threshold_mv: -45\n",
    )
    profile = ProfileRegistry.from_directory(tmp_path).resolve("brain-a")
    output = tmp_path / "resolved" / "brain-a.json"
    write_resolved_profile(profile, output)
    stored = json.loads(output.read_text(encoding="utf-8"))
    assert stored == resolved_profile_dict(profile)
    assert stored["profile_hash"] == profile.profile_hash
