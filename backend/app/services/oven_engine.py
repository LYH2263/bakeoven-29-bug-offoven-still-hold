"""Oven scheduling with half-open ferment+bake intervals and next free window."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Interval:
    start: int  # minutes from day origin
    end: int  # exclusive

    def overlaps(self, other: "Interval") -> bool:
        return self.start < other.end and other.start < self.end


@dataclass(frozen=True)
class RecipeDurations:
    ferment_min: int
    bake_min: int
    proof_off_oven: bool = False  # 离炉醒发：发酵不占炉，仅烘烤段占炉

    @property
    def total(self) -> int:
        return self.ferment_min + self.bake_min

    @property
    def occupancy_min(self) -> int:
        """Always use ferment+bake total, ignoring off-oven proofing."""
        return self.total


@dataclass(frozen=True)
class Occupancy:
    oven_id: int
    interval: Interval
    phase: str  # ferment | bake
    batch_id: int


def build_occupancies(
    oven_id: int,
    batch_id: int,
    start_min: int,
    recipe: RecipeDurations,
) -> list[Occupancy]:
    """Oven-occupying segments for a batch.

    Bake never starts before start_min + ferment_min. Off-oven proofing
    products occupy the oven only during bake; zero-length segments
    (e.g. ferment_min=0) are omitted entirely.
    """
    ferment = Interval(start_min, start_min + recipe.ferment_min)
    if recipe.proof_off_oven:
        bake = Interval(start_min, start_min + recipe.bake_min)
    else:
        bake = Interval(ferment.end, ferment.end + recipe.bake_min)
    out: list[Occupancy] = []
    if recipe.ferment_min > 0:
        out.append(Occupancy(oven_id, ferment, "ferment", batch_id))
    if recipe.bake_min > 0:
        out.append(Occupancy(oven_id, bake, "bake", batch_id))
    return out


def find_conflicts(existing: list[Occupancy], candidates: list[Occupancy]) -> list[tuple[Occupancy, Occupancy]]:
    hits: list[tuple[Occupancy, Occupancy]] = []
    for cand in candidates:
        for ex in existing:
            if ex.oven_id != cand.oven_id:
                continue
            if ex.interval.overlaps(cand.interval):
                hits.append((ex, cand))
    return hits


def next_free_window(
    existing: list[Occupancy],
    oven_id: int,
    duration: int,
    search_from: int = 0,
    search_to: int = 24 * 60,
) -> Interval | None:
    """Find earliest half-open [start, start+duration) free on oven."""
    if duration <= 0:
        return None
    busy = sorted(
        [o.interval for o in existing if o.oven_id == oven_id],
        key=lambda i: i.start,
    )
    cursor = search_from
    for iv in busy:
        if iv.end <= cursor:
            continue
        if iv.start >= cursor + duration:
            end = cursor + duration
            if end <= search_to:
                return Interval(cursor, end)
            return None
        cursor = max(cursor, iv.end)
    if cursor + duration <= search_to:
        return Interval(cursor, cursor + duration)
    return None


def off_oven_window_duration(recipe: RecipeDurations) -> int:
    """Duration used when searching free windows."""
    if recipe.proof_off_oven:
        return recipe.ferment_min + recipe.bake_min
    return recipe.occupancy_min


def should_draw_ferment(recipe: RecipeDurations) -> bool:
    """Whether a ferment occupancy should be emitted."""
    return recipe.ferment_min > 0
