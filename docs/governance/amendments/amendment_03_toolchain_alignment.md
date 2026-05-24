# Amendment 3 — Toolchain Alignment
*Traces to: Article II*
*Status: PROPOSED — ratify by removing this line*

Every agent working on this project must operate within the toolchain that is currently
active and recorded in `docs/toolchain_config.md`. No agent may introduce a new
toolchain, framework, or build system without a Bill enacted through the Legislative
Process. Switching toolchains mid-stage is not permitted — it requires a new stage gate.

The active toolchain record in `docs/toolchain_config.md` is the single source of truth
for all build, flash, and test operations. An agent that silently switches from the active
toolchain to a different one violates Article II regardless of whether the output compiles.

A blocked toolchain may only be re-activated by explicit human decision at a stage gate,
recorded in toolchain_config.md with a date and reason.
