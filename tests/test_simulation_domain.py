from src.simulation import (
    CenterScenario,
    OrderDemand,
    SimulationOptions,
    build_order_candidates,
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
        CenterScenario("C1", "Alpha", 35.6895, 139.6917, 1.0, 1, 1000),
        CenterScenario("C2", "Beta", 35.7, 139.8, 1.0, 1, 2000),
    ]
    orders = [
        OrderDemand("O1", 35.6896, 139.6918, 1.0, 1),
        OrderDemand("O2", 35.6897, 139.6919, 1.0, 1),
    ]

    result = simulate_assignments(orders=orders, centers=centers, options=options)

    assert [assignment.center_name for assignment in result.assignments] == ["Alpha", "Beta"]
    assert result.center_summaries[0].assigned_orders == 1
    assert result.center_summaries[1].assigned_orders == 1
    assert result.total_fixed_cost == 3000


def test_simulate_assignments_is_deterministic_on_tie_and_counts_overflow():
    options = SimulationOptions(orders_per_staff=1)
    centers = [
        CenterScenario("C1", "Alpha", 35.0, 139.0, 1.0, 0, 500),
        CenterScenario("C2", "Beta", 35.0, 139.0, 1.0, 0, 700),
    ]
    orders = [OrderDemand("O1", 35.0, 139.0, 1.0, 1)]

    result = simulate_assignments(orders=orders, centers=centers, options=options)

    assert result.assignments[0].center_name == "Alpha"
    assert result.assignments[0].capacity_exceeded is True
    assert result.center_summaries[0].overflow_orders == 1
    assert result.total_cost == result.total_fixed_cost + result.total_variable_cost
