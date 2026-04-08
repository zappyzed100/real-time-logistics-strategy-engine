from __future__ import annotations

import os
import statistics
import time
from typing import TypedDict

import numpy as np

from src.simulation.native_engine import COMPILER_ENV_VAR, run_assignment_engine

ORDER_COUNT = 10_000
CENTER_COUNT = 47
ORDERS_PER_STAFF = 20
STAFFING_ROUND_INCREMENT = 1
WARMUP_RUNS = 5
MEASURED_RUNS = 25
COMPILERS = ("g++", "clang++")


class BenchmarkInputs(TypedDict):
    ranked_center_indices: np.ndarray
    center_staffing_levels: np.ndarray
    center_candidate_offsets: np.ndarray
    candidate_order_indices: np.ndarray
    candidate_center_indices: np.ndarray
    candidate_distance_km: np.ndarray
    candidate_delivery_cost: np.ndarray
    orders_per_staff: int
    staffing_round_increment: int
    order_count: int
    center_count: int


def build_benchmark_inputs() -> BenchmarkInputs:
    order_indices = np.arange(ORDER_COUNT, dtype=np.int32)
    ranked_center_indices = np.arange(CENTER_COUNT, dtype=np.int32)
    center_staffing_levels = np.asarray([12 + (center_index % 4) for center_index in range(CENTER_COUNT)], dtype=np.int32)
    center_candidate_offsets = np.arange(0, (CENTER_COUNT + 1) * ORDER_COUNT, ORDER_COUNT, dtype=np.int32)

    rotated_orders = [np.roll(order_indices, center_index * 211) for center_index in range(CENTER_COUNT)]
    candidate_order_indices = np.concatenate(rotated_orders).astype(np.int32, copy=False)
    candidate_center_indices = np.repeat(np.arange(CENTER_COUNT, dtype=np.int32), ORDER_COUNT)
    candidate_distance_km = (candidate_order_indices.astype(np.float64) % 500) * 0.1 + candidate_center_indices * 0.01
    candidate_delivery_cost = candidate_distance_km * 12.0 + candidate_center_indices * 3.0 + 600.0

    return {
        "ranked_center_indices": ranked_center_indices,
        "center_staffing_levels": center_staffing_levels,
        "center_candidate_offsets": center_candidate_offsets,
        "candidate_order_indices": candidate_order_indices,
        "candidate_center_indices": candidate_center_indices,
        "candidate_distance_km": candidate_distance_km,
        "candidate_delivery_cost": candidate_delivery_cost,
        "orders_per_staff": ORDERS_PER_STAFF,
        "staffing_round_increment": STAFFING_ROUND_INCREMENT,
        "order_count": ORDER_COUNT,
        "center_count": CENTER_COUNT,
    }


def benchmark_compiler(compiler: str, inputs: BenchmarkInputs) -> tuple[dict[str, np.ndarray], list[float]]:
    os.environ[COMPILER_ENV_VAR] = compiler
    result_snapshot: dict[str, np.ndarray] | None = None

    for _ in range(WARMUP_RUNS):
        result = run_assignment_engine(**inputs)
        result_snapshot = {
            "assigned_center_indices": result.assigned_center_indices.copy(),
            "assigned_distance_km": result.assigned_distance_km.copy(),
            "assigned_delivery_cost": result.assigned_delivery_cost.copy(),
            "assigned_mask": result.assigned_mask.copy(),
        }

    timings_ms: list[float] = []
    for _ in range(MEASURED_RUNS):
        started_at = time.perf_counter()
        result = run_assignment_engine(**inputs)
        timings_ms.append((time.perf_counter() - started_at) * 1000)
        result_snapshot = {
            "assigned_center_indices": result.assigned_center_indices.copy(),
            "assigned_distance_km": result.assigned_distance_km.copy(),
            "assigned_delivery_cost": result.assigned_delivery_cost.copy(),
            "assigned_mask": result.assigned_mask.copy(),
        }

    if result_snapshot is None:
        raise RuntimeError(f"benchmark did not execute for compiler {compiler}")
    return result_snapshot, timings_ms


def assert_same_outputs(left: dict[str, np.ndarray], right: dict[str, np.ndarray]) -> None:
    for key in left:
        if not np.array_equal(left[key], right[key]):
            raise RuntimeError(f"compiler outputs differ for {key}")


def main() -> None:
    inputs = build_benchmark_inputs()
    benchmark_results: dict[str, tuple[dict[str, np.ndarray], list[float]]] = {}
    for compiler in COMPILERS:
        benchmark_results[compiler] = benchmark_compiler(compiler=compiler, inputs=inputs)

    assert_same_outputs(benchmark_results[COMPILERS[0]][0], benchmark_results[COMPILERS[1]][0])

    print(f"dataset: orders={ORDER_COUNT}, centers={CENTER_COUNT}, candidates={ORDER_COUNT * CENTER_COUNT}")
    summary_rows: list[tuple[str, float, float, float]] = []
    for compiler in COMPILERS:
        timings_ms = benchmark_results[compiler][1]
        summary_rows.append(
            (
                compiler,
                statistics.mean(timings_ms),
                statistics.median(timings_ms),
                min(timings_ms),
            )
        )

    for compiler, mean_ms, median_ms, min_ms in summary_rows:
        print(f"{compiler}: mean={mean_ms:.3f} ms median={median_ms:.3f} ms min={min_ms:.3f} ms")

    winner = min(summary_rows, key=lambda row: (row[2], row[1]))[0]
    print(f"winner={winner}")


if __name__ == "__main__":
    main()
