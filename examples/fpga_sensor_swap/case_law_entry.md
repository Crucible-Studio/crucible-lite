# Case Law Entry — B-001 / H-001

> Append this block to `docs/governance/case_law.md` after H-001 is closed.

---

## B-001 — Sensor Substitution: LSM6DS3 → LSM6DSO32 (DAL C DCU)

**Date enacted:** 2026-07-16  
**Stage:** Stage 0 (pre-simulation)  
**Status:** ENACTED — subject to 5 Conditions  
**DO-254 classification:** Hardware design change — RTL and verification data updated

**Summary:** BOM substitution of EOL-approaching LSM6DS3 with LSM6DSO32 in the DAL C DCU
inertial sensor front-end. Two of five domain primitives unchanged (SPI frequency, VDDIO).
ODR encoding unchanged but FS range minimum changed (Primitive 4 — silent calibration risk).
Hearing identified three technical risks: WHO_AM_I identity change causing initialization
halt (caught by Crucible toolchain at bill submission time before hardware was touched),
FS range encoding change causing silent 2× sensitivity error, and VRE uncharacterized at
temperature with overcompensation in wrong direction if interim coefficient used.

**RTL changes authorized:**
- `config_rom.v` — WHO_AM_I_EXPECTED 8'h69 → 8'h6C, CTRL1_XL FS bits updated (C-1, C-2)
- `data_formatter.v` — VRE coefficient update (C-3 only — DO-160G test required first)

**RTL changes NOT authorized (unchanged):**
- `spi_master.v` — 2 MHz SPI clock divider unchanged
- `sample_buf.v` — buffer depth unchanged
- `uart_tx.v` — output format unchanged
- I/O constraints — LVCMOS33 unchanged

**Conditions (all must be met; C-5 expires on C-3 completion):**
- C-1 WHO_AM_I 0x6C confirmed at 2 MHz via SPI before `config_rom.v` merge
- C-2 FS bits updated + attitude verified at ±10° reference angle; error < ±0.5°
- C-3 DO-160G Cat B vibration at −40°C / +25°C / +85°C; VRE data committed
- C-4 `data_formatter.v` VRE coefficients from C-3 data only; Article I citation per line
- C-5 VRE_UNVALIDATED=1 build tag required until C-3 complete; Article II applies

**Hearing:** H-001 (complete — `docs/governance/hearings/H-001_lsm6ds3_to_lsm6dso32.md`)

---

## Precedents established

**Precedent P-001 — WHO_AM_I validation is mandatory for any sensor substitution.**
The WHO_AM_I register (typically at 0x0F) is a fixed, factory-programmed device identifier.
It changes between sensor generations even within the same vendor family: LSM6DS3 = 0x69,
LSM6DSO32 = 0x6C (ST Microelectronics). Any `config_rom.v` that hardcodes an expected
WHO_AM_I value must be updated on sensor substitution. Failure: initialization halts, data
path gated, zero output with no error flag. The Crucible toolchain caught this case at bill
submission time by comparing both datasheets — before hardware was touched. Future changes
in this class are auto-flagged by the system; no Hearing required for WHO_AM_I alone.

**Precedent P-002 — Full-scale range encoding must be verified register-by-register,
not assumed from interface family compatibility.**
FS range minimum encoding can change between sensor generations at the same register address.
LSM6DS3 CTRL1_XL[3:2] = 0b00 → ±2g; LSM6DSO32 CTRL1_XL[3:2] = 0b00 → ±4g. A verbatim
config ROM copy produces a 2× sensitivity error that passes all non-reference functional
tests. Verification requires attitude output at a known reference angle, not register write
confirmation alone. This failure class is distinct from WHO_AM_I and must be explicitly
checked for any substitution that shares a register map family.

**Precedent P-003 — VRE compensation coefficients may not be transferred between sensors
under Article I, even within the same vendor family.**
A coefficient derived from Sensor A DO-160G characterization is not a valid primitive
citation for Sensor B, regardless of performance direction. LSM6DS3 coefficient
(70 µg/g²) applied to LSM6DSO32 output (true VRE 55 µg/g²) at 50 g_rms produces
−37.5 mg residual bias — a −2.2° systematic pitch error in the wrong direction. This is
not a conservative interim state. DO-160G vibration test at three temperatures (−40°C,
+25°C, +85°C) is a mandatory condition before any VRE coefficient update. The interim
period requires Article II gate on any test article flash.
