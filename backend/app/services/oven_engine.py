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
        """真实占炉时长：离炉醒发只占烘烤段，否则发酵+烘烤。"""
        if self.proof_off_oven:
            return self.bake_min
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
    products occupy the oven only during bake (which still starts after
    fermentation elapses); zero-length segments are omitted entirely.
    """
    ferment_end = start_min + recipe.ferment_min
    bake = Interval(ferment_end, ferment_end + recipe.bake_min)
    out: list[Occupancy] = []
    if not recipe.proof_off_oven and recipe.ferment_min > 0:
        out.append(Occupancy(oven_id, Interval(start_min, ferment_end), "ferment", batch_id))
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


def plan_work_window(
    existing: list[Occupancy],
    oven_id: int,
    recipe: RecipeDurations,
    day_start: int = 8 * 60,
    day_end: int = 22 * 60,
) -> Interval | None:
    """Earliest feasible 开工窗口，返回 [开工时刻, 离炉时刻)。

    空档搜索按真实占炉时长（离炉产品仅烘烤分钟）进行；离炉产品的
    入炉时刻 = 开工 + 发酵，故入炉空档从 day_start+发酵 起搜，再把
    开工时刻前移发酵分钟。离炉时刻即区间止点，可与批次止点对账。
    """
    ferment_shift = recipe.ferment_min if recipe.proof_off_oven else 0
    slot = next_free_window(
        existing,
        oven_id,
        recipe.occupancy_min,
        search_from=day_start + ferment_shift,
        search_to=day_end,
    )
    if slot is None:
        return None
    return Interval(slot.start - ferment_shift, slot.end)
