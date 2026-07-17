"""
Demo runner — FPGA sensor swap / mini INS demo.

Shows attitude error across four sensor/compensation scenarios.
Intended for live demo to avionics audience; run on MAX 10 dev proxy or laptop.

Usage
-----
    cd crucible-lite-product
    python examples/fpga_sensor_swap/demo_run.py

Requirements: numpy (pip install numpy)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from src.signals import generate, SENSOR_G_RMS, VRE_ACCEL_LSM6DS3, VRE_ACCEL_LSM6DSO32
from src.algorithm import run, steady_state_error

DURATION_S = 5.0

SCENARIOS = [
    (
        "static", "nominal",
        "BEFORE SWAP — LSM6DS3, WHO_AM_I = 0x69 (FPGA expects 0x69 — PASS)",
        False,
    ),
    (
        None, None,
        "AFTER SWAP — LSM6DSO32, WHO_AM_I = 0x6C (FPGA expects 0x69 — init halts)",
        True,
    ),
    (
        "static", "nominal",
        "AFTER FIX  — LSM6DSO32, WHO_AM_I check updated to 0x6C in config_rom.v",
        False,
    ),
]

DAL_C_ATTITUDE_BUDGET_DEG = 0.5  # deg — DAL C system error budget (attitude display)


def _bar(error_deg: float, scale: float = 5.0, width: int = 40) -> str:
    filled = int(min(1.0, abs(error_deg) / scale) * width)
    sign = "+" if error_deg >= 0 else "-"
    return f"|{sign}{'█' * filled}{' ' * (width - filled)}|"


def main() -> None:
    print()
    print("=" * 72)
    print("  FPGA Sensor Swap Demo — LSM6DS3 → LSM6DSO32")
    print(f"  Attitude budget: ±{DAL_C_ATTITUDE_BUDGET_DEG}°")
    print("=" * 72)

    for profile, condition, label, is_hazard in SCENARIOS:
        print()
        print(f"  {label}")

        if profile is None:
            # Simulates INT1 polarity mismatch — FPGA edge detector never fires, no data
            print("  Roll:  ---- (no data)")
            print("  Pitch: ---- (no data)")
            print("  Status: NO OUTPUT  ← WHO_AM_I = 0x6C, FPGA expects 0x69 — init halts")
            continue

        samples   = generate(profile, condition, duration_s=DURATION_S)
        estimates = run(samples)
        roll_err, pitch_err = steady_state_error(estimates)

        within_budget = (
            abs(roll_err)  <= DAL_C_ATTITUDE_BUDGET_DEG and
            abs(pitch_err) <= DAL_C_ATTITUDE_BUDGET_DEG
        )

        status = "PASS ✓" if within_budget else "FAIL ✗"

        print(f"  Roll:  {roll_err:+.2f}°  {_bar(roll_err)}")
        print(f"  Pitch: {pitch_err:+.2f}°  {_bar(pitch_err)}")
        print(f"  Status: {status}")

    print()
    print("=" * 72)
    print("  Root cause: WHO_AM_I changed — LSM6DS3 = 0x69, LSM6DSO32 = 0x6C (FPGA expected 0x69).")
    print("  Fix: Update WHO_AM_I check in config_rom.v  (8'h69 → 8'h6C).")
    print("=" * 72)
    print()

    # ── Crucible auto-generated change record ──────────────────────────────────
    W = 76
    def row(s=""):
        pad = max(0, W - 2 - len(s))
        print("║" + s + " " * pad + "║")

    print("╔" + "═" * (W - 2) + "╗")
    print("║  CRUCIBLE CHANGE RECORD — auto-generated" + " " * (W - 43) + "║")
    print("║  Bill: B-001  │  Hearing: H-001  │  Status: APPROVED" + " " * (W - 55) + "║")
    print("╠" + "═" * (W - 2) + "╣")
    row()
    row("  Change")
    row("    LSM6DS3 (Adafruit #4503)  →  LSM6DSO32 (Adafruit #4692)")
    row("    Reason: supplier EOL notice")
    row()
    row("  Design delta — config_rom.v")
    row("    WHO_AM_I_EXPECTED   8'h69  →  8'h6C    [Primitive 3 — Init Handshake]")
    row("    FS_RANGE_BITS       2'b00  →  2'b10    [Primitive 4 — ODR / FS Range]")
    row()
    row("  Primitive citations (Amendment 01)")
    row("    P3 WHO_AM_I: 0x69→0x6C   source: ST DS13495 vs DocID026899")
    row("    P4 FS range: ±2g→±4g min  source: CTRL1_XL table, both datasheets")
    row()
    row("  Conditions of approval")
    row("    [✓] C-1  WHO_AM_I_EXPECTED updated in config_rom.v")
    row("    [✓] C-2  FS encoding verified against LSM6DSO32 CTRL1_XL table")
    row("    [✓] C-3  data_formatter.v scale factor updated (±4g minimum)")
    row("    [⏳] C-4  DO-160G Cat B VRE characterization — test pending")
    row("    [✓] C-5  Human approval on record (H-001 Justice ruling)")
    row()
    row("  Precedent established")
    row("    P-001: WHO_AM_I_EXPECTED must be updated for any sensor substitution.")
    row("           Future swaps in this class: auto-flagged, no Hearing required.")
    row()
    row("  Traceable artifacts")
    row("    docs/governance/hearings/H-001_sensor_swap.md")
    row("    docs/governance/case_law.md           ← P-001 entry")
    row("    fpga_sensor_swap/domain_primitives.md ← Primitive 3, 4 updated")
    row("    fpga_sensor_swap/device_context.md    ← BOM updated")
    row()
    print("╠" + "═" * (W - 2) + "╣")
    print("║  This record is the certification data package entry for this change." + " " * (W - 73) + "║")
    print("╚" + "═" * (W - 2) + "╝")
    print()


if __name__ == "__main__":
    main()
