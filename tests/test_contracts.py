from flybox.contracts import EvidenceClass, LocomotionCommand, ProvenanceRef, SimulationStamp


def test_evidence_classes_are_stable_strings() -> None:
    assert [item.value for item in EvidenceClass] == [
        "measured",
        "inferred",
        "modeled",
        "engineered",
        "derived",
    ]


def test_provenance_ref_keeps_biological_locator_as_text() -> None:
    ref = ProvenanceRef(
        source="MaleCNS",
        version="v1.0",
        license_id="CC-BY-4.0",
        evidence=EvidenceClass.MEASURED,
        locator="body:720575940000000001",
    )
    assert ref.locator == "body:720575940000000001"


def test_simulation_stamp_keeps_clocks_independent() -> None:
    stamp = SimulationStamp(sequence=7, neural_time_ms=12.5, body_time_s=0.020, wall_time_s=0.031)
    assert stamp.neural_time_ms == 12.5
    assert stamp.body_time_s == 0.020
    assert stamp.wall_time_s == 0.031


def test_v0_motor_command_is_explicit_high_level_bridge() -> None:
    command = LocomotionCommand(forward_drive=0.8, turn_drive=-0.2)
    assert command.forward_drive == 0.8
    assert command.turn_drive == -0.2
    assert command.frequency_scale == 1.0
