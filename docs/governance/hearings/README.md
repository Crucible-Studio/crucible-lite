# Fragmented Hearing Records

Each Judicial Hearing gets its own file: `H-NNN_short-name.md`.
The `MANIFEST.md` is a machine-readable index used by enforcement checks.

## File naming

```
H-001_sample-rate-calibration.md
H-002_pvdf-transduction-model.md
```

## Required file structure

Every hearing file must contain all three of these sections. A file missing any
section is an incomplete (informal) ruling and will be flagged by the police agent
as JUDICIAL-INDEPENDENCE-VIOLATION.

```markdown
# Hearing H-NNN: <Name>
*Date: YYYY-MM-DD*
*Files: src/signals.py, src/algorithm.py*
*Amendment: 12*

## Attorney-A argued:
[Full argument — position assigned at hearing declaration]

## Attorney-B argued:
[Full argument — opposing position]

## Justice ruled:
[Ruling — written by the Justice, not by either attorney]
[Must state: authorized / not authorized / requires further evidence]
```

## When to create a new hearing file

A new hearing file is required whenever `src/signals.py` or `src/algorithm.py` will
be changed. The hearing must be completed (all three sections) and the MANIFEST.md
row added before any commit touching those files is permitted.

## MANIFEST.md format

The MANIFEST is parsed by `corpus.py` and `bash_write_guard.py`. It must remain a
valid Markdown table. The Has-A / Has-B / Has-J columns must be exactly `TRUE` or
`FALSE` (uppercase). The Status column must be `OPEN` or `CLOSED`.

To add a row after a hearing is complete, append to the table in MANIFEST.md:
```
| H-NNN | Hearing Name | YYYY-MM-DD | src/signals.py | TRUE | TRUE | TRUE | OPEN |
```

## Relationship to case_law.md

During migration, both layouts coexist. `CorpusGraph` reads fragmented files first,
then reads `case_law.md` for entries not yet migrated. Over time all new hearings
should be recorded here rather than in the monolithic `case_law.md`.
