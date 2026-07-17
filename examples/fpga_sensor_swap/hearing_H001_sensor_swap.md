# H-001 — Judicial Hearing: LSM6DS3 to LSM6DSO32 Sensor Substitution (DAL C DCU)

**Hearing name:** LSM6DS3 to LSM6DSO32 sensor substitution, DAL C DCU  
**Date:** 2026-07-16  
**Attorney-A position:** Substitution is safe — three primitives unchanged, two have clear bounded fixes  
**Attorney-B position:** FS range encoding change is a silent corruption risk; VRE cannot be approved without characterization data at temperature  
**Evidence:** Bill B-001, device_context.md, domain_primitives.md, ST datasheet DS13495 (LSM6DSO32), ST datasheet DocID026899 Rev 10 (LSM6DS3)

---

## Attorney-A argued:

This is a same-vendor, same-family substitution. The interface continuity is strong: SPI
mode, VDDIO, operating frequency, ODR encoding, and INT1 polarity are all unchanged. The
Crucible governance system caught the critical register difference — WHO_AM_I — at bill
submission time, before any hardware was touched. This is the system working as intended.
The fix is a single constant, verifiable by SPI read, traceable to two ST datasheets.

On Primitive 3 (WHO_AM_I): Condition C-1 is sufficient. Read WHO_AM_I over SPI, confirm
0x6C, update the constant. This is not a novel engineering judgment — it is a documented
register value from the production datasheet. The governed toolchain caught it in under a
minute. An ungoverned swap would have caught it after half a day with a logic analyzer.

On Primitive 4 (FS range): The FS encoding change is real but bounded. CTRL1_XL FS bits
are a two-bit field at a documented register address. The correction is: update the bits,
update the sensitivity constant in `data_formatter.v`, verify attitude output at a known
reference angle. A condition requiring reference-angle verification contains the risk. This
is not a hidden failure mode — it is a documented register map difference between two parts
whose datasheets are on record.

On Primitive 5 (VRE): The +25°C improvement is consistent with the direction of the DSO
family's vibration robustness improvements. A condition gating `data_formatter.v` on
DO-160G test results is appropriate. Maintaining the existing LSM6DS3 coefficient as interim
is conservative in the sense that it overcorrects rather than undercorrects — the system
attitude output will drift slightly, but the sensor data path is functional and delivering
attitude estimates within testing range while characterization is completed.

Conclusion: Approve with five conditions. WHO_AM_I and FS fixes may begin immediately
under C-1 and C-2. `data_formatter.v` VRE update is gated on C-3.

---

## Attorney-B argued:

I accept that WHO_AM_I was caught correctly by the Crucible toolchain. That is exactly the
case that P-001 should establish. My concerns are with the items that were not caught
automatically and require engineering judgment to evaluate correctly.

On Primitive 4 (FS range encoding): Attorney-A calls this "bounded." I need to be precise
about the failure mode. The sensor outputs data. WHO_AM_I check passes (after C-1 update).
The attitude estimate numerically converges. The display shows a plausible pitch angle.
Every power-on self-test passes. The error — all accelerometer readings at half true
sensitivity — is only detectable by placing the board at a known reference angle and
comparing the estimate. In a program without an explicit attitude reference test in the
regression suite, this defect ships.

The FS range change also affects noise floor. LSM6DS3 at ±2g: noise density ~90 µg/√Hz.
LSM6DSO32 at ±4g minimum: noise density ~130 µg/√Hz — 44% higher. For a DAL C attitude
function, this must be evaluated against the error budget, not assumed benign.

Condition C-2 must require attitude output at a known reference angle — not just a register
read confirming the bits were written correctly. A register read does not exercise the
sensitivity scaling path in `data_formatter.v`.

On Primitive 5 (VRE): Attorney-A's "conservative interim" framing is incorrect and I need
to correct it on the record. The LSM6DS3 coefficient is 70 µg/g². The LSM6DSO32 true VRE
is 55 µg/g². If the 70 µg/g² coefficient is applied to LSM6DSO32 output at 50 g_rms
structural resonance, the overcorrection is: (70 − 55) × 2500 = 37,500 µg = 37.5 mg.
The sign of this residual is negative — the compensation subtracts more than the actual
VRE. The result is a −2.2° systematic pitch bias. This is not a conservative drift in
the safe direction. It is a 4× exceedance of the ±0.5° DAL C error budget, in a direction
that could cause an instrument to under-read pitch during a nose-up attitude.

Any build combining LSM6DSO32 `config_rom.v` with LSM6DS3 VRE compensation is a
hazard-creating intermediate state. Article II must cover flashing such builds to any
test article, without exception.

Conclusion: Approve with five conditions, with C-3 (DO-160G test) mandatory and
non-advisory, C-2 strengthened to require reference-angle attitude verification, and
C-5 (Article II gate on intermediate builds) explicitly binding.

---

## Justice ruled:

**APPROVED WITH FIVE CONDITIONS.**

Attorney-A prevails on Primitive 3. The WHO_AM_I case is clear: the Crucible toolchain
caught the mismatch at change submission time using the two production datasheets. The fix
is a single constant with datasheet-traceable source. This is the reference case for
Precedent P-001: governed toolchains catch identity mismatches before hardware is touched.

Attorney-B prevails on Primitive 4. The failure mode — correct WHO_AM_I, plausible
output, silent 2× sensitivity error at all pitch angles — is the most dangerous class of
substitution defect because it passes all non-reference tests. Condition C-2 is therefore
strengthened: FS verification requires attitude output at a known reference angle, not
register write confirmation alone. The noise floor increase (90 → 130 µg/√Hz) must be
evaluated against the DAL C error budget before C-2 can be closed.

Attorney-B prevails on Primitive 5 on Article I grounds. The LSM6DS3 VRE coefficient
of 70 µg/g² is not a valid citation for LSM6DSO32 behavior. The overcompensation
direction (−37.5 mg residual, −2.2° systematic bias at 50 g_rms) means the interim state
is not conservative — it is a different class of wrong. Calling it "conservative" is
rejected as a valid governance characterization. C-3 is mandatory.

**Conditions of approval (binding):**

**C-1** — WHO_AM_I_EXPECTED updated to 8'h6C in `config_rom.v`. SPI WHO_AM_I read at 2 MHz
confirmed 0x6C. Evidence committed to `device_context.md` Test Results before merge.
Citation in RTL: `// Traces to: Init Handshake (Amendment 01 primitive 3), ST DS13495 Table`.

**C-2** — CTRL1_XL FS bits updated in `config_rom.v` (2'b00 → 2'b10). Sensitivity
constant updated in `data_formatter.v`. Attitude output verified at ±10° reference angle
using phone inclinometer; error < ±0.5° DAL C budget at both polarities. Noise floor
evaluated against system error budget allocation. Evidence committed before merge.
Citation: `// Traces to: ODR / FS Range (Amendment 01 primitive 4), CTRL1_XL Table DS13495`.

**C-3** — DO-160G Category B vibration test performed on LSM6DSO32 at −40°C, +25°C,
and +85°C. VRE measured at each temperature. Results committed to `device_context.md`
Test Results and `do160g_lsm6dso32.pdf` before `data_formatter.v` VRE coefficients are modified.

**C-4** — VRE compensation table in `data_formatter.v` derived exclusively from C-3
measured data. Article I citation on every coefficient line:
`// Traces to: VRE (Amendment 01 primitive 5), do160g_lsm6dso32.pdf`.
Code-reviewer sign-off required before merge.

**C-5** — Any firmware build combining LSM6DSO32 `config_rom.v` with LSM6DS3 VRE
compensation coefficients must be tagged `VRE_UNVALIDATED=1` in build metadata. Flashing
such a build to any test article requires explicit human approval under Article II. This
condition expires when C-3 is complete and `data_formatter.v` is updated.

**This Hearing is COMPLETE.** All three sections (A, B, Justice) are non-empty.
Add row to `docs/governance/hearings/MANIFEST.md`:
`H-001 | LSM6DS3 to LSM6DSO32 substitution DAL C DCU | 2026-07-16 | complete | TRUE | TRUE | TRUE`
