from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from math import asin, cos, radians, sin, sqrt
from pathlib import Path


@lru_cache(maxsize=1)
def load_simulation_constants() -> dict[str, float | int]:
    constants_path = Path(__file__).with_name("constants.json")
    with constants_path.open(encoding="utf-8") as constants_file:
        raw_constants = json.load(constants_file)
    return {
        "orders_per_staff": int(raw_constants["orders_per_staff"]),
        "labor_cost_per_staff": float(raw_constants["labor_cost_per_staff"]),
        "staffing_round_increment": int(raw_constants["staffing_round_increment"]),
        "unassigned_cost_multiplier": float(raw_constants["unassigned_cost_multiplier"]),
    }


SIMULATION_CONSTANTS = load_simulation_constants()
UNASSIGNED_COST_MULTIPLIER = float(SIMULATION_CONSTANTS["unassigned_cost_multiplier"])

# data/01_raw/estat/prefecture_population_density.csv を基に固定した人口密度。
CENTER_POPULATION_DENSITY = {
    "東京": 6410.4,
    "大阪": 4641.0,
    "神奈川": 3824.5,
    "埼玉": 1934.5,
    "愛知": 1458.7,
    "千葉": 1219.0,
    "福岡": 1030.6,
    "兵庫": 651.0,
    "沖縄": 643.3,
    "京都": 559.4,
    "香川": 506.7,
    "茨城": 470.5,
    "静岡": 467.4,
    "奈良": 359.1,
    "滋賀": 352.0,
    "佐賀": 332.7,
    "広島": 330.4,
    "長崎": 317.9,
    "宮城": 316.3,
    "三重": 306.8,
    "群馬": 305.0,
    "栃木": 301.8,
    "石川": 270.7,
    "岡山": 265.6,
    "富山": 243.8,
    "愛媛": 235.3,
    "熊本": 234.7,
    "山口": 219.7,
    "和歌山": 195.4,
    "岐阜": 186.4,
    "福井": 183.1,
    "山梨": 181.5,
    "大分": 177.4,
    "新潟": 175.0,
    "徳島": 173.6,
    "鹿児島": 173.0,
    "鳥取": 157.9,
    "長野": 151.1,
    "宮崎": 138.4,
    "福島": 133.1,
    "青森": 128.4,
    "山形": 114.6,
    "島根": 100.1,
    "高知": 97.4,
    "秋田": 82.5,
    "岩手": 79.3,
    "北海道": 66.7,
}


@dataclass(frozen=True, slots=True)
class SimulationOptions:
    base_delivery_fee: float = 600.0
    distance_rate_per_km: float = 12.0
    weight_exponent: float = 0.6
    weight_divisor: float = 12.0
    max_weight_surcharge: float = 1.2
    orders_per_staff: int = int(SIMULATION_CONSTANTS["orders_per_staff"])
    labor_cost_per_staff: float = float(SIMULATION_CONSTANTS["labor_cost_per_staff"])
    staffing_round_increment: int = int(SIMULATION_CONSTANTS["staffing_round_increment"])

    def __post_init__(self) -> None:
        if self.orders_per_staff <= 0:
            raise ValueError("orders_per_staff must be positive")
        if self.staffing_round_increment <= 0:
            raise ValueError("staffing_round_increment must be positive")
        if self.distance_rate_per_km < 0:
            raise ValueError("distance_rate_per_km must be non-negative")
        if self.weight_divisor <= 0:
            raise ValueError("weight_divisor must be positive")
        if self.labor_cost_per_staff < 0:
            raise ValueError("labor_cost_per_staff must be non-negative")


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
    center_candidate_rank: int | None = None
    order_candidate_rank: int | None = None


@dataclass(frozen=True, slots=True)
class OrderAssignment:
    order_id: str
    center_id: str | None
    center_name: str | None
    distance_km: float
    delivery_cost: float
    capacity_exceeded: bool
    is_unassigned: bool = False
    fallback_center_id: str | None = None
    fallback_center_name: str | None = None


@dataclass(frozen=True, slots=True)
class CenterSummary:
    center_id: str
    center_name: str
    staffing_level: int
    capacity: int
    assigned_orders: int
    overflow_orders: int
    fixed_cost: float
    labor_cost: float
    variable_cost: float
    total_cost: float


@dataclass(frozen=True, slots=True)
class SimulationResult:
    assignments: tuple[OrderAssignment, ...]
    center_summaries: tuple[CenterSummary, ...]
    total_fixed_cost: float
    total_labor_cost: float
    total_variable_cost: float
    total_cost: float
    unassigned_order_count: int
    unassigned_total_cost: float


def center_population_density(center_name: str) -> float:
    return CENTER_POPULATION_DENSITY.get(center_name, 0.0)


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
    candidates: list[OrderCandidate] | None = None,
    options: SimulationOptions = SimulationOptions(),
) -> SimulationResult:
    if not centers:
        raise ValueError("at least one center is required")

    all_candidates = (
        candidates if candidates is not None else build_order_candidates(orders=orders, centers=centers, options=options)
    )
    candidates_by_order: dict[str, list[OrderCandidate]] = defaultdict(list)
    candidates_by_center: dict[str, list[OrderCandidate]] = defaultdict(list)
    for candidate in all_candidates:
        candidates_by_order[candidate.order_id].append(candidate)
        candidates_by_center[candidate.center_id].append(candidate)

    if not all(candidate.center_candidate_rank is not None for candidate in all_candidates):
        for center_id in candidates_by_center:
            candidates_by_center[center_id] = sorted(
                candidates_by_center[center_id],
                key=lambda candidate: (candidate.delivery_cost, candidate.distance_km, candidate.order_id),
            )

    variable_cost_by_center: defaultdict[str, float] = defaultdict(float)
    assigned_orders_by_center: defaultdict[str, int] = defaultdict(int)
    overflow_orders_by_center: defaultdict[str, int] = defaultdict(int)
    assignments_by_order: dict[str, OrderAssignment] = {}

    ranked_centers = sorted(
        centers,
        key=lambda center: (-center_population_density(center.center_name), center.center_id, center.center_name),
    )
    max_staffing_level = max(center.staffing_level for center in centers)

    # o を 0 から n ずつ進め、各拠点で o を超える範囲から最大 n 人分だけ取り出し、
    # その人数 × m 件までの未割当配送先を低コスト順で担当させる。
    for current_staff_floor in range(0, max_staffing_level, options.staffing_round_increment):
        for center in ranked_centers:
            if center.staffing_level <= current_staff_floor:
                continue

            active_staff_in_round = min(options.staffing_round_increment, center.staffing_level - current_staff_floor)
            assignment_limit = active_staff_in_round * options.orders_per_staff
            assigned_in_round = 0
            for candidate in candidates_by_center[center.center_id]:
                if candidate.order_id in assignments_by_order:
                    continue

                assignments_by_order[candidate.order_id] = OrderAssignment(
                    order_id=candidate.order_id,
                    center_id=candidate.center_id,
                    center_name=candidate.center_name,
                    distance_km=candidate.distance_km,
                    delivery_cost=candidate.delivery_cost,
                    capacity_exceeded=False,
                )
                assigned_orders_by_center[center.center_id] += 1
                variable_cost_by_center[center.center_id] += candidate.delivery_cost
                assigned_in_round += 1
                if assigned_in_round >= assignment_limit:
                    break

    unassigned_total_cost = 0.0
    for order in sorted(orders, key=lambda current: current.order_id):
        if order.order_id in assignments_by_order:
            continue

        cheapest_candidate = next(
            (candidate for candidate in candidates_by_order[order.order_id] if candidate.order_candidate_rank == 1),
            None,
        )
        if cheapest_candidate is None:
            cheapest_candidate = min(
                candidates_by_order[order.order_id],
                key=lambda candidate: (
                    candidate.delivery_cost,
                    candidate.distance_km,
                    candidate.center_name,
                    candidate.center_id,
                ),
            )
        penalty_cost = round(cheapest_candidate.delivery_cost * UNASSIGNED_COST_MULTIPLIER, 2)
        unassigned_total_cost += penalty_cost
        assignments_by_order[order.order_id] = OrderAssignment(
            order_id=order.order_id,
            center_id=None,
            center_name=None,
            distance_km=cheapest_candidate.distance_km,
            delivery_cost=penalty_cost,
            capacity_exceeded=True,
            is_unassigned=True,
            fallback_center_id=cheapest_candidate.center_id,
            fallback_center_name=cheapest_candidate.center_name,
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
            labor_cost=round(center.staffing_level * options.labor_cost_per_staff, 2),
            variable_cost=round(variable_cost_by_center[center.center_id], 2),
            total_cost=round(
                variable_cost_by_center[center.center_id]
                + center.fixed_cost
                + center.staffing_level * options.labor_cost_per_staff,
                2,
            ),
        )
        for center in sorted(centers, key=lambda current: (current.center_name, current.center_id))
    )

    total_fixed_cost = round(sum(center.fixed_cost for center in centers), 2)
    total_labor_cost = round(sum(center.staffing_level * options.labor_cost_per_staff for center in centers), 2)
    ordered_assignments = tuple(
        assignments_by_order[order.order_id] for order in sorted(orders, key=lambda current: current.order_id)
    )
    total_variable_cost = round(sum(assignment.delivery_cost for assignment in ordered_assignments), 2)
    return SimulationResult(
        assignments=ordered_assignments,
        center_summaries=center_summaries,
        total_fixed_cost=total_fixed_cost,
        total_labor_cost=total_labor_cost,
        total_variable_cost=total_variable_cost,
        total_cost=round(total_fixed_cost + total_labor_cost + total_variable_cost, 2),
        unassigned_order_count=sum(1 for assignment in ordered_assignments if assignment.is_unassigned),
        unassigned_total_cost=round(unassigned_total_cost, 2),
    )
