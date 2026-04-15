"""Reusable test fixtures for the routing service.

Small, deterministic set of Paris landmarks plus helpers to build
caregivers and patient stops.
"""

from __future__ import annotations

from app.services.routing.models import Caregiver, Coordinate, PatientStop

# --------------------------------------------------------------------------- #
# Paris landmark coordinates (approx. WGS-84)
# --------------------------------------------------------------------------- #

EIFFEL_TOWER = Coordinate(lat=48.8584, lon=2.2945)
ARC_DE_TRIOMPHE = Coordinate(lat=48.8738, lon=2.2950)
LOUVRE = Coordinate(lat=48.8606, lon=2.3376)
BASTILLE = Coordinate(lat=48.8532, lon=2.3692)
MONTPARNASSE = Coordinate(lat=48.8422, lon=2.3219)
PERE_LACHAISE = Coordinate(lat=48.8614, lon=2.3933)

# Convenient clusters used by tests
PARIS_POIS: list[Coordinate] = [
    EIFFEL_TOWER,
    ARC_DE_TRIOMPHE,
    LOUVRE,
    BASTILLE,
    MONTPARNASSE,
    PERE_LACHAISE,
]

# A caregiver base near the geographic center (Châtelet-ish).
CAREGIVER_HOME_CENTER = Coordinate(lat=48.8580, lon=2.3470)
# A second base in the west (Trocadéro-ish) for multi-caregiver tests.
CAREGIVER_HOME_WEST = Coordinate(lat=48.8625, lon=2.2870)


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #


def make_caregiver(
    cg_id: int | str = 1,
    *,
    home: Coordinate = CAREGIVER_HOME_CENTER,
    capacity_minutes: int = 480,
    shift_start_minutes: int = 8 * 60,
    shift_end_minutes: int = 18 * 60,
) -> Caregiver:
    """Return a :class:`Caregiver` with sensible defaults."""
    return Caregiver(
        id=cg_id,
        home=home,
        capacity_minutes=capacity_minutes,
        shift_start_minutes=shift_start_minutes,
        shift_end_minutes=shift_end_minutes,
    )


def make_patient(
    pid: int | str,
    coord: Coordinate,
    *,
    service_minutes: float = 30.0,
    time_window: tuple[int, int] | None = None,
) -> PatientStop:
    """Return a :class:`PatientStop`."""
    return PatientStop(
        id=pid,
        coord=coord,
        service_minutes=service_minutes,
        time_window=time_window,
    )


__all__ = [
    "ARC_DE_TRIOMPHE",
    "BASTILLE",
    "CAREGIVER_HOME_CENTER",
    "CAREGIVER_HOME_WEST",
    "EIFFEL_TOWER",
    "LOUVRE",
    "MONTPARNASSE",
    "PARIS_POIS",
    "PERE_LACHAISE",
    "make_caregiver",
    "make_patient",
]
