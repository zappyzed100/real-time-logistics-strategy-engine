from src.simulation import (
    CENTER_POPULATION_DENSITY,
    SIMULATION_CONSTANTS,
    CenterScenario,
    OrderCandidate,
    OrderDemand,
    SimulationOptions,
    center_population_density,
    load_simulation_constants,
    simulate_assignments,
)


def make_ranked_candidates() -> list[OrderCandidate]:
    return [
        OrderCandidate("O1", "13", "東京", 4.0, 100.0, 1.0, center_candidate_rank=1, order_candidate_rank=1),
        OrderCandidate("O2", "13", "東京", 5.0, 200.0, 1.0, center_candidate_rank=2, order_candidate_rank=2),
        OrderCandidate("O1", "27", "大阪", 6.0, 300.0, 1.0, center_candidate_rank=1, order_candidate_rank=2),
        OrderCandidate("O2", "27", "大阪", 7.0, 150.0, 1.0, center_candidate_rank=2, order_candidate_rank=1),
    ]


def test_simulate_assignments_uses_staff_capacity_before_falling_back():
    options = SimulationOptions(orders_per_staff=1)
    centers = [
        CenterScenario("13", "東京", 35.6895, 139.6917, 1.0, 1, 1000),
        CenterScenario("27", "大阪", 35.7, 139.8, 1.0, 1, 2000),
    ]
    orders = [
        OrderDemand("O1", 35.6896, 139.6918, 1.0, 1),
        OrderDemand("O2", 35.6897, 139.6919, 1.0, 1),
    ]

    result = simulate_assignments(orders=orders, centers=centers, candidates=make_ranked_candidates(), options=options)

    assert [assignment.center_name for assignment in result.assignments] == ["東京", "大阪"]
    assert result.center_summaries[0].assigned_orders == 1
    assert result.center_summaries[0].labor_cost == 500000.0
    assert result.center_summaries[1].assigned_orders == 1
    assert result.total_fixed_cost == 3000
    assert result.total_labor_cost == 1000000.0
    assert result.total_cost == result.total_fixed_cost + result.total_labor_cost + result.total_variable_cost


def test_center_population_density_returns_hardcoded_density():
    assert center_population_density("東京") == CENTER_POPULATION_DENSITY["東京"]
    assert center_population_density("未定義") == 0.0


def test_load_simulation_constants_returns_externalized_values():
    constants = load_simulation_constants()

    assert constants == SIMULATION_CONSTANTS
    assert constants["orders_per_staff"] == 20
    assert constants["labor_cost_per_staff"] == 500000.0
    assert constants["staffing_round_increment"] == 1


def test_simulate_assignments_prefers_high_density_center_first_on_tie():
    options = SimulationOptions(orders_per_staff=1)
    centers = [
        CenterScenario("1", "北海道", 35.0, 139.0, 1.0, 1, 500),
        CenterScenario("13", "東京", 35.0, 139.0, 1.0, 1, 700),
    ]
    orders = [OrderDemand("O1", 35.0, 139.0, 1.0, 1)]

    candidates = [
        OrderCandidate("O1", "1", "北海道", 1.0, 200.0, 1.0, center_candidate_rank=1, order_candidate_rank=2),
        OrderCandidate("O1", "13", "東京", 1.0, 200.0, 1.0, center_candidate_rank=1, order_candidate_rank=1),
    ]

    result = simulate_assignments(orders=orders, centers=centers, candidates=candidates, options=options)

    assert result.assignments[0].center_name == "東京"
    assert result.assignments[0].capacity_exceeded is False
    assert result.total_labor_cost == 1000000.0
    assert result.total_cost == result.total_fixed_cost + result.total_labor_cost + result.total_variable_cost


def test_simulate_assignments_uses_staffing_round_increment_chunks():
    options = SimulationOptions(orders_per_staff=2, staffing_round_increment=2)
    centers = [
        CenterScenario("13", "東京", 35.0, 139.0, 1.0, 3, 0),
        CenterScenario("27", "大阪", 36.0, 140.0, 1.0, 0, 0),
    ]
    orders = [OrderDemand(f"O{i}", 35.0, 139.0, 1.0, 1) for i in range(1, 7)]

    candidates = [
        OrderCandidate(f"O{i}", "13", "東京", float(i), float(100 + i), 1.0, center_candidate_rank=i, order_candidate_rank=1)
        for i in range(1, 7)
    ] + [
        OrderCandidate(
            f"O{i}", "27", "大阪", float(10 + i), float(200 + i), 1.0, center_candidate_rank=i, order_candidate_rank=2
        )
        for i in range(1, 7)
    ]

    result = simulate_assignments(orders=orders, centers=centers, candidates=candidates, options=options)

    assigned_to_tokyo = [assignment for assignment in result.assignments if assignment.center_name == "東京"]
    unassigned = [assignment for assignment in result.assignments if assignment.is_unassigned]
    assert len(assigned_to_tokyo) == 6
    assert len(unassigned) == 0


def test_simulate_assignments_marks_unassigned_orders_with_penalty_cost():
    options = SimulationOptions(orders_per_staff=1)
    centers = [
        CenterScenario("13", "東京", 35.0, 139.0, 1.0, 0, 500),
        CenterScenario("27", "大阪", 35.0, 139.0, 1.2, 0, 700),
    ]
    orders = [OrderDemand("O1", 35.0, 139.0, 1.0, 1)]

    candidates = [
        OrderCandidate("O1", "13", "東京", 1.0, 100.0, 1.0, center_candidate_rank=1, order_candidate_rank=1),
        OrderCandidate("O1", "27", "大阪", 1.0, 120.0, 1.0, center_candidate_rank=1, order_candidate_rank=2),
    ]

    result = simulate_assignments(orders=orders, centers=centers, candidates=candidates, options=options)

    assert result.assignments[0].center_name is None
    assert result.assignments[0].capacity_exceeded is True
    assert result.assignments[0].is_unassigned is True
    assert result.assignments[0].fallback_center_name == "東京"
    assert result.unassigned_order_count == 1
    assert result.unassigned_total_cost == result.total_variable_cost
    assert result.total_labor_cost == 0.0
    assert result.total_cost == result.total_fixed_cost + result.total_labor_cost + result.total_variable_cost


def test_simulate_assignments_uses_precomputed_ranked_candidates_without_re_sorting():
    options = SimulationOptions(orders_per_staff=1)
    centers = [
        CenterScenario("13", "東京", 35.0, 139.0, 1.0, 1, 0),
        CenterScenario("27", "大阪", 35.0, 139.0, 1.0, 1, 0),
    ]
    orders = [
        OrderDemand("O1", 35.0, 139.0, 1.0, 1),
        OrderDemand("O2", 35.0, 139.0, 1.0, 1),
    ]
    candidates = [
        OrderCandidate("O1", "13", "東京", 4.0, 100.0, 1.0, center_candidate_rank=1, order_candidate_rank=1),
        OrderCandidate("O2", "13", "東京", 5.0, 200.0, 1.0, center_candidate_rank=2, order_candidate_rank=1),
        OrderCandidate("O1", "27", "大阪", 6.0, 300.0, 1.0, center_candidate_rank=1, order_candidate_rank=2),
        OrderCandidate("O2", "27", "大阪", 7.0, 400.0, 1.0, center_candidate_rank=2, order_candidate_rank=2),
    ]

    result = simulate_assignments(orders=orders, centers=centers, candidates=candidates, options=options)

    assert [assignment.center_name for assignment in result.assignments] == ["東京", "大阪"]
    assert result.assignments[1].delivery_cost == 400.0


def test_simulate_assignments_requires_precomputed_candidates():
    centers = [CenterScenario("13", "東京", 35.0, 139.0, 1.0, 1, 0)]
    orders = [OrderDemand("O1", 35.0, 139.0, 1.0, 1)]

    try:
        simulate_assignments(orders=orders, centers=centers, candidates=[])
    except ValueError as exc:
        assert str(exc) == "precomputed candidates are required"
    else:
        raise AssertionError("ValueError was not raised")


def test_simulate_assignments_requires_candidate_ranks():
    centers = [CenterScenario("13", "東京", 35.0, 139.0, 1.0, 1, 0)]
    orders = [OrderDemand("O1", 35.0, 139.0, 1.0, 1)]
    candidates = [OrderCandidate("O1", "13", "東京", 1.0, 100.0, 1.0)]

    try:
        simulate_assignments(orders=orders, centers=centers, candidates=candidates)
    except ValueError as exc:
        assert str(exc) == "precomputed candidates must include center_candidate_rank and order_candidate_rank"
    else:
        raise AssertionError("ValueError was not raised")


def test_simulate_assignments_requires_primary_order_rank():
    centers = [CenterScenario("13", "東京", 35.0, 139.0, 1.0, 0, 0)]
    orders = [OrderDemand("O1", 35.0, 139.0, 1.0, 1)]
    candidates = [OrderCandidate("O1", "13", "東京", 1.0, 100.0, 1.0, center_candidate_rank=1, order_candidate_rank=2)]

    try:
        simulate_assignments(orders=orders, centers=centers, candidates=candidates)
    except ValueError as exc:
        assert str(exc) == "missing order_candidate_rank=1 for orders: O1"
    else:
        raise AssertionError("ValueError was not raised")
