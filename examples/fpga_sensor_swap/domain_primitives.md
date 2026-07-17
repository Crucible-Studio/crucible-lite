# Amendment 01 — Domain Primitives (Avionics Inertial Sensor Interface)

**Device:** DAL C Data Concentrator Unit (DCU), dev proxy: Intel MAX 10 Eval Kit (EK-10M08E144)  
**Current sensor:** ST Microelectronics LSM6DS3 (Adafruit #4503, ~$7 CAD)  
**Proposed sensor:** ST Microelectronics LSM6DSO32 (Adafruit #4692, ~$11 CAD)  
**Applicable standards:** DO-254 Level C, DO-160G Section 8 (vibration)  
**Status:** RATIFIED — Spec Gate

---

## Purpose

Every RTL parameter, QSF constraint, clock divider, buffer depth, fixed-point coefficient,
and compensation table in this project must trace to one of the five primitives below.
A constant without a primitive citation violates Article I and is blocked at commit.

In an avionics context, uncited constants are not a style problem — they are a DO-254
traceability gap that blocks certification. Article I and DO-254 Section 11.3 (hardware
design standards) impose the same requirement from different directions.

---

## Primitive 1 — SPI Clock Frequency (f_SCLK, Hz)

**Definition:** Maximum serial clock frequency the sensor accepts on its SPI interface
without bit errors, specified at the qualification voltage and worst-case temperature
(−40°C to +85°C for DO-160G ground vehicle / −55°C to +85°C for airborne equipment).

**Why this is load-bearing:** The FPGA SPI master clock divider is derived from f_SCLK.
At avionics temperature extremes, PCB trace capacitance increases and signal rise times
degrade. A clock rate safe at +25°C lab conditions may produce corrupt reads at −40°C.
DO-254 requires the operating margin to be demonstrated, not assumed.

**LSM6DS3 value:** 10 MHz (max, all temperatures per ST datasheet DocID026899)  
**LSM6DSO32 value:** 10 MHz (max, all temperatures per ST datasheet DS13495)  
**Operating point chosen:** 2 MHz (conservative — no RTL change; both sensors share same limit)

**Consequence of swap:** f_SCLK operating point is unchanged at 2 MHz. No RTL change to
`spi_master.v`. Both sensors are qualified at this rate across the DO-160G temperature range.
If a future variant raises the operating point to 10 MHz, a new Bill and Hearing are required.

---

## Primitive 2 — VDDIO Voltage (V_IO, Volts)

**Definition:** Nominal I/O logic voltage at the sensor's SPI pins, at which the sensor's
output high level (V_OH) and input threshold (V_IH) are specified.

**Why this is load-bearing:** The FPGA I/O constraints (QSF file for Quartus) declare the
I/O standard for the Arduino header bank. A mismatch between the declared standard and the actual sensor V_IO
causes the FPGA output driver to overdrive the sensor's ESD clamp diodes. In avionics
hardware, ESD overstress causes latent failure — the device passes functional test but
degrades in the field under thermal cycling. This is a DO-160G Section 16 (voltage spike)
interaction and is not caught by standard functional verification.

**LSM6DS3 value:** 3.3V VDDIO (LVCMOS33) — Adafruit #4503 breakout includes onboard LDO  
**LSM6DSO32 value:** 3.3V VDDIO (LVCMOS33, same) — Adafruit #4692 breakout includes onboard LDO  
**Constraint change required:** None — both sensors use 3.3V logic. Arduino header I/O bank stays LVCMOS33.

**Consequence of swap:** No electrical interface change. This is the strongest safe
primitive in the substitution. No DO-254 re-assurance of I/O constraints required.

---

## Primitive 3 — Initialization Handshake (WHO_AM_I, hex)

**Definition:** The fixed, read-only device identifier returned by the sensor in response
to a WHO_AM_I register read (address 0x0F). The FPGA startup sequence (`config_rom.v`)
reads this register immediately after power-on and compares it against the expected value
for the installed sensor. If the values do not match, initialization halts and the data
path is never enabled.

**Why this is load-bearing:** The WHO_AM_I check is the primary mechanism by which the
FPGA confirms it is communicating with a known-good sensor before enabling the data path.
A mismatch is a hard stop — no data flows. DO-254 verification must confirm that
`config_rom.v` contains the correct expected value for the installed sensor, and that the
check is executed before any FIFO write. A config ROM that hardcodes the previous sensor's
WHO_AM_I will silently fail every time the new sensor is installed.

**LSM6DS3 value:** WHO_AM_I (0x0F) = **0x69** (fixed, factory-programmed, read-only)  
**LSM6DSO32 value:** WHO_AM_I (0x0F) = **0x6C** (fixed, factory-programmed, read-only)  
Sources: ST datasheet DocID026899 Rev 10 (LSM6DS3, Table 44); ST datasheet DS13495 (LSM6DSO32).

**Root cause of demo failure:** `config_rom.v` was written with `WHO_AM_I_EXPECTED = 8'h69`
for the LSM6DS3. After the swap, the FPGA reads 0x6C, comparison fails, initialization
halts, data path stays gated. Output: silence. Sensor powered, FPGA running, zero data.

**Consequence of swap:** `config_rom.v` must be updated: `WHO_AM_I_EXPECTED = 8'h6C`.
This is a DO-254 design change requiring design review and regression test evidence.
A condition of approval requires verification that the updated check is executed first
in the startup sequence, before any FIFO or ODR configuration write.

**Note on INT1 polarity (both sensors):** Both LSM6DS3 and LSM6DSO32 have CTRL3_C
register bit 5 (H_LACTIVE) default = 0 = active-HIGH. Interrupt polarity is unchanged
between these two sensors — no `config_rom.v` update is required for INT1 behavior.

---

## Primitive 4 — Output Data Rate (ODR, Hz)

**Definition:** Number of complete 6-axis IMU samples (accelerometer + gyroscope)
produced per second at the configured decimation register setting.

**Why this is load-bearing:** ODR determines the data bus load on the downstream
ARINC-429 or MIL-STD-1553 interface. Avionics bus protocols are bandwidth-constrained
and time-slotted. A change in ODR that exceeds the allocated slot timing causes bus
contention and affects other LRUs on the same bus — a system-level effect that is
outside the scope of the sensor substitution and must not be introduced.

**LSM6DS3 value:** 6.66 kHz (max); CTRL1_XL ODR bits 0b0101 = 208 Hz, 0b1010 = 1.66 kHz,
  0b1011 = 3.33 kHz; operating point: 2 kHz via ODR_XL = 0b1000 (CTRL1_XL[7:4])  
**LSM6DSO32 value:** 6.66 kHz (max); same CTRL1_XL ODR encoding — operating point unchanged at 2 kHz

**Consequence of swap:** Operating ODR is held at 2 kHz with the same register encoding.
Downstream bus loading is unchanged. No ARINC-429 reallocation required.
This is the second-strongest safe primitive after Primitive 2.

**Secondary risk — full-scale range encoding:** LSM6DS3 minimum FS = ±2g (CTRL1_XL[3:2] = 0b00).
LSM6DSO32 minimum FS = ±4g (same bit field = 0b00). If `config_rom.v` is copied verbatim,
all accelerometer output will be at half sensitivity — data flows, no error flag, wrong
scale factor applied. Bench tests pass; maneuver tests fail. This is a silent corruption
risk that Condition 3 of H-001 must address.

---

## Primitive 5 — Vibration Rectification Error (VRE, µg/g² and °/s per g²)

**Definition:** The DC bias error induced in accelerometer and gyroscope outputs by
broadband vibration, expressed as a bias shift per unit of vibration power spectral
density (g²). This is a first-order error source in airborne inertial sensing that
does not appear in bench or ground-vehicle testing.

**Why this is load-bearing:** DO-160G Section 8 (Vibration) defines the vibration
environment for airborne equipment. At Category B (general aviation) levels, the
vibration PSD is 0.04 g²/Hz from 10–2000 Hz. A sensor with a VRE of 50 µg/g² in
this environment produces a sustained accelerometer bias of ~0.8 mg — equivalent to
a 0.046° attitude error. For a DAL C DCU, this must be within the system error budget
allocated at ARP4754A system design level.

**LSM6DS3 value:** VRE **not published** by ST Microelectronics. Value from internal
  DO-160G characterization: ~70 µg/g² (accel), ~7 mdeg/s per g² (gyro). The absence
  of a published value means any coefficient in `data_formatter.v` is based on a single
  internal measurement with no supplier-backed traceability.

**LSM6DSO32 value:** VRE **not published** by ST Microelectronics. ST publishes
  "vibration robustness" as a scalar bias stability number, not a per-g² coefficient.
  Value from internal DO-160G characterization: ~55 µg/g² (accel), ~6 mdeg/s per g² (gyro).
  Same vendor, different generation — characterization methodology may differ.

**Net effect at 50 g_rms (structural resonance scenario):**
- LSM6DS3 (uncompensated): 70e-6 × 2500 = 175 mg bias → 10.1° pitch error
- LSM6DSO32 (uncompensated): 55e-6 × 2500 = 137.5 mg bias → 7.9° pitch error
- LSM6DSO32 with LSM6DS3 coefficients applied: −37.5 mg residual → −2.2° pitch error
- LSM6DSO32 with correct coefficients: 0 mg → 0° error
- DAL C attitude budget: ±0.5°. Both uncompensated and wrong-coefficient cases are 4–20× over budget.

**Consequence of swap:** Neither sensor publishes VRE. A DO-160G test at three temperatures
is required before `data_formatter.v` can be updated. This is the condition that requires
a Judicial Hearing — the compensation data does not exist yet at the time of the swap.

---

## Primitive derivation summary

| # | Primitive | Unit | DO Standard | Changes on swap? | Governance required |
|---|-----------|------|-------------|-----------------|---------------------|
| 1 | SPI Clock Frequency | Hz | DO-254 §11.3 | No (both 10 MHz max, held at 2 MHz) | None |
| 2 | VDDIO Voltage | V | DO-160G §16 | No (both 3.3V) | None |
| 3 | Initialization Handshake | WHO_AM_I hex | DO-254 verification | Yes — 0x69 → 0x6C | Design change + Hearing (Condition) |
| 4 | Output Data Rate | Hz | System bus allocation | No (same encoding, held at 2 kHz) | FS encoding check required |
| 5 | Vibration Rectification Error | µg/g² | DO-160G §8 | Yes (characterization needed) | Hearing |

Two primitives are safe unchanged (1, 2). One requires a targeted config_rom.v update and
design review (3 WHO_AM_I). One has a hidden FS encoding risk (4 ODR). One requires
a DO-160G test before deployment (5 VRE). A Judicial Hearing is required.
