from app.services.oven_engine import (
    Interval,
    Occupancy,
    RecipeDurations,
    build_occupancies,
    find_conflicts,
    next_free_window,
    plan_work_window,
)


def test_half_open_no_touch_conflict():
    a = Occupancy(1, Interval(0, 30), "bake", 1)
    b = Occupancy(1, Interval(30, 60), "bake", 2)
    assert find_conflicts([a], [b]) == []


def test_overlap_detected():
    recipe = RecipeDurations(20, 30)
    cand = build_occupancies(1, 9, 10, recipe)
    existing = [Occupancy(1, Interval(25, 40), "bake", 1)]
    assert find_conflicts(existing, cand)


def test_next_free_window_after_busy():
    existing = [
        Occupancy(1, Interval(0, 40), "ferment", 1),
        Occupancy(1, Interval(40, 70), "bake", 1),
    ]
    w = next_free_window(existing, 1, duration=30, search_from=0)
    assert w == Interval(70, 100)


def test_next_free_in_gap():
    existing = [
        Occupancy(1, Interval(0, 20), "bake", 1),
        Occupancy(1, Interval(80, 100), "bake", 2),
    ]
    w = next_free_window(existing, 1, duration=30, search_from=0)
    assert w == Interval(20, 50)


def test_default_recipe_two_segments():
    occ = build_occupancies(1, 7, 100, RecipeDurations(20, 30))
    assert occ == [
        Occupancy(1, Interval(100, 120), "ferment", 7),
        Occupancy(1, Interval(120, 150), "bake", 7),
    ]


def test_off_oven_proof_only_bake_segment():
    recipe = RecipeDurations(40, 35, proof_off_oven=True)
    assert build_occupancies(1, 7, 540, recipe) == [
        Occupancy(1, Interval(580, 615), "bake", 7),
    ]


def test_off_oven_bake_not_before_ferment_end():
    # 烘烤起点仍不得早于开工分钟 + 发酵分钟
    (bake,) = build_occupancies(1, 7, 480, RecipeDurations(50, 20, proof_off_oven=True))
    assert bake.interval.start == 480 + 50


def test_zero_ferment_only_bake_segment():
    # 布朗尼：发酵 0 分钟，未标明离炉也只有烘烤段
    assert build_occupancies(2, 3, 600, RecipeDurations(0, 30)) == [
        Occupancy(2, Interval(600, 630), "bake", 3),
    ]


def test_flag_off_restores_two_segments():
    on = build_occupancies(1, 1, 0, RecipeDurations(20, 30, proof_off_oven=True))
    off = build_occupancies(1, 1, 0, RecipeDurations(20, 30, proof_off_oven=False))
    assert [o.phase for o in on] == ["bake"]
    assert [o.phase for o in off] == ["ferment", "bake"]


def test_off_oven_bake_fits_gap_left_by_ferment():
    # 已有批次发酵占 [0,40)；离炉批次 10 分开工、发酵 30，烘烤 [40,60) 恰好接上
    existing = [Occupancy(1, Interval(0, 40), "ferment", 1)]
    cand = build_occupancies(1, 9, 10, RecipeDurations(30, 20, proof_off_oven=True))
    assert find_conflicts(existing, cand) == []


def test_occupancy_min_used_for_window_search():
    assert RecipeDurations(40, 35).occupancy_min == 75
    assert RecipeDurations(40, 35, proof_off_oven=True).occupancy_min == 35
    # 离炉产品只按烘烤分钟找空档：40 分钟空档放不下 75，放得下 35
    existing = [Occupancy(1, Interval(40, 1440), "bake", 1)]
    assert next_free_window(existing, 1, RecipeDurations(40, 35).occupancy_min) is None
    w = next_free_window(existing, 1, RecipeDurations(40, 35, proof_off_oven=True).occupancy_min)
    assert w == Interval(0, 35)


def test_plan_window_off_oven_uses_bake_only():
    # 08:00 起；[08:00,08:40) 与 [09:15,22:00) 被占，仅剩 35 分钟入炉空档
    # 离炉（发酵40/烘烤35）放得下：08:00 开工、08:40 入炉；普通产品（合计75）放不下
    busy = [
        Occupancy(1, Interval(480, 520), "bake", 1),
        Occupancy(1, Interval(555, 1320), "bake", 2),
    ]
    assert plan_work_window(busy, 1, RecipeDurations(40, 35, proof_off_oven=True)) == Interval(480, 555)
    assert plan_work_window(busy, 1, RecipeDurations(40, 35)) is None


def test_plan_window_off_oven_shift_is_ferment():
    # 空炉：08:00 开工 → 08:40 入炉、09:15 离炉
    w = plan_work_window([], 1, RecipeDurations(40, 35, proof_off_oven=True))
    assert w == Interval(480, 555)
    # 按窗口开工排产：烘烤段恰好落在搜到的空档，离炉止点=窗口止点
    (bake,) = build_occupancies(1, 7, w.start, RecipeDurations(40, 35, proof_off_oven=True))
    assert bake.interval == Interval(520, 555)
    assert bake.interval.end == w.end


def test_plan_window_non_off_spans_total():
    assert plan_work_window([], 1, RecipeDurations(40, 35)) == Interval(480, 555)


def test_plan_window_zero_ferment_brownie():
    assert plan_work_window([], 2, RecipeDurations(0, 30)) == Interval(480, 510)
    assert plan_work_window([], 2, RecipeDurations(0, 30, proof_off_oven=True)) == Interval(480, 510)
