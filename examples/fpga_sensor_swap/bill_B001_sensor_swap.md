# Bill B-001 — Sensor Substitution: LSM6DS3 → LSM6DSO32 (DAL C DCU)

**Proposed by:** hw-advisor  
**Date:** 2026-07-16  
**Stage:** Stage 0 (pre-simulation) — BOM change before RTL freeze  
**DO-254 classification:** Hardware design change — requires design review evidence  
**Requires Hearing:** Yes — Primitive 3 (WHO_AM_I), Primitive 4 (FS range encoding), Primitive 5 (VRE) all change  
**Requires human approval:** Yes — BOM change with DO-160G qualification implication (Article II)

---

## Proposed Change

Substitute the inertial measurement unit in the DAL C DCU sensor front-end from the
ST Microelectronics LSM6DS3 (Adafruit #4503, ~$7 CAD) to the ST Microelectronics
LSM6DSO32 (Adafruit #4692, ~$11 CAD). Both sensors are from the same vendor, share the
same SPI interface family (Mode 3, LVCMOS33, 2 MHz operating point), and use the same
physical connector (Arduino header pin assignment unchanged). However, they have different
WHO_AM_I values, different minimum full-scale range encoding, and uncharacterized VRE at
temperature.

The downstream UART output format is unchanged. The sample buffer internal interface is
unchanged. The FPGA I/O constraints are unchanged.

---

## Motivation

The LSM6DS3 is approaching natural end-of-life as ST Microelectronics migrates the product
line to the DSO-series. The LSM6DSO32 is the current-generation replacement from the same
vendor. Extended accelerometer range (±32g vs ±16g maximum), improved vibration robustness
per ST characterization, and no EOL indication. MTBF improves from ~160,000 to ~190,000
hours (MIL-HDBK-217F, +40°C ground benign). Same-vendor substitution — the governance case
is harder to dismiss than a cross-vendor swap.

---

## Impact Analysis by Domain Primitive

### Primitive 1 — SPI Clock Frequency

| Parameter | LSM6DS3 | LSM6DSO32 | Operating point |
|-----------|---------|----------|----------------|
| f_SCLK max (datasheet) | 10 MHz | 10 MHz | 2 MHz (held) |
| RTL clock divider change | — | Not required | None |

**Assessment:** Both sensors share a 10 MHz SPI maximum. Operating point held at 2 MHz —
no RTL change to `spi_master.v`. PASS — no change.

### Primitive 2 — VDDIO Voltage

| Parameter | LSM6DS3 | LSM6DSO32 | Delta |
|-----------|---------|----------|-------|
| VDDIO | 3.3V (Adafruit LDO) | 3.3V (Adafruit LDO) | None |
| I/O standard | LVCMOS33 | LVCMOS33 | None |

**Assessment:** Both breakout boards include an onboard LDO. FPGA I/O constraints
unchanged. PASS — no change.

### Primitive 3 — Initialization Handshake (WHO_AM_I)

| Parameter | LSM6DS3 | LSM6DSO32 | Delta |
|-----------|---------|----------|-------|
| WHO_AM_I register (0x0F) | **0x69** | **0x6C** | Changed |
| Source | ST DocID026899 Rev 10, Table 44 | ST DS13495 | Verified |
| CTRL3_C H_LACTIVE default | 0 (active-high) | 0 (active-high) | Unchanged |
| INT1 polarity | Active-high | Active-high | Unchanged |

**Assessment:** WHO_AM_I is a fixed, factory-programmed, read-only identifier.
`config_rom.v` validates WHO_AM_I before enabling the data path. With the current
hardcoded value (0x69), the FPGA will reject the LSM6DSO32 (which returns 0x6C),
initialization will halt, and no data will flow. This is a hard, immediate, verifiable
failure — the primary risk of the substitution.

**Risk:** HIGH — data path silently disabled. Required as Condition C-1.  
**Fix:** `WHO_AM_I_EXPECTED = 8'h6C` in `config_rom.v`. One constant. Cite Primitive 3.

**Note on INT1 polarity:** Both sensors have CTRL3_C bit 5 (H_LACTIVE) default = 0 =
active-high. INT1 behavior is **unchanged** between these sensors — no `config_rom.v`
update required for interrupt polarity. This is the single strongest safe parameter.

### Primitive 4 — Output Data Rate / Full-Scale Range

| Parameter | LSM6DS3 | LSM6DSO32 | Delta |
|-----------|---------|----------|-------|
| ODR encoding (CTRL1_XL[7:4]) | Same | Same | None |
| Operating point | 2 kHz (ODR_XL = 0b1000) | 2 kHz (same encoding) | None |
| FS minimum (CTRL1_XL[3:2] = 0b00) | ±2g | ±4g | **Encoding changed** |
| Sensitivity at 0b00 | 0.061 mg/LSB | 0.122 mg/LSB | 2× difference |

**Assessment:** ODR encoding is unchanged — 2 kHz operating point holds. However, the
full-scale range minimum doubled: register value 0b00 means ±2g on LSM6DS3 and ±4g on
LSM6DSO32. If `config_rom.v` is copied verbatim, the sensor operates at ±4g with the
driver applying ±2g sensitivity. All accelerometer readings will be half of true value.
Data flows, no error flag, wrong scale factor. Passes bench functional test; fails at
any non-zero pitch angle when compared against a reference.

**Risk:** MEDIUM-HIGH — silent calibration error, invisible at bench. Required as Condition C-2.  
**Fix:** Update CTRL1_XL FS bits in `config_rom.v` and sensitivity constant in
`data_formatter.v`. Cite Primitive 4. Verify attitude output at known reference angle.

### Primitive 5 — Vibration Rectification Error (VRE)

| Parameter | LSM6DS3 | LSM6DSO32 | Delta |
|-----------|---------|----------|-------|
| VRE accel (internal char.) | ~70 µg/g² | ~55 µg/g² | −21% (improvement) |
| VRE gyro (internal char.) | ~7 mdeg/s per g² | ~6 mdeg/s per g² | −14% |
| Published VRE | Not published | Not published | N/A — neither supplier publishes |
| VRE temperature coefficient | Not published | Not published | UNKNOWN |

**Assessment:** Neither sensor publishes VRE. Both compensation values are from internal
DO-160G characterization with no supplier-backed traceability. The LSM6DSO32 improves at
+25°C, but temperature behavior is uncharacterized. If the LSM6DS3 coefficient remains in
`data_formatter.v` after the swap, the overcompensation produces −37.5 mg residual bias at
50 g_rms — equivalent to −2.2° systematic pitch error in flight. The overcorrection is in
the opposite direction from the true VRE. This is not a conservative interim state.

**Risk:** HIGH — systematic attitude error during flight vibration, invisible at bench.  
**Required:** DO-160G test at −40°C / +25°C / +85°C before `data_formatter.v` can be updated.

---

## Required Changes (conditional on H-001 ruling)

1. **`config_rom.v`** — update for LSM6DSO32:
   - `WHO_AM_I_EXPECTED = 8'h6C`  
     `// Traces to: Init Handshake (Amendment 01 primitive 3), ST DS13495 Table`
   - `CTRL1_XL_FS = 2'b10` (sets ±8g on DSO32; review sensitivity tradeoff)  
     `// Traces to: ODR / FS Range (Amendment 01 primitive 4), CTRL1_XL Table DS13495`

2. **`data_formatter.v`** — update VRE compensation table after DO-160G test:
   - Coefficients from LSM6DSO32 characterization at −40°C, +25°C, +85°C only
   - `// Traces to: VRE (Amendment 01 primitive 5), do160g_lsm6dso32.pdf`
   - **DO NOT update before Condition C-3 is complete**

3. **`device_context.md`** — update BOM, test results, VRE measured values after test

4. **Traceability matrix** — update sensor part number and VRE source document reference

---

## Changes that do NOT require a Hearing (pre-approved Standing Orders)

- Procuring LSM6DSO32 breakout boards for bench testing
- Reading WHO_AM_I register to confirm SPI communication (confirms C-1)
- Running existing regression suite against new sensor at +25°C bench conditions

---

## Conditions of approval (draft — subject to H-001 ruling)

- **C-1** WHO_AM_I_EXPECTED updated to 8'h6C; SPI WHO_AM_I read confirms 0x6C
- **C-2** FS range bits updated; attitude verified at known reference angle (error < ±0.5°)
- **C-3** DO-160G Cat B vibration at −40°C / +25°C / +85°C; VRE committed to device_context.md
- **C-4** `data_formatter.v` VRE coefficients from C-3 data only; Article I citation per line
- **C-5** Human approval required for any build flashed before C-3 complete (Article II)

**To advance:** `/judicial hear "LSM6DS3 to LSM6DSO32 sensor substitution, DAL C DCU" safety vs risk`
