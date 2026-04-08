from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from src.simulation.native_engine import run_assignment_engine


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


@dataclass(frozen=True, slots=True)
class StaticPreparedSimulationData:
    ordered_orders: tuple[OrderDemand, ...]
    primary_candidates_by_order: tuple[OrderCandidate | None, ...]
    ranked_center_indices: np.ndarray
    center_candidate_offsets: np.ndarray
    candidate_order_indices: np.ndarray
    candidate_center_indices: np.ndarray
    candidate_distance_km: np.ndarray
    candidate_delivery_cost: np.ndarray
    center_signatures: tuple[tuple[str, str], ...]


def center_population_density(center_name: str) -> float:
    return CENTER_POPULATION_DENSITY.get(center_name, 0.0)


def prepare_static_simulation_data(
    orders: Sequence[OrderDemand],
    centers: Sequence[CenterScenario],
    candidates: Sequence[OrderCandidate],
) -> StaticPreparedSimulationData:
    ordered_orders = tuple(sorted(orders, key=lambda current: current.order_id))
    center_signatures = tuple((center.center_id, center.center_name) for center in centers)
    order_index_by_id = {order.order_id: index for index, order in enumerate(ordered_orders)}
    center_index_by_id = {center_id: index for index, (center_id, _) in enumerate(center_signatures)}
    seen_order_ids: set[str] = set()
    candidates_by_center: list[list[OrderCandidate]] = [[] for _ in center_signatures]
    primary_candidates_by_order: list[OrderCandidate | None] = [None] * len(ordered_orders)

    for candidate in candidates:
        center_index = center_index_by_id.get(candidate.center_id)
        if center_index is None:
            raise ValueError(f"unknown center_id in candidates: {candidate.center_id}")
        order_index = order_index_by_id.get(candidate.order_id)
        if order_index is None:
            raise ValueError(f"unknown order_id in candidates: {candidate.order_id}")
        if candidate.center_candidate_rank is None or candidate.order_candidate_rank is None:
            raise ValueError("precomputed candidates must include center_candidate_rank and order_candidate_rank")

        seen_order_ids.add(candidate.order_id)
        candidates_by_center[center_index].append(candidate)
        if candidate.order_candidate_rank == 1 and primary_candidates_by_order[order_index] is None:
            primary_candidates_by_order[order_index] = candidate

    missing_order_ids = sorted(set(order_index_by_id) - seen_order_ids)
    if missing_order_ids:
        raise ValueError(f"missing precomputed candidates for orders: {', '.join(missing_order_ids[:5])}")

    missing_primary_rank_order_ids = [
        ordered_orders[index].order_id
        for index, primary_candidate in enumerate(primary_candidates_by_order)
        if primary_candidate is None
    ]
    if missing_primary_rank_order_ids:
        raise ValueError(f"missing order_candidate_rank=1 for orders: {', '.join(missing_primary_rank_order_ids[:5])}")

    candidate_order_indices_list: list[int] = []
    candidate_center_indices_list: list[int] = []
    candidate_distance_km_list: list[float] = []
    candidate_delivery_cost_list: list[float] = []
    center_candidate_offsets = [0]
    for center_index, center_candidates in enumerate(candidates_by_center):
        for candidate in center_candidates:
            candidate_order_indices_list.append(order_index_by_id[candidate.order_id])
            candidate_center_indices_list.append(center_index)
            candidate_distance_km_list.append(candidate.distance_km)
            candidate_delivery_cost_list.append(candidate.delivery_cost)
        center_candidate_offsets.append(len(candidate_order_indices_list))

    ranked_center_indices = np.asarray(
        [
            center_index
            for center_index, (center_id, center_name) in sorted(
                enumerate(center_signatures),
                key=lambda item: (-center_population_density(item[1][1]), item[1][0], item[1][1]),
            )
        ],
        dtype=np.int32,
    )
    return StaticPreparedSimulationData(
        ordered_orders=ordered_orders,
        primary_candidates_by_order=tuple(primary_candidates_by_order),
        ranked_center_indices=ranked_center_indices,
        center_candidate_offsets=np.asarray(center_candidate_offsets, dtype=np.int32),
        candidate_order_indices=np.asarray(candidate_order_indices_list, dtype=np.int32),
        candidate_center_indices=np.asarray(candidate_center_indices_list, dtype=np.int32),
        candidate_distance_km=np.asarray(candidate_distance_km_list, dtype=np.float64),
        candidate_delivery_cost=np.asarray(candidate_delivery_cost_list, dtype=np.float64),
        center_signatures=center_signatures,
    )


def _validate_prepared_static_data(
    prepared_static_data: StaticPreparedSimulationData,
    centers: Sequence[CenterScenario],
) -> None:
    current_center_signatures = tuple((center.center_id, center.center_name) for center in centers)
    if prepared_static_data.center_signatures != current_center_signatures:
        raise ValueError("prepared_static_data does not match current centers")


def simulate_assignments(
    orders: Sequence[OrderDemand],
    centers: Sequence[CenterScenario],
    candidates: Sequence[OrderCandidate],
    options: SimulationOptions = SimulationOptions(),
    prepared_static_data: StaticPreparedSimulationData | None = None,
) -> SimulationResult:
    if not centers:
        raise ValueError("at least one center is required")
    if not candidates:
        raise ValueError("precomputed candidates are required")

    static_prepared_data = prepared_static_data or prepare_static_simulation_data(
        orders=orders,
        centers=centers,
        candidates=candidates,
    )
    _validate_prepared_static_data(static_prepared_data, centers)
    center_staffing_levels = np.asarray([center.staffing_level for center in centers], dtype=np.int32)
    native_result = run_assignment_engine(
        ranked_center_indices=static_prepared_data.ranked_center_indices,
        center_staffing_levels=center_staffing_levels,
        center_candidate_offsets=static_prepared_data.center_candidate_offsets,
        candidate_order_indices=static_prepared_data.candidate_order_indices,
        candidate_center_indices=static_prepared_data.candidate_center_indices,
        candidate_distance_km=static_prepared_data.candidate_distance_km,
        candidate_delivery_cost=static_prepared_data.candidate_delivery_cost,
        orders_per_staff=options.orders_per_staff,
        staffing_round_increment=options.staffing_round_increment,
        order_count=len(static_prepared_data.ordered_orders),
        center_count=len(centers),
    )

    variable_cost_by_center: defaultdict[str, float] = defaultdict(float)
    assigned_orders_by_center: defaultdict[str, int] = defaultdict(int)
    overflow_orders_by_center: defaultdict[str, int] = defaultdict(int)
    assignments_by_order: dict[str, OrderAssignment] = {}

    unassigned_total_cost = 0.0
    for order_index, order in enumerate(static_prepared_data.ordered_orders):
        if bool(native_result.assigned_mask[order_index]):
            assigned_center = centers[int(native_result.assigned_center_indices[order_index])]
            assignment = OrderAssignment(
                order_id=order.order_id,
                center_id=assigned_center.center_id,
                center_name=assigned_center.center_name,
                distance_km=float(native_result.assigned_distance_km[order_index]),
                delivery_cost=float(native_result.assigned_delivery_cost[order_index]),
                capacity_exceeded=False,
            )
            assignments_by_order[order.order_id] = assignment
            assigned_orders_by_center[assigned_center.center_id] += 1
            variable_cost_by_center[assigned_center.center_id] += assignment.delivery_cost
            continue

        cheapest_candidate = static_prepared_data.primary_candidates_by_order[order_index]
        if cheapest_candidate is None:
            raise RuntimeError(f"missing primary candidate for order {order.order_id}")
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
    ordered_assignments = tuple(assignments_by_order[order.order_id] for order in static_prepared_data.ordered_orders)
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
