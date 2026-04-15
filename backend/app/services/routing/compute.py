"""Pathology-weighted service time computation.

This module converts a patient's list of pathologies (plus per-care
overrides) into a single service duration in minutes. It is deliberately
kept free of ORM / schema types — it takes plain mappings.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import TypedDict

DEFAULT_MIN_MINUTES: float = 10.0


class PathologyItem(TypedDict, total=False):
    """Shape expected by :func:`compute_patient_minutes`.

    Keys:
        base_minutes: Default ``pathology.base_care_minutes`` (required).
        coefficient: Default ``pathology.weight_coefficient`` (required).
        override_minutes: Per-care override of base minutes (optional).
        override_coefficient: Per-care override of coefficient (optional).
    """

    base_minutes: float
    coefficient: float
    override_minutes: float | None
    override_coefficient: float | None


def compute_patient_minutes(
    items: Iterable[PathologyItem],
    *,
    floor_minutes: float = DEFAULT_MIN_MINUTES,
) -> float:
    """Return the total estimated care duration in minutes.

    Formula::

        duration = Σ  (override_minutes OR base_minutes)
                     * (override_coefficient OR coefficient)

    If no pathology is provided, the function returns ``floor_minutes``.
    The result is clamped to ``floor_minutes`` even when the formula
    would yield a smaller value, to guarantee a realistic minimum.
    """
    total = 0.0
    count = 0
    for item in items:
        count += 1
        base = item.get("override_minutes")
        if base is None:
            base = item["base_minutes"]
        coef = item.get("override_coefficient")
        if coef is None:
            coef = item["coefficient"]
        total += float(base) * float(coef)

    if count == 0:
        return floor_minutes
    return max(total, floor_minutes)
