Ratify amendments interactively without manual file editing.

Usage: /governance ratify [amendment-number|all]

Examples:
  /governance ratify 2        — ratify Amendment 2 (Stage Gate Order)
  /governance ratify 1 2 3 4  — ratify multiple in sequence
  /governance ratify all      — ratify all PROPOSED amendments in order

---

## Subcommand: /governance ratify

Reads the specified amendment(s) from `docs/governance/amendments.md` and walks the
human through ratification with explicit yes/no confirmation per amendment.

**Step 1 — Load target amendments**

Parse "$ARGUMENTS" after "ratify". If the argument is "all", collect every amendment
whose Status line contains "PROPOSED". Otherwise collect the amendment number(s) listed.

If an amendment number is not found in amendments.md: print
  "Amendment [N] not found in docs/governance/amendments.md"
and skip it.

**Step 2 — For each amendment, in order:**

Print the full text of the amendment (everything from its `### Amendment N` header
to the `---` separator before the next amendment).

Then ask:
  "Ratify Amendment [N] — [Title]? (yes / no / skip)"

- **yes**: Remove the `*Status: PROPOSED[...]` line from the amendment text in
  `docs/governance/amendments.md`. Update the Amendment Index row for this amendment:
  change "PROPOSED" to "RATIFIED" in the Status column.
  Print: "Amendment [N] — [Title]: RATIFIED ✓"

- **no**: Print: "Amendment [N] — [Title]: NOT ratified. It remains PROPOSED."
  Continue to the next amendment.

- **skip**: Same as no — skip without ratifying.

**Step 3 — Print ratification summary**

After all requested amendments are processed:

```
══════════════════════════════════════════════════════════════
RATIFICATION COMPLETE
══════════════════════════════════════════════════════════════
  Ratified this session:  [list of amendment numbers and titles]
  Skipped / not ratified: [list, or "none"]
══════════════════════════════════════════════════════════════
```

If Amendments 2–4 are now all ratified, print:
  "Mandatory framework amendments ratified. Ready to run /session 0."

If Amendment 1 is ratified, print:
  "Domain primitives ratified. Article I enforcement is now active."

---

Now parse "$ARGUMENTS" and run the matching subcommand.
Valid subcommands: `ratify`.
If no subcommand given, print usage and stop.
