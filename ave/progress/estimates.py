"""Honest time remaining.

Rates are seconds of wall clock per unit of work. A missing rate means the UI
must say "Estimating time…", never invent a number. Shown estimates are rounded
and may not jump up by more than 25% unless the caller names why.
"""

from __future__ import annotations

from dataclasses import dataclass

JUMP_LIMIT = 0.25


@dataclass
class RateBook:
    """Moving average of measured seconds per work unit, keyed by stage."""

    rates: dict[str, float]
    samples: dict[str, int]

    @classmethod
    def empty(cls) -> RateBook:
        return cls(rates={}, samples={})

    def observe(self, stage: str, units: float, elapsed_s: float) -> None:
        if units <= 0 or elapsed_s < 0:
            return
        measured = elapsed_s / units
        previous = self.rates.get(stage)
        count = self.samples.get(stage, 0)
        if previous is None or count == 0:
            self.rates[stage] = measured
            self.samples[stage] = 1
            return
        # Keep the last few runs heavier than the first calibration.
        weight = min(count, 8)
        self.rates[stage] = (previous * weight + measured) / (weight + 1)
        self.samples[stage] = count + 1

    def seconds_for(self, stage: str, units: float) -> float | None:
        rate = self.rates.get(stage)
        if rate is None or units < 0:
            return None
        return rate * units


def remaining_seconds(book: RateBook, remaining_by_stage: dict[str, float]) -> float | None:
    total = 0.0
    any_known = False
    for stage, units in remaining_by_stage.items():
        seconds = book.seconds_for(stage, units)
        if seconds is None:
            continue
        any_known = True
        total += seconds
    return total if any_known else None


def round_remaining(seconds: float | None) -> str:
    if seconds is None:
        return "Estimating time…"
    if seconds < 45:
        return "less than a minute left"
    minutes = max(1, round(seconds / 60))
    if minutes == 1:
        return "about 1 min left"
    return f"about {minutes} min left"


def smooth_remaining(previous_s: float | None, computed_s: float | None, *, why: str = "") -> tuple[float | None, str]:
    """Hold a jump above 25% unless a reason is given.

    Returns the value to show and a revision note. An empty note means the
    estimate did not need explaining.
    """
    if computed_s is None:
        return previous_s, ""
    if previous_s is None or previous_s <= 0:
        return computed_s, ""
    if computed_s <= previous_s * (1 + JUMP_LIMIT):
        return computed_s, ""
    if why.strip():
        return computed_s, why.strip()
    return previous_s * (1 + JUMP_LIMIT), ""


def within_tolerance(shown_s: float, actual_remaining_s: float, tolerance: float = 0.20) -> bool:
    if actual_remaining_s <= 0:
        return shown_s <= 1
    return abs(shown_s - actual_remaining_s) / actual_remaining_s <= tolerance
