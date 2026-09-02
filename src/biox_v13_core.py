#!/usr/bin/env python3
"""Pure-Python data and tensor utilities for the v1.3.0 PFM-anchored model.

The legacy input set is two-dimensional (N/m and pC/m) and is retained for
provenance.  The DFT-apparent input set can additionally provide a full 3-D
elastic matrix and dielectric tensor.  Its electromechanical coupling is
explicitly an apparent-PFM closure, not an intrinsic tensor claim.  No
COMSOL or third-party package is required for this module.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


EPS0 = 8.8541878128e-12
MATERIAL_ORDER = ("BiOCl", "BiOBr", "BiOI")
PFM_ORDER = ("BiOI", "BiOBr", "BiOCl")


def transpose(matrix: Sequence[Sequence[float]]) -> list[list[float]]:
    return [list(column) for column in zip(*matrix)]


def matmul(left: Sequence[Sequence[float]], right: Sequence[Sequence[float]]) -> list[list[float]]:
    if not left or not right or len(left[0]) != len(right):
        raise ValueError("Incompatible matrix dimensions.")
    return [
        [sum(left[i][k] * right[k][j] for k in range(len(right)))
         for j in range(len(right[0]))]
        for i in range(len(left))
    ]


def invert_matrix(matrix: Sequence[Sequence[float]]) -> list[list[float]]:
    """Invert a square matrix with partial-pivot Gauss-Jordan elimination."""
    n = len(matrix)
    if n == 0 or any(len(row) != n for row in matrix):
        raise ValueError("Only non-empty square matrices can be inverted.")
    work = [list(map(float, row)) + [1.0 if i == j else 0.0 for j in range(n)]
            for i, row in enumerate(matrix)]
    for column in range(n):
        pivot = max(range(column, n), key=lambda row: abs(work[row][column]))
        if abs(work[pivot][column]) < 1e-30:
            raise ValueError("Matrix is singular.")
        work[column], work[pivot] = work[pivot], work[column]
        scale = work[column][column]
        work[column] = [value / scale for value in work[column]]
        for row in range(n):
            if row == column:
                continue
            factor = work[row][column]
            work[row] = [value - factor * pivot_value
                         for value, pivot_value in zip(work[row], work[column])]
    return [row[n:] for row in work]


def is_positive_definite(matrix: Sequence[Sequence[float]]) -> bool:
    """Cholesky test without NumPy so the precheck remains dependency-free."""
    n = len(matrix)
    if n == 0 or any(len(row) != n for row in matrix):
        return False
    lower = [[0.0] * n for _ in range(n)]
    try:
        for i in range(n):
            for j in range(i + 1):
                subtotal = sum(lower[i][k] * lower[j][k] for k in range(j))
                if i == j:
                    value = matrix[i][i] - subtotal
                    if value <= 0.0:
                        return False
                    lower[i][j] = math.sqrt(value)
                else:
                    lower[i][j] = (matrix[i][j] - subtotal) / lower[j][j]
    except (ValueError, ZeroDivisionError):
        return False
    return True


def flatten_column_major(matrix: Sequence[Sequence[float]]) -> list[float]:
    return [matrix[row][column]
            for column in range(len(matrix[0]))
            for row in range(len(matrix))]


@dataclass(frozen=True)
class PFMTarget:
    d33_app_pm_per_v: float
    sd_pm_per_v: float
    n_cycles: int


@dataclass(frozen=True)
class Material2D:
    name: str
    lattice_a_A: float
    bandgap_eV: float
    c2d_N_per_m: list[list[float]] | None
    e2d_pC_per_m: list[list[float]] | None
    d11_reported_pm_per_v: float | None
    d31_reported_pm_per_v: float | None
    epsilon_r_s_sensitivity_diag: list[float] | None
    epsilon_status: str
    pfm_target: PFMTarget
    # Optional first-principles 3-D data.  These are kept separate from the
    # legacy 2-D bridge so that a run cannot silently mix the two conventions.
    cE_3d_Pa: list[list[float]] | None = None
    epsilon_r_electronic_diag: list[float] | None = None
    epsilon_r_ionic_diag: list[float] | None = None
    epsilon_r_low_frequency_diag: list[float] | None = None
    dft_piezo_total_e_C_per_m2: list[list[float]] | None = None
    apparent_e33_C_per_m2: float | None = None
    constitutive_status: str = "legacy_2d_bridge"

    @property
    def c66_N_per_m(self) -> float:
        if self.c2d_N_per_m is None:
            raise ValueError(f"{self.name}: no 2-D stiffness matrix is available.")
        return self.c2d_N_per_m[2][2]

    @property
    def d11_derived_pm_per_v(self) -> float:
        if self.c2d_N_per_m is None or self.e2d_pC_per_m is None:
            raise ValueError(f"{self.name}: no 2-D tensor pair is available.")
        return self.e2d_pC_per_m[0][0] / (self.c2d_N_per_m[0][0] - self.c2d_N_per_m[0][1])

    @property
    def d31_derived_pm_per_v(self) -> float:
        if self.c2d_N_per_m is None or self.e2d_pC_per_m is None:
            raise ValueError(f"{self.name}: no 2-D tensor pair is available.")
        return self.e2d_pC_per_m[2][0] / (self.c2d_N_per_m[0][0] + self.c2d_N_per_m[0][1])

    def validate(self) -> None:
        if self.c2d_N_per_m is not None or self.e2d_pC_per_m is not None:
            if self.c2d_N_per_m is None or self.e2d_pC_per_m is None:
                raise ValueError(f"{self.name}: c2d and e2d must be supplied together.")
            if len(self.c2d_N_per_m) != 3 or any(len(row) != 3 for row in self.c2d_N_per_m):
                raise ValueError(f"{self.name}: c2d_N_per_m must be 3x3.")
            if len(self.e2d_pC_per_m) != 3 or any(len(row) != 3 for row in self.e2d_pC_per_m):
                raise ValueError(f"{self.name}: e2d_pC_per_m must be 3x3.")
            if any(abs(self.c2d_N_per_m[i][j] - self.c2d_N_per_m[j][i]) > 1e-9
                   for i in range(3) for j in range(3)):
                raise ValueError(f"{self.name}: c2d matrix is not symmetric.")
            if not is_positive_definite(self.c2d_N_per_m):
                raise ValueError(f"{self.name}: c2d matrix is not positive definite.")
            if self.d11_reported_pm_per_v is None or self.d31_reported_pm_per_v is None:
                raise ValueError(f"{self.name}: reported d11/d31 values are required with a 2-D tensor pair.")
        if self.epsilon_r_s_sensitivity_diag is not None and any(
                value <= 0.0 for value in self.epsilon_r_s_sensitivity_diag):
            raise ValueError(f"{self.name}: all sensitivity dielectric entries must be positive.")
        if self.cE_3d_Pa is not None:
            if len(self.cE_3d_Pa) != 6 or any(len(row) != 6 for row in self.cE_3d_Pa):
                raise ValueError(f"{self.name}: cE_3d_Pa must be 6x6 when supplied.")
            if any(abs(self.cE_3d_Pa[i][j] - self.cE_3d_Pa[j][i]) > 1e-3
                   for i in range(6) for j in range(6)):
                raise ValueError(f"{self.name}: cE_3d_Pa must be symmetric.")
            if not is_positive_definite(self.cE_3d_Pa):
                raise ValueError(f"{self.name}: cE_3d_Pa is not positive definite.")
        for label, diagonal in (
            ("epsilon_r_electronic_diag", self.epsilon_r_electronic_diag),
            ("epsilon_r_ionic_diag", self.epsilon_r_ionic_diag),
            ("epsilon_r_low_frequency_diag", self.epsilon_r_low_frequency_diag),
        ):
            if diagonal is not None and (len(diagonal) != 3 or any(value <= 0.0 for value in diagonal)):
                raise ValueError(f"{self.name}: {label} must contain three positive entries.")
        if self.dft_piezo_total_e_C_per_m2 is not None:
            if len(self.dft_piezo_total_e_C_per_m2) != 3 or any(
                    len(row) != 6 for row in self.dft_piezo_total_e_C_per_m2):
                raise ValueError(f"{self.name}: dft_piezo_total_e_C_per_m2 must be 3x6 when supplied.")
        if self.c2d_N_per_m is not None and self.e2d_pC_per_m is not None:
            for label, derived, reported in (
                ("d11", self.d11_derived_pm_per_v, self.d11_reported_pm_per_v),
                ("d31", self.d31_derived_pm_per_v, self.d31_reported_pm_per_v),
            ):
                scale = max(abs(reported), 1e-12)
                if abs(derived - reported) / scale > 0.02:
                    raise ValueError(
                        f"{self.name}: derived {label}={derived:.6g} pm/V does not match "
                        f"reported {reported:.6g} pm/V.")

    def effective_3d(self, thickness_nm: float,
                     c33_over_c11: float = 1.0,
                     c13_over_c12: float = 1.0,
                     shear_over_c66: float = 1.0,
                     e33_over_e31: float = 0.0) -> tuple[list[list[float]], list[list[float]], list[list[float]]]:
        """Return effective 3-D cE, eES and epsilon matrices for COMSOL.

        This is an effective-continuum extension, not a claim that the source
        article supplied out-of-plane elastic constants.
        """
        if thickness_nm <= 0.0:
            raise ValueError("Effective thickness must be positive.")
        if self.c2d_N_per_m is None or self.e2d_pC_per_m is None or self.epsilon_r_s_sensitivity_diag is None:
            raise ValueError(f"{self.name}: legacy 2-D bridge requires c2d, e2d and dielectric inputs.")
        t_m = thickness_nm * 1e-9
        c11 = self.c2d_N_per_m[0][0] / t_m
        c12 = self.c2d_N_per_m[0][1] / t_m
        c66 = self.c2d_N_per_m[2][2] / t_m
        c33 = c11 * c33_over_c11
        c13 = c12 * c13_over_c12
        shear = c66 * shear_over_c66
        c3d = [
            [c11, c12, c13, 0.0, 0.0, 0.0],
            [c12, c11, c13, 0.0, 0.0, 0.0],
            [c13, c13, c33, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, shear, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, shear, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, c66],
        ]
        if not is_positive_definite(c3d):
            raise ValueError(f"{self.name}: effective 3-D stiffness is not positive definite.")

        e11 = self.e2d_pC_per_m[0][0] * 1e-12 / t_m
        e31 = self.e2d_pC_per_m[2][0] * 1e-12 / t_m
        e33 = e31 * float(e33_over_e31)
        e3d = [
            [e11, -e11, 0.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, -0.5 * e11],
            [e31, e31, e33, 0.0, 0.0, 0.0],
        ]
        eps = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
        for i, value in enumerate(self.epsilon_r_s_sensitivity_diag):
            eps[i][i] = value
        return c3d, e3d, eps

    def dft_apparent_3d(self, epsilon_variant: str = "low_frequency_total") -> tuple[
            list[list[float]], list[list[float]], list[list[float]]]:
        """Return DFT elastic/dielectric data with a PFM-apparent e33 channel.

        The DFT runs in the supplied archive report a zero total macroscopic
        piezoelectric tensor.  For the apparent-response comparison we retain
        that result as provenance and introduce only the measured SSPFM normal
        response as an effective ``e33`` channel.  This is a measurement-level
        closure; it must not be described as an intrinsic bulk coefficient.
        """
        if self.cE_3d_Pa is None:
            raise ValueError(f"{self.name}: no DFT 3-D elastic matrix is available.")
        if epsilon_variant == "electronic":
            diagonal = self.epsilon_r_electronic_diag
        elif epsilon_variant == "ionic":
            diagonal = self.epsilon_r_ionic_diag
        elif epsilon_variant in {"low_frequency_total", "total"}:
            diagonal = self.epsilon_r_low_frequency_diag
        else:
            raise ValueError(f"Unsupported DFT dielectric variant: {epsilon_variant}")
        if diagonal is None:
            raise ValueError(f"{self.name}: dielectric variant {epsilon_variant!r} is unavailable.")
        if self.apparent_e33_C_per_m2 is None:
            raise ValueError(f"{self.name}: apparent_e33_C_per_m2 is required for the apparent model.")
        c3d = [list(row) for row in self.cE_3d_Pa]
        e3d = [[0.0] * 6 for _ in range(3)]
        # Voigt order is xx, yy, zz, yz, xz, xy.  The only calibrated channel
        # is normal polarization generated by normal strain.
        e3d[2][2] = float(self.apparent_e33_C_per_m2)
        eps = [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
        for i, value in enumerate(diagonal):
            eps[i][i] = float(value)
        return c3d, e3d, eps


def load_config(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") not in {"1.3.0-pfm-anchored", "1.3.0-dft-apparent"}:
        raise ValueError(f"Unexpected material schema in {path}.")
    return payload


def load_materials(path: Path) -> dict[str, Material2D]:
    payload = load_config(path)
    output: dict[str, Material2D] = {}
    for name in MATERIAL_ORDER:
        raw = payload["materials"][name]
        target = raw["pfm_target"]
        material = Material2D(
            name=name,
            lattice_a_A=float(raw["lattice_a_A"]),
            bandgap_eV=float(raw["bandgap_eV"]),
            c2d_N_per_m=(
                [[float(value) for value in row] for row in raw["c2d_N_per_m"]]
                if raw.get("c2d_N_per_m") is not None else None
            ),
            e2d_pC_per_m=(
                [[float(value) for value in row] for row in raw["e2d_pC_per_m"]]
                if raw.get("e2d_pC_per_m") is not None else None
            ),
            d11_reported_pm_per_v=(
                float(raw["d2d_reported_pm_per_V"]["d11"])
                if raw.get("d2d_reported_pm_per_V") is not None else None
            ),
            d31_reported_pm_per_v=(
                float(raw["d2d_reported_pm_per_V"]["d31"])
                if raw.get("d2d_reported_pm_per_V") is not None else None
            ),
            epsilon_r_s_sensitivity_diag=(
                [float(value) for value in raw["epsilon_r_s_sensitivity_diag"]]
                if raw.get("epsilon_r_s_sensitivity_diag") is not None else None
            ),
            epsilon_status=str(raw["epsilon_status"]),
            pfm_target=PFMTarget(
                d33_app_pm_per_v=float(target["d33_app_pm_per_V"]),
                sd_pm_per_v=float(target["sd_pm_per_V"]),
                n_cycles=int(target["n_cycles"]),
            ),
            cE_3d_Pa=(
                [[float(value) for value in row] for row in raw["cE_3d_Pa"]]
                if raw.get("cE_3d_Pa") is not None else None
            ),
            epsilon_r_electronic_diag=(
                [float(value) for value in raw["epsilon_r_electronic_diag"]]
                if raw.get("epsilon_r_electronic_diag") is not None else None
            ),
            epsilon_r_ionic_diag=(
                [float(value) for value in raw["epsilon_r_ionic_diag"]]
                if raw.get("epsilon_r_ionic_diag") is not None else None
            ),
            epsilon_r_low_frequency_diag=(
                [float(value) for value in raw["epsilon_r_low_frequency_diag"]]
                if raw.get("epsilon_r_low_frequency_diag") is not None else None
            ),
            dft_piezo_total_e_C_per_m2=(
                [[float(value) for value in row]
                 for row in raw["dft_piezo_total_e_C_per_m2"]]
                if raw.get("dft_piezo_total_e_C_per_m2") is not None else None
            ),
            apparent_e33_C_per_m2=(
                float(raw["apparent_e33_C_per_m2"])
                if raw.get("apparent_e33_C_per_m2") is not None else None
            ),
            constitutive_status=str(raw.get("constitutive_status", "legacy_2d_bridge")),
        )
        material.validate()
        output[name] = material
    return output


def order_from(values: dict[str, float]) -> list[str]:
    return sorted(values, key=values.get, reverse=True)


def relative_targets(materials: dict[str, Material2D]) -> dict[str, float]:
    base = materials["BiOCl"].pfm_target.d33_app_pm_per_v
    return {name: material.pfm_target.d33_app_pm_per_v / base
            for name, material in materials.items()}
