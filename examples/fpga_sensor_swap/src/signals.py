"""
IMU physics model — FPGA sensor swap demo.
Implements generate(profile, condition) per Crucible signals.py contract.

System boundary
---------------
These samples represent data at the NAVIGATION FILTER input — after the FPGA PL
has applied its LP anti-aliasing filter and VRE compensation table from data_formatter.v.
Broadband vibration (10–2000 Hz) is rejected by the FPGA hardware filter before
this point. VRE bias is a DC component; it passes through or is subtracted depending
on whether data_formatter.v carries the correct coefficient for the installed sensor.

This is the critical distinction: the condition parameter models whether data_formatter.v
was updated for the LSM6DSO32 or still carries LSM6DS3 coefficients (VRE_UNVALIDATED).

Profiles
--------
static           : bench test, no vehicle vibration
turbulence_cat_b : DO-160G Section 8 Category B environment
                   50 g_rms at sensor (structural resonance at 150 Hz)
                   Broadband noise REJECTED by FPGA hardware LP filter.
                   VRE DC bias present or absent depending on condition.

Conditions
----------
nominal           : data_formatter.v has correct LSM6DSO32 VRE coefficient → bias removed
vre_uncompensated : data_formatter.v has NO VRE table → raw VRE bias reaches nav filter
vre_wrong_sensor  : data_formatter.v has LSM6DS3 coefficient applied to LSM6DSO32
                    → overcorrects (70 µg/g² applied to 55 µg/g² sensor); negative residual
                    → represents VRE_UNVALIDATED build state (H-001 Condition C-5)
"""

import numpy as np
from dataclasses import dataclass
from typing import List

# Traces to: ODR (Amendment 01 primitive 4)
ODR_HZ: int = 2000
DT: float = 1.0 / ODR_HZ

# VRE coefficients — Traces to: VRE (Amendment 01 primitive 5)
# LSM6DS3:   VRE not published by ST Microelectronics. Value from internal DO-160G characterization.
# LSM6DSO32: VRE not published by ST Microelectronics. Value from internal DO-160G characterization.
#             ST publishes "vibration robustness" as a bias stability number, not a per-g² coefficient.
#             Same-vendor substitution — neither part has supplier-backed VRE traceability.
VRE_ACCEL_LSM6DS3:    float = 70e-6   # g per g²  — ST Micro LSM6DS3, internal measurement
VRE_ACCEL_LSM6DSO32:  float = 55e-6   # g per g²  — ST Micro LSM6DSO32, internal measurement
VRE_GYRO_LSM6DS3:     float = 7e-3    # deg/s per g²
VRE_GYRO_LSM6DSO32:   float = 6e-3    # deg/s per g²

# Structural resonance vibration level at sensor — Traces to: VRE (Amendment 01 primitive 5)
# DO-160G Cat B input: 0.04 g²/Hz, 10–2000 Hz → 8.9 g_rms
# Panel resonance amplification Q≈6 at f_r=150 Hz → 50 g_rms at sensor mounting point
SENSOR_G_RMS: float = 50.0  # g_rms at sensor

# VRE-induced DC bias magnitudes (what data_formatter.v must subtract)
# Traces to: VRE (Amendment 01 primitive 5)
# LSM6DSO32 installed: raw bias = VRE_LSM6DSO32 * g_rms²
_VRE_BIAS_ACCEL = VRE_ACCEL_LSM6DSO32 * SENSOR_G_RMS ** 2   # 137.5 mg — raw LSM6DSO32 VRE
_VRE_BIAS_GYRO  = VRE_GYRO_LSM6DSO32  * SENSOR_G_RMS ** 2   # 15.0 deg/s

# Post-FPGA noise floor (broadband vibration filtered by FPGA hardware LP; only sensor noise remains)
# Traces to: ODR (Amendment 01 primitive 4) — LSM6DSO32 in-run noise specs
ACCEL_NOISE_G:  float = 0.8e-3   # g rms
GYRO_NOISE_DPS: float = 0.008    # deg/s rms


@dataclass
class ImuSample:
    ts_ms:   float
    accel_x: float   # g, body X (forward)
    accel_y: float   # g, body Y (right wing)
    accel_z: float   # g, body Z (down) — gravity = +1.0 at level flight
    gyro_x:  float   # deg/s, roll rate
    gyro_y:  float   # deg/s, pitch rate
    gyro_z:  float   # deg/s, yaw rate


def generate(profile: str, condition: str,
             duration_s: float = 10.0, seed: int = 42) -> List[ImuSample]:
    """
    Generate post-FPGA IMU samples for the given environment and sensor/firmware condition.

    Truth: level flight, zero angular rate, accel_z = +1g.
    """
    rng = np.random.default_rng(seed)
    n   = int(duration_s * ODR_HZ)

    if profile == "turbulence_cat_b":
        # VRE DC bias that reaches the navigation filter — depends on what data_formatter.v does
        # Traces to: VRE (Amendment 01 primitive 5)
        if condition == "vre_uncompensated":
            # data_formatter.v has no VRE table — full LSM6DSO32 bias reaches nav filter
            vre_bias_ax = _VRE_BIAS_ACCEL      # +137.5 mg on accel_x
            vre_bias_gx = _VRE_BIAS_GYRO       # +15.0 deg/s on gyro_x

        elif condition == "vre_wrong_sensor":
            # data_formatter.v subtracts LSM6DS3 coefficient from LSM6DSO32 output.
            # LSM6DS3 VRE was larger → overcorrects → negative residual bias.
            # Residual = LSM6DSO32 bias - LSM6DS3 correction applied
            applied_accel = VRE_ACCEL_LSM6DS3 * SENSOR_G_RMS ** 2  # 175 mg subtracted
            applied_gyro  = VRE_GYRO_LSM6DS3  * SENSOR_G_RMS ** 2
            vre_bias_ax   = _VRE_BIAS_ACCEL - applied_accel         # 137.5 - 175 = -37.5 mg
            vre_bias_gx   = _VRE_BIAS_GYRO  - applied_gyro

        else:  # nominal — correct LSM6DSO32 coefficient in data_formatter.v
            vre_bias_ax = 0.0
            vre_bias_gx = 0.0
    else:
        vre_bias_ax = 0.0
        vre_bias_gx = 0.0

    samples: List[ImuSample] = []
    for i in range(n):
        samples.append(ImuSample(
            ts_ms   = i * DT * 1000.0,
            # accel truth = [0, 0, +1g]; VRE bias on X axis; sensor noise only (vibration filtered)
            accel_x = 0.0 + vre_bias_ax + rng.normal(0.0, ACCEL_NOISE_G),
            accel_y = 0.0              + rng.normal(0.0, ACCEL_NOISE_G),
            accel_z = 1.0              + rng.normal(0.0, ACCEL_NOISE_G),
            # gyro truth = [0, 0, 0]; VRE bias on roll axis
            gyro_x  = 0.0 + vre_bias_gx + rng.normal(0.0, GYRO_NOISE_DPS),
            gyro_y  = 0.0              + rng.normal(0.0, GYRO_NOISE_DPS),
            gyro_z  = 0.0              + rng.normal(0.0, GYRO_NOISE_DPS),
        ))
    return samples
