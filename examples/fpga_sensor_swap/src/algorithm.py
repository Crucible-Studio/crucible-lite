"""
Attitude estimator — FPGA sensor swap demo.
Implements run(samples) per Crucible algorithm.py contract.

Mirrors the complementary filter running on the host PC (MAX 10 has no ARM core).
Operates on post-FPGA samples (broadband vibration already filtered by FPGA hardware).
The VRE DC bias, if present, passes through the FPGA LP filter and appears here as a
constant offset on accel_x — which the complementary filter's accelerometer correction
path integrates into a steady-state attitude error.

Filter design
-------------
α = 0.98 → corner f_c ≈ 6.4 Hz
  Traces to: ODR (Amendment 01 primitive 4)
  Gyro path dominates at f > f_c (vehicle manoeuvre band)
  Accel path dominates at f < f_c (gravity reference, and VRE DC bias)

The VRE DC bias (0 Hz) is below f_c → passes fully through the accel correction path.
This is the mechanism by which wrong VRE compensation creates systematic attitude error.
"""

import math
from typing import List, Tuple
from .signals import ImuSample, DT

# Traces to: ODR (Amendment 01 primitive 4)
# f_c = (1-α) * ODR / (2π * α) ≈ 6.4 Hz — chosen between manoeuvre band and vibration band
ALPHA: float = 0.98


def run(samples: List[ImuSample]) -> List[Tuple[float, float, float]]:
    """
    Complementary filter attitude estimator.

    Parameters
    ----------
    samples : list of ImuSample, post-FPGA (broadband vibration pre-filtered)

    Returns
    -------
    list of (ts_ms, roll_deg, pitch_deg)
        Truth for all demo scenarios: 0.0° / 0.0°
    """
    roll:  float = 0.0
    pitch: float = 0.0
    results: List[Tuple[float, float, float]] = []

    for s in samples:
        # Gyro propagation — integrates true rotation + VRE gyro bias
        roll_gyro  = roll  + s.gyro_x * DT
        pitch_gyro = pitch + s.gyro_y * DT

        # Accelerometer attitude reference — DC VRE bias on accel_x tilts gravity estimate
        # Traces to: VRE (Amendment 01 primitive 5)
        accel_roll  = math.degrees(math.atan2(s.accel_y, s.accel_z))
        accel_pitch = math.degrees(
            math.atan2(-s.accel_x, math.sqrt(s.accel_y ** 2 + s.accel_z ** 2))
        )

        # Complementary fusion — Traces to: ODR (Amendment 01 primitive 4)
        roll  = ALPHA * roll_gyro  + (1.0 - ALPHA) * accel_roll
        pitch = ALPHA * pitch_gyro + (1.0 - ALPHA) * accel_pitch

        results.append((s.ts_ms, roll, pitch))

    return results


def steady_state_error(results: List[Tuple[float, float, float]],
                       tail_fraction: float = 0.25) -> Tuple[float, float]:
    """Mean roll/pitch error over the final tail_fraction of the run. Truth = 0°."""
    n_tail = max(1, int(len(results) * tail_fraction))
    tail   = results[-n_tail:]
    return (
        sum(r[1] for r in tail) / n_tail,
        sum(r[2] for r in tail) / n_tail,
    )
