# Amendment 5 — Simulation is the Hardware Proxy
*Traces to: Article I + II*
*Status: PROPOSED — ratify when Stage 1 begins*

If something cannot be tested in simulation, a simulation test must be written first.
Hardware results that deviate from simulation predictions are evidence of a hardware or
mounting problem — not a firmware problem — unless the corresponding simulation test
was never written.

The handoff document (`docs/governance/handoff.md`) is the binding prediction set
against which hardware results are compared at each stage gate.
