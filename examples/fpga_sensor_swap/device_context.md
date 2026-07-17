# Device Context — Avionics FPGA Sensor Swap Demo

**Program:** DAL C Data Concentrator Unit (DCU) — attitude data acquisition function  
**Dev proxy:** Intel MAX 10 Eval Kit (EK-10M08E144) — no hard ARM core; algorithm runs on host PC  
**Current sensor:** ST Microelectronics LSM6DS3 MEMS IMU (Adafruit breakout, #4503)  
**Proposed sensor:** ST Microelectronics LSM6DSO32 MEMS IMU (Adafruit breakout, #4692)  
**Applicable standards:** DO-254 Level C, DO-160G (environmental qualification)  
**Classification:** DAL C — flight data function; not primary flight control

---

## Device Purpose

This DCU front-end acquires 6-axis inertial data (accelerometer + gyroscope) from a
MEMS IMU connected via Arduino headers, and streams raw samples over UART at 115200 baud
(proxy for ARINC-429 on the production LRU).

The MAX 10 FPGA handles the SPI front-end, interrupt-driven sample capture, and UART output.
There is no hard ARM core — the complementary filter (algorithm.py) runs on the host PC,
receiving raw samples over USB-Serial. This mirrors a production LRU where the FPGA front-end
feeds a separate processing unit.

**Failure modes and severity:**
- **Silent data corruption** (wrong scale factor or VRE compensation): DAL C — hazardous
  if attitude data feeds display; affects crew situational awareness
- **Data gap** (dropped sample, FIFO overflow): DAL C — minor; detected by downstream
  health monitor as gap in sequence number
- **No data** (IMU not responding): DAL C — detected; DCU flags sensor fail; redundant
  source activated

**Domain primitives** (traces to Amendment 01):
1. SPI Clock Frequency (Hz) — governs RTL clock divider; operating point held at 2 MHz
2. VDDIO Voltage (V) — governs FPGA I/O standard; both sensors: 3.3V (LVCMOS33)
3. Interrupt Latency (µs) — governs FIFO depth; polarity differs between sensors
4. Output Data Rate (Hz) — governs bus slot allocation; operating point held at 2 kHz
5. Vibration Rectification Error (µg/g²) — governs VRE compensation table; changes on swap

---

## Operating Envelope

- **Normal conditions:** Airborne, −40°C to +70°C, 0–55,000 ft altitude, 28V DC aircraft power
- **Worst-case (DO-160G):** Cat B vibration (0.04 g²/Hz, 10–2000 Hz), Cat A temperature
  (−55°C cold soak, +85°C operating), 50,000 ft altitude, 100V spike on power input
- **Out-of-scope:** Lightning strike (covered by separate LRU shielding), liquid immersion

---

## System Constraints (DO-254 hardware requirements)

| Constraint | Value | Implication |
|-----------|-------|-------------|
| DAL | Level C | Three DO-254 objectives: planning, design, verification |
| FPGA assurance | DO-254 Level C | RTL changes require design review and regression test evidence |
| Environmental | DO-160G | Any sensor substitution must match or improve DO-160G qualification |
| Power | 28V DC, 3W max for sensor front-end | Adafruit breakout has onboard LDO; no auxiliary rail required |
| Operating temp | −40°C to +85°C | Sample buffer depth must be verified at temp extremes |
| MTBF requirement | ≥ 50,000 hours | Sensor substitution must not degrade system MTBF |
| Bus interface | ARINC-429 (production), UART proxy (dev) | ODR must stay at 2 kHz; bus slot allocation fixed |

---

## Bill of Materials (BOM)

| Component | Part | Supplier | Unit Price | Notes |
|-----------|------|---------|-----------|-------|
| FPGA board | MAX 10 Eval Kit (EK-10M08E144) | DigiKey CA | ~$80 CAD | Intel MAX 10 8K LE; Arduino headers; algorithm runs on host PC |
| IMU (current) | LSM6DS3 breakout (#4503) | Adafruit | ~$7 CAD | ST Micro; 2014-gen; approaching EOL; SPI mode 3, 3.3V |
| IMU (proposed) | LSM6DSO32 breakout (#4692) | Adafruit | ~$11 CAD | ST Micro; current-gen; ±32g range; SPI mode 3, 3.3V |
| Jumper wires | M-F 6" jumper wire | SparkFun | ~$5 CAD | 6 per sensor to Arduino headers |
| **Total** | | | **~$103 CAD** | |

**Why this pair for the governance demo:**
LSM6DS3 is ST Micro's 2014-generation IMU — still in production but approaching natural EOL
as the product line migrates to the DSO-series. LSM6DSO32 is the current-generation replacement
from the same vendor. Same SPI interface family, same 3.3V logic, but different register map
(requires `config_rom.v` update) and different VRE (requires `data_formatter.v` update).
Neither sensor publishes VRE — both compensation coefficients rely on internal characterization.
Same-vendor substitution makes the governance case harder to dismiss: the audience cannot say
"obviously you need governance for cross-vendor swaps." The answer is: same vendor, same family,
still triggered a Hearing.

**MTBF (MIL-HDBK-217F, +40°C ground benign — estimated, COTS parts):**
- LSM6DS3: ~160,000 hours
- LSM6DSO32: ~190,000 hours
- Delta: +19% improvement.

---

## Hardware Interface

### Arduino Header Pin Assignment (LSM6DS3 and LSM6DSO32 — same SPI signals, jumper wires)

| Arduino Pin | Signal | MAX 10 GPIO | Direction | I/O Standard | Notes |
|------------|--------|------------|-----------|-------------|-------|
| D10 | SPI_CS_N | PIN_91 | OUT | 3.3V LVCMOS | Active-low chip select |
| D11 | MOSI | PIN_90 | OUT | 3.3V LVCMOS | |
| D12 | MISO | PIN_89 | IN | 3.3V LVCMOS | |
| D13 | SCLK | PIN_88 | OUT | 3.3V LVCMOS | 2 MHz operating point |
| D2 | INT (data ready) | PIN_69 | IN | 3.3V LVCMOS | Both sensors: INT1 active-high by default (CTRL3_C H_LACTIVE=0) — unchanged |
| GND | GND | — | PWR | — | |
| 3.3V | VDD | — | PWR | — | Both sensors: 3.3V (breakout has onboard LDO) |

**I/O standard: 3.3V LVCMOS — unchanged between sensors.**  
**SPI mode: Mode 3 (CPOL=1, CPHA=1) — same for both sensors.**  
**Toolchain:** Intel Quartus Prime Lite (free). Constraints in `.qsf` (not XDC).  
**Algorithm:** Runs on host PC via `demo_run.py` — MAX 10 streams samples over UART (USB-Serial on Arduino header).  
**Swap:** Unplug 6 jumper wires, plug 6 jumper wires. 30 seconds.

---

## System Architecture (MAX 10 FPGA + Host PC)

```
                ┌──────────────── MAX 10 FPGA ─────────────────┐
[Arduino D10-13,D2]──►[SPI Master]──►[Sample Buffer]──►[UART Tx 115200]
     2 MHz            SPI Mode 3      8 samples             ↓
                           ▲          (2 kHz, 2 ms)    [USB-Serial]
                      [Config ROM]                           ↓
                       startup seq                    [Host PC — algorithm.py]
                           ▲                          Complementary Filter
                     [WHO_AM_I check]                 roll / pitch estimate
                      0x69 expected
                      ← CHANGES on swap                (proxy for ARINC-429)
                 └─────────────────────────────────────────────┘
```

**The WHO_AM_I check in config_rom.v is the primary demo failure point.**
The FPGA reads WHO_AM_I before enabling the sample buffer. LSM6DS3 returns 0x69 (expected).
LSM6DSO32 returns 0x6C (mismatch) → init halts → sample buffer never armed → no data.

**The system boundary that matters for VRE:**
The navigation filter (host PC) receives post-FPGA samples where broadband vibration
has been rejected by the FPGA hardware LP filter. VRE bias is DC — it passes through.
If data_formatter.v has the wrong VRE coefficient, the navigation filter integrates
false pitch as truth. This is the secondary failure mode (Demo Candidate B).

**RTL modules that change on sensor substitution:**
- `config_rom.v` — WHO_AM_I expected value, startup register sequence, FS range setting
- `data_formatter.v` — VRE coefficient table (must match installed sensor)

**RTL modules unchanged:**
- `spi_master.v` — clock divider stays at 2 MHz
- `sample_buf.v` — depth unchanged (8 samples, 2 ms latency budget)
- `uart_tx.v` — output format unchanged

**Navigation filter (host PC — `src/algorithm.py`):**
- Complementary filter, α = 0.98, corner f_c ≈ 6.4 Hz
- Traces to: ODR (Amendment 01 primitive 4)
- VRE DC bias on accel_x → false pitch via `atan2(-accel_x, √(ay²+az²))`
- DAL C attitude error budget: ±0.5°

---

## Test Results (current hardware — LSM6DS3)

| Test | Result | Date | Evidence |
|------|--------|------|---------|
| SPI WHO_AM_I read (0x0F) | PASS — 0x69 returned | 2026-07-16 | uart_log_whoami_lsm6ds3.txt |
| 6-axis stream at 2 kHz | PASS — 0 dropped samples, 120 s | 2026-07-16 | uart_log_stream_120s.txt |
| INT1 latency | 48 µs from edge to sample capture | 2026-07-16 | scope: int1_latency_lsm6ds3.png |
| Static bias (bench, 0g) | Accel: 1.1 mg, Gyro: 0.04 °/s | 2026-07-16 | uart_log_static_bias.txt |
| VRE (vibration table, DO-160G Cat B) | 70 µg/g² (accel), 7 mdeg/s per g² (gyro) | 2026-07-16 | do160g_lsm6ds3.pdf |

---

## DO-254 Change Impact Assessment (pre-Hearing summary)

| Item | Change? | DO-254 re-assurance required |
|------|---------|------------------------------|
| Hardware design data (RTL) | Yes — config_rom.v, data_formatter.v | Design review + regression test |
| Hardware requirements | No — functional requirements unchanged | None |
| Verification test cases | Yes — VRE test case values update | Regression with new sensor |
| Traceability matrix | Yes — new sensor part number, new VRE source | RTM update |
| FPGA tool qualification | No — same synthesis tool, same device | None |
| DO-160G qualification | Partial — VRE temperature data missing for LSM6DSO32 | Cat B vibration test at temp |

**Certification authority notification:** Not required for DAL C component change within
approved design change procedures. Change impact analysis (this Hearing record) is
sufficient evidence for the certification data package.
