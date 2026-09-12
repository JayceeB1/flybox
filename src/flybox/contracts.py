"""Transport-agnostic contracts shared by FlyBox components.

These dataclasses intentionally contain no FlyGym, MuJoCo, MaleCNS, UE, or
network-transport imports. Adapters convert backend-native structures into these
stable contracts so scientific records stay readable when implementations change.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum


class EvidenceClass(StrEnum):
    """How a value or mapping entered the FlyBox scientific model."""

    MEASURED = "measured"
    INFERRED = "inferred"
    MODELED = "modeled"
    ENGINEERED = "engineered"
    DERIVED = "derived"


@dataclass(frozen=True, slots=True)
class ProvenanceRef:
    """A compact, serializable pointer to scientific or software provenance."""

    source: str
    version: str
    license_id: str
    evidence: EvidenceClass
    sha256: str | None = None
    locator: str | None = None
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class SimulationStamp:
    """Synchronized clocks for one accepted cross-component boundary."""

    sequence: int
    neural_time_ms: float
    body_time_s: float
    wall_time_s: float


@dataclass(frozen=True, slots=True)
class BodyObservation:
    """Normalized body state at the FlyBox bridge boundary.

    FlyBox bridge contracts use SI units even when a backend uses another native
    convention. Adapters are responsible for deterministic unit conversion.
    """

    stamp: SimulationStamp
    thorax_position_m: tuple[float, float, float]
    thorax_quaternion_wxyz: tuple[float, float, float, float]
    linear_velocity_m_s: tuple[float, float, float]
    angular_velocity_rad_s: tuple[float, float, float]
    joint_position_rad: Mapping[str, float] = field(default_factory=dict)
    joint_velocity_rad_s: Mapping[str, float] = field(default_factory=dict)
    contact_force_n: Mapping[str, tuple[float, float, float]] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SensoryDrive:
    """External drive applied to identified neural populations for one window."""

    duration_ms: float
    neuron_ids: Sequence[str]
    drive: Sequence[float]
    channel: str
    provenance: Sequence[ProvenanceRef] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class NeuralReadout:
    """Observed activity for identified neurons over a neural integration window."""

    stamp: SimulationStamp
    duration_ms: float
    neuron_ids: Sequence[str]
    spike_counts: Sequence[int]
    firing_rates_hz: Sequence[float]


@dataclass(frozen=True, slots=True)
class LocomotionCommand:
    """Temporary V0 high-level motor contract.

    This is explicitly an engineered bridge to the FlyGym locomotion controller;
    it is not presented as a measured biological motor representation.
    """

    forward_drive: float
    turn_drive: float
    reverse_drive: float = 0.0
    frequency_scale: float = 1.0
    stance_gain: float = 1.0


@dataclass(frozen=True, slots=True)
class ExperimentEvent:
    """Append-only record emitted by the experiment runner."""

    stamp: SimulationStamp
    kind: str
    payload: Mapping[str, object]
    provenance: Sequence[ProvenanceRef] = field(default_factory=tuple)
