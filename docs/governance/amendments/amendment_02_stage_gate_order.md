# Amendment 2 — Stage Gate Order
*Traces to: Article I + II*
*Status: PROPOSED — ratify by removing this line*

Development proceeds through exactly these stages in order, and no stage begins
until the previous stage's exit criteria are explicitly confirmed by the human:

  Spec Gate → Stage 0 (HIL Toolchain Lock) → Stage 1 (Simulation) →
  Stage 2 (Firmware Integration) → Stage 3 (Field Test) → Stage 4 (Host Integration)

An agent must not begin Stage N+1 work while Stage N has any open failure, even one
that appears unrelated to the next stage's work. Each stage's errors become
exponentially more expensive to fix in later stages. Hardware is a validation tool,
not a debugging tool.

**Exit criteria for each stage are defined in `/session`.**
**Stage closeout is executed by `stage-compactor`.**
