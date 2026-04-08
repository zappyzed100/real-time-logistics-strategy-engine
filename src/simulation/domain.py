from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt


@dataclass(frozen=True, slots=True)
class SimulationOptions:
    base_delivery_fee: float = 600.0
    distance_rate_per_km: float = 12.0
    weight_exponent: float = 0.6
    weight_divisor: float = 12.0
    max_weight_surcharge: float = 1.2
    orders_per_staff: int = 250

    def __post_init__(self) -> None:
        if self.orders_per_staff <= 0:
            raise ValueError("orders_per_staff must be positive")
        if self.distance_rate_per_km < 0:
            raise ValueError("distance_rate_per_km must be non-negative")
        if self.weight_divisor <= 0:
            raise ValueError("weight_divisor must be positive")


@dataclass(frozen=True, slots=True)
class CenterScenario:
    center_id: str
    center_name: str
    latitude: float
    longitude: float
    shipping_cost: float
    staffing_level: int
    fixed_cost: float

    def capacity(self, options: SimulationOptions) -> int:
        return max(self.staffing_level, 0) * options.orders_per_staff


@dataclass(frozen=True, slots=True)
class OrderDemand:
    order_id: str
    customer_lat: float
    customer_lon: float
    weight_kg: float
    quantity: int

    @property
    def total_weight_kg(self) -> float:
        return self.weight_kg * self.quantity


@dataclass(frozen=True, slots=True)
class OrderCandidate:
    order_id: str
    center_id: str
    center_name: str
    distance_km: float
    delivery_cost: float
    total_weight_kg: float


@dataclass(frozen=True, slots=True)
class OrderAssignment:
    order_id: str
    center_id: str
    center_name: str
    distance_km: float
    delivery_cost: float
    capacity_exceeded: bool


@dataclass(frozen=True, slots=True)
class CenterSummary:
    center_id: str
    center_name: str
    staffing_level: int
    capacity: int
    assigned_orders: int
    overflow_orders: int
    fixed_cost: float
    variable_cost: float
    total_cost: float


@dataclass(frozen=True, slots=True)
class SimulationResult:
    assignments: tuple[OrderAssignment, ...]
    center_summaries: tuple[CenterSummary, ...]
    total_fixed_cost: float
    total_variable_cost: float
    total_cost: float


def haversine_distance_km(
    origin_lat: float,
    origin_lon: float,
    destination_lat: float,
    destination_lon: float,
) -> float:
    radius_km = 6371.0
    lat_delta = radians((destination_lat - origin_lat) / 2)
    lon_delta = radians((destination_lon - origin_lon) / 2)
    a_value = power_sin(lat_delta) + cos(radians(origin_lat)) * cos(radians(destination_lat)) * power_sin(lon_delta)
    return radius_km * 2 * asin(sqrt(a_value))


def power_sin(angle_radians: float) -> float:
    return sin(angle_radians) ** 2


def calculate_delivery_cost(
    order: OrderDemand,
    center: CenterScenario,
    options: SimulationOptions = SimulationOptions(),
) -> float:
    distance_km = haversine_distance_km(
        origin_lat=order.customer_lat,
        origin_lon=order.customer_lon,
        destination_lat=center.latitude,
        destination_lon=center.longitude,
    )
    weight_multiplier = 1 + min(
        (order.total_weight_kg**options.weight_exponent) / options.weight_divisor, options.max_weight_surcharge
    )
    return round(
        (options.base_delivery_fee + distance_km * options.distance_rate_per_km) * center.shipping_cost * weight_multiplier, 2
    )


def build_order_candidates(
    orders: list[OrderDemand],
    centers: list[CenterScenario],
    options: SimulationOptions = SimulationOptions(),
) -> list[OrderCandidate]:
    candidates: list[OrderCandidate] = []
    for order in orders:
        for center in centers:
            candidates.append(
                OrderCandidate(
                    order_id=order.order_id,
                    center_id=center.center_id,
                    center_name=center.center_name,
                    distance_km=haversine_distance_km(
                        origin_lat=order.customer_lat,
                        origin_lon=order.customer_lon,
                        destination_lat=center.latitude,
                        destination_lon=center.longitude,
                    ),
                    delivery_cost=calculate_delivery_cost(order=order, center=center, options=options),
                    total_weight_kg=order.total_weight_kg,
                )
            )
    return candidates


def simulate_assignments(
    orders: list[OrderDemand],
    centers: list[CenterScenario],
    options: SimulationOptions = SimulationOptions(),
) -> SimulationResult:
    if not centers:
        raise ValueError("at least one center is required")

    candidates_by_order: dict[str, list[OrderCandidate]] = defaultdict(list)
    for candidate in build_order_candidates(orders=orders, centers=centers, options=options):
        candidates_by_order[candidate.order_id].append(candidate)

    remaining_capacity = {center.center_id: center.capacity(options) for center in centers}
    variable_cost_by_center = defaultdict(float)
    assigned_orders_by_center = defaultdict(int)
    overflow_orders_by_center = defaultdict(int)
    assignments: list[OrderAssignment] = []

    for order in sorted(orders, key=lambda current: current.order_id):
        ranked_candidates = sorted(
            candidates_by_order[order.order_id],
            key=lambda candidate: (candidate.delivery_cost, candidate.center_name, candidate.center_id),
        )
        selected = next(
            (candidate for candidate in ranked_candidates if remaining_capacity[candidate.center_id] > 0), ranked_candidates[0]
        )
        capacity_exceeded = remaining_capacity[selected.center_id] <= 0
        if not capacity_exceeded:
            remaining_capacity[selected.center_id] -= 1
        else:
            overflow_orders_by_center[selected.center_id] += 1

        assigned_orders_by_center[selected.center_id] += 1
        variable_cost_by_center[selected.center_id] += selected.delivery_cost
        assignments.append(
            OrderAssignment(
                order_id=selected.order_id,
                center_id=selected.center_id,
                center_name=selected.center_name,
                distance_km=selected.distance_km,
                delivery_cost=selected.delivery_cost,
                capacity_exceeded=capacity_exceeded,
            )
        )

    center_summaries = tuple(
        CenterSummary(
            center_id=center.center_id,
            center_name=center.center_name,
            staffing_level=center.staffing_level,
            capacity=center.capacity(options),
            assigned_orders=assigned_orders_by_center[center.center_id],
            overflow_orders=overflow_orders_by_center[center.center_id],
            fixed_cost=center.fixed_cost,
            variable_cost=round(variable_cost_by_center[center.center_id], 2),
            total_cost=round(variable_cost_by_center[center.center_id] + center.fixed_cost, 2),
        )
        for center in sorted(centers, key=lambda current: (current.center_name, current.center_id))
    )

    total_fixed_cost = round(sum(center.fixed_cost for center in centers), 2)
    total_variable_cost = round(sum(assignment.delivery_cost for assignment in assignments), 2)
    return SimulationResult(
        assignments=tuple(assignments),
        center_summaries=center_summaries,
        total_fixed_cost=total_fixed_cost,
        total_variable_cost=total_variable_cost,
        total_cost=round(total_fixed_cost + total_variable_cost, 2),
    )
