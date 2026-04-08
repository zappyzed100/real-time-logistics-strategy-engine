from __future__ import annotations

import ctypes
import hashlib
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

import numpy as np


class NativeAssignmentResult(NamedTuple):
    assigned_center_indices: np.ndarray
    assigned_distance_km: np.ndarray
    assigned_delivery_cost: np.ndarray
    assigned_mask: np.ndarray


INT32_ARRAY = np.ctypeslib.ndpointer(dtype=np.int32, ndim=1, flags="C_CONTIGUOUS")
FLOAT64_ARRAY = np.ctypeslib.ndpointer(dtype=np.float64, ndim=1, flags="C_CONTIGUOUS")
UINT8_ARRAY = np.ctypeslib.ndpointer(dtype=np.uint8, ndim=1, flags="C_CONTIGUOUS")


def _compiler_command(output_path: Path, source_path: Path) -> list[str]:
    compiler = shutil.which("g++")
    if compiler is None:
        raise RuntimeError("g++ is required to build the native assignment engine")

    command = [
        compiler,
        "-O3",
        "-DNDEBUG",
        "-std=c++17",
        "-shared",
        "-fPIC",
        "-march=native",
        str(source_path),
        "-o",
        str(output_path),
    ]
    if shutil.which("ld.lld") is not None:
        command.insert(-2, "-fuse-ld=lld")
    return command


@lru_cache(maxsize=1)
def _load_native_library() -> ctypes.CDLL:
    source_path = Path(__file__).with_name("assignment_engine.cpp")
    build_dir = Path(tempfile.gettempdir()) / "real_time_logistics_native_engine"
    build_dir.mkdir(parents=True, exist_ok=True)
    source_digest = hashlib.sha256(source_path.read_bytes()).hexdigest()[:16]
    output_path = build_dir / f"assignment_engine_{source_digest}.so"

    if not output_path.exists():
        command = _compiler_command(output_path=output_path, source_path=source_path)
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or "failed to build native assignment engine")

    library = ctypes.CDLL(str(output_path))
    library.run_assignment_engine.argtypes = [
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.c_int32,
        ctypes.c_int32,
        INT32_ARRAY,
        INT32_ARRAY,
        INT32_ARRAY,
        INT32_ARRAY,
        INT32_ARRAY,
        FLOAT64_ARRAY,
        FLOAT64_ARRAY,
        INT32_ARRAY,
        FLOAT64_ARRAY,
        FLOAT64_ARRAY,
        UINT8_ARRAY,
    ]
    library.run_assignment_engine.restype = ctypes.c_int32
    return library


def run_assignment_engine(
    ranked_center_indices: np.ndarray,
    center_staffing_levels: np.ndarray,
    center_candidate_offsets: np.ndarray,
    candidate_order_indices: np.ndarray,
    candidate_center_indices: np.ndarray,
    candidate_distance_km: np.ndarray,
    candidate_delivery_cost: np.ndarray,
    orders_per_staff: int,
    staffing_round_increment: int,
    order_count: int,
    center_count: int,
) -> NativeAssignmentResult:
    library = _load_native_library()
    ranked_center_indices_array = np.ascontiguousarray(ranked_center_indices, dtype=np.int32)
    center_staffing_levels_array = np.ascontiguousarray(center_staffing_levels, dtype=np.int32)
    center_candidate_offsets_array = np.ascontiguousarray(center_candidate_offsets, dtype=np.int32)
    candidate_order_indices_array = np.ascontiguousarray(candidate_order_indices, dtype=np.int32)
    candidate_center_indices_array = np.ascontiguousarray(candidate_center_indices, dtype=np.int32)
    candidate_distance_km_array = np.ascontiguousarray(candidate_distance_km, dtype=np.float64)
    candidate_delivery_cost_array = np.ascontiguousarray(candidate_delivery_cost, dtype=np.float64)

    assigned_center_indices = np.full(order_count, -1, dtype=np.int32)
    assigned_distance_km = np.zeros(order_count, dtype=np.float64)
    assigned_delivery_cost = np.zeros(order_count, dtype=np.float64)
    assigned_mask = np.zeros(order_count, dtype=np.uint8)

    status = library.run_assignment_engine(
        order_count,
        center_count,
        int(candidate_order_indices_array.shape[0]),
        orders_per_staff,
        staffing_round_increment,
        ranked_center_indices_array,
        center_staffing_levels_array,
        center_candidate_offsets_array,
        candidate_order_indices_array,
        candidate_center_indices_array,
        candidate_distance_km_array,
        candidate_delivery_cost_array,
        assigned_center_indices,
        assigned_distance_km,
        assigned_delivery_cost,
        assigned_mask,
    )
    if status != 0:
        raise RuntimeError(f"native assignment engine failed with status {status}")

    return NativeAssignmentResult(
        assigned_center_indices=assigned_center_indices,
        assigned_distance_km=assigned_distance_km,
        assigned_delivery_cost=assigned_delivery_cost,
        assigned_mask=assigned_mask,
    )
