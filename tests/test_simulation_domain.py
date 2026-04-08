from src.simulation import (
    CENTER_POPULATION_DENSITY,
    CenterScenario,
    OrderDemand,
    SimulationOptions,
    build_order_candidates,
    center_population_density,
    haversine_distance_km,
    simulate_assignments,
)


def test_haversine_distance_km_returns_zero_for_same_point():
    assert haversine_distance_km(35.0, 139.0, 35.0, 139.0) == 0.0


def test_build_order_candidates_returns_all_order_center_pairs():
    centers = [
        CenterScenario("C1", "Tokyo", 35.6895, 139.6917, 1.5, 2, 1000),
        CenterScenario("C2", "Osaka", 34.6937, 135.5023, 1.2, 1, 800),
    ]
    orders = [
        OrderDemand("O1", 35.68, 139.76, 2.0, 1),
        OrderDemand("O2", 34.70, 135.50, 3.0, 2),
    ]

    candidates = build_order_candidates(orders=orders, centers=centers)

    assert len(candidates) == 4
    assert {candidate.order_id for candidate in candidates} == {"O1", "O2"}
    assert {candidate.center_name for candidate in candidates} == {"Tokyo", "Osaka"}


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

    result = simulate_assignments(orders=orders, centers=centers, options=options)

    assert [assignment.center_name for assignment in result.assignments] == ["東京", "大阪"]
    assert result.center_summaries[0].assigned_orders == 1
    assert result.center_summaries[1].assigned_orders == 1
    assert result.total_fixed_cost == 3000


def test_center_population_density_returns_hardcoded_density():
    assert center_population_density("東京") == CENTER_POPULATION_DENSITY["東京"]
    assert center_population_density("未定義") == 0.0


def test_simulate_assignments_prefers_high_density_center_first_on_tie():
    options = SimulationOptions(orders_per_staff=1)
    centers = [
        CenterScenario("1", "北海道", 35.0, 139.0, 1.0, 1, 500),
        CenterScenario("13", "東京", 35.0, 139.0, 1.0, 1, 700),
    ]
    orders = [OrderDemand("O1", 35.0, 139.0, 1.0, 1)]

    result = simulate_assignments(orders=orders, centers=centers, options=options)

    assert result.assignments[0].center_name == "東京"
    assert result.assignments[0].capacity_exceeded is False
    assert result.total_cost == result.total_fixed_cost + result.total_variable_cost


def test_simulate_assignments_marks_unassigned_orders_with_penalty_cost():
    options = SimulationOptions(orders_per_staff=1)
    centers = [
        CenterScenario("13", "東京", 35.0, 139.0, 1.0, 0, 500),
        CenterScenario("27", "大阪", 35.0, 139.0, 1.2, 0, 700),
    ]
    orders = [OrderDemand("O1", 35.0, 139.0, 1.0, 1)]

    result = simulate_assignments(orders=orders, centers=centers, options=options)

    assert result.assignments[0].center_name is None
    assert result.assignments[0].capacity_exceeded is True
    assert result.assignments[0].is_unassigned is True
    assert result.assignments[0].fallback_center_name == "東京"
    assert result.unassigned_order_count == 1
    assert result.unassigned_total_cost == result.total_variable_cost
    assert result.total_cost == result.total_fixed_cost + result.total_variable_cost
