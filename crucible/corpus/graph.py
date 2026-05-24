"""
CorpusGraph — governance knowledge graph.

Parses governance documents into typed nodes and edges. Enforcement checks query
the graph instead of running regex over monolithic Markdown, which closes the
"well-crafted comment" bypass and enables structural validation of Hearing entries.

Node types:
  Amendment  — a ratified or proposed amendment
  Primitive  — a domain primitive named in Amendment 1
  Hearing    — a Judicial Hearing (complete or incomplete)
  SourceFile — a source file governed by Article I / Amendment 12

Edges (represented as attributes on nodes):
  Amendment.governs        → set of SourceFile paths
  Hearing.files_covered    → set of SourceFile paths
  Hearing.amendment_refs   → set of Amendment numbers cited
  Primitive.amendment      → Amendment number
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ─── Node types ───────────────────────────────────────────────────────────────

@dataclass
class Primitive:
    name: str
    amendment: int = 1

    def matches(self, text: str) -> bool:
        return self.name.lower() in text.lower()


@dataclass
class Amendment:
    number: int
    title: str
    status: str          # RATIFIED | PROPOSED | NOT YET RATIFIED
    traces_to: str
    primitives: list[Primitive] = field(default_factory=list)
    governs: set[str] = field(default_factory=set)   # SourceFile paths


@dataclass
class Hearing:
    id: str              # e.g. "H-001"
    name: str
    date: str
    files_covered: set[str] = field(default_factory=set)
    amendment_refs: set[int] = field(default_factory=set)
    has_attorney_a: bool = False
    has_attorney_b: bool = False
    has_justice_ruled: bool = False

    def is_complete(self) -> bool:
        return self.has_attorney_a and self.has_attorney_b and self.has_justice_ruled

    def missing_sections(self) -> list[str]:
        missing = []
        if not self.has_attorney_a:
            missing.append('Attorney-A argued')
        if not self.has_attorney_b:
            missing.append('Attorney-B argued')
        if not self.has_justice_ruled:
            missing.append('Justice ruled')
        return missing

    def covers_layer2(self) -> bool:
        layer2 = {'src/signals.py', 'src/algorithm.py'}
        return bool(self.files_covered & layer2) or any(
            re.search(r'signals\.py|algorithm\.py|Layer\s*2', f, re.IGNORECASE)
            for f in self.files_covered
        )


# ─── Graph ────────────────────────────────────────────────────────────────────

class CorpusGraph:
    """Governance knowledge graph built from docs/governance/ documents."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.amendments: dict[int, Amendment] = {}
        self.hearings: dict[str, Hearing] = {}
        self._build()

    def _build(self) -> None:
        self._parse_amendments()
        self._parse_hearings()

    # ── Amendment parsing ─────────────────────────────────────────────────────

    def _parse_amendments(self) -> None:
        """Parse amendments from fragmented directory first, fall back to monolithic."""
        amend_dir = self.repo_root / 'docs' / 'governance' / 'amendments'
        if amend_dir.exists():
            self._parse_fragmented_amendments(amend_dir)
        else:
            self._parse_monolithic_amendments()

    def _parse_fragmented_amendments(self, amend_dir: Path) -> None:
        """Parse from MANIFEST.md index + individual amendment files."""
        manifest = amend_dir / 'MANIFEST.md'
        if manifest.exists():
            self._parse_amendment_manifest(manifest, amend_dir)
            return
        # No manifest — scan files directly.
        for f in sorted(amend_dir.glob('amendment_*.md')):
            amend = self._parse_amendment_file(f)
            if amend:
                self.amendments[amend.number] = amend

    def _parse_amendment_manifest(self, manifest: Path, amend_dir: Path) -> None:
        """Parse MANIFEST.md table and load individual amendment files."""
        text = manifest.read_text()
        for line in text.splitlines():
            if not line.startswith('|') or line.startswith('| #') or line.startswith('|---'):
                continue
            cols = [c.strip() for c in line.strip('|').split('|')]
            if len(cols) < 5:
                continue
            num_raw, title, status, traces, filename = cols[:5]
            try:
                number = int(num_raw.strip())
            except ValueError:
                continue
            amend = Amendment(
                number=number,
                title=title.strip(),
                status=status.strip(),
                traces_to=traces.strip(),
            )
            # Load the full file to get primitives and any extra content.
            amend_file = amend_dir / filename.strip()
            if amend_file.exists():
                self._enrich_amendment_from_file(amend, amend_file)
            if number == 12:
                amend.governs = {'src/signals.py', 'src/algorithm.py'}
            self.amendments[number] = amend

    def _parse_amendment_file(self, path: Path) -> Optional[Amendment]:
        """Parse a single amendment_NN_slug.md file."""
        text = path.read_text()
        num_m = re.match(r'amendment_(\d+)_', path.stem)
        if not num_m:
            return None
        number = int(num_m.group(1))
        title_m = re.match(r'#\s+Amendment\s+\d+\s+[—–-]\s*(.+)', text)
        title = title_m.group(1).strip() if title_m else f'Amendment {number}'
        traces = ''
        traces_m = re.search(r'\*Traces to:\s*([^\*\n]+)', text)
        if traces_m:
            traces = traces_m.group(1).strip()
        status = 'RATIFIED'
        if 'NOT YET RATIFIED' in text:
            status = 'NOT YET RATIFIED'
        elif 'PROPOSED' in text:
            status = 'PROPOSED'
        amend = Amendment(number=number, title=title, status=status, traces_to=traces)
        self._enrich_amendment_from_file(amend, path)
        if number == 12:
            amend.governs = {'src/signals.py', 'src/algorithm.py'}
        return amend

    def _enrich_amendment_from_file(self, amend: Amendment, path: Path) -> None:
        """Extract primitives (Amendment 1 only) from the amendment file body."""
        if amend.number != 1 or amend.status != 'RATIFIED':
            return
        text = path.read_text()
        names = re.findall(r'^\s*\d+\.\s+([A-Z][^\(]+)', text, re.MULTILINE)
        amend.primitives = [Primitive(name=n.strip()) for n in names]

    def _parse_monolithic_amendments(self) -> None:
        """Fallback: parse docs/governance/amendments.md (pre-fragmentation layout)."""
        path = self.repo_root / 'docs' / 'governance' / 'amendments.md'
        if not path.exists():
            return
        text = path.read_text()
        blocks = re.split(r'\n(?=### Amendment \d+)', text)
        for block in blocks:
            m = re.match(r'### Amendment (\d+)[^\n]*\n', block)
            if not m:
                continue
            number = int(m.group(1))
            title_match = re.match(r'### Amendment \d+\s+[—–-]?\s*(.*)', block)
            title = title_match.group(1).strip() if title_match else f'Amendment {number}'
            traces = ''
            traces_m = re.search(r'\*Traces to:\s*([^\*\n]+)', block)
            if traces_m:
                traces = traces_m.group(1).strip()
            status = 'RATIFIED'
            if 'NOT YET RATIFIED' in block:
                status = 'NOT YET RATIFIED'
            elif 'PROPOSED' in block:
                status = 'PROPOSED'
            amend = Amendment(number=number, title=title, status=status, traces_to=traces)
            if number == 1 and status == 'RATIFIED':
                names = re.findall(r'^\s*\d+\.\s+([A-Z][^\(]+)', block, re.MULTILINE)
                amend.primitives = [Primitive(name=n.strip()) for n in names]
            if number == 12:
                amend.governs = {'src/signals.py', 'src/algorithm.py'}
            self.amendments[number] = amend

    # ── Hearing parsing ───────────────────────────────────────────────────────

    def _parse_hearings(self) -> None:
        """Parse hearings from fragmented files first, fall back to case_law.md."""
        hearings_dir = self.repo_root / 'docs' / 'governance' / 'hearings'
        if hearings_dir.exists():
            self._parse_fragmented_hearings(hearings_dir)
        self._parse_monolithic_case_law()

    def _parse_fragmented_hearings(self, hearings_dir: Path) -> None:
        """Parse individual hearing files (H-NNN_name.md)."""
        manifest = hearings_dir / 'MANIFEST.md'
        if manifest.exists():
            self._parse_manifest(manifest, hearings_dir)
            return
        # No manifest — scan files directly.
        for f in sorted(hearings_dir.glob('H-*.md')):
            hearing = self._parse_hearing_file(f)
            if hearing:
                self.hearings[hearing.id] = hearing

    def _parse_manifest(self, manifest: Path, hearings_dir: Path) -> None:
        """Parse MANIFEST.md table and load referenced hearing files."""
        text = manifest.read_text()
        for line in text.splitlines():
            if not line.startswith('|') or line.startswith('| ID') or line.startswith('|---'):
                continue
            cols = [c.strip() for c in line.strip('|').split('|')]
            if len(cols) < 7:
                continue
            hid, name, date, files_raw, has_a, has_b, has_j = cols[:7]
            hid = hid.strip()
            if not re.match(r'H-\d+', hid):
                continue
            hearing = Hearing(
                id=hid,
                name=name.strip(),
                date=date.strip(),
                files_covered=set(f.strip() for f in files_raw.split(',') if f.strip()),
                has_attorney_a=(has_a.strip().upper() == 'TRUE'),
                has_attorney_b=(has_b.strip().upper() == 'TRUE'),
                has_justice_ruled=(has_j.strip().upper() == 'TRUE'),
            )
            # Load full file if it exists to get amendment refs.
            hearing_file = hearings_dir / f'{hid}.md'
            if not hearing_file.exists():
                # Try glob for name-suffixed file.
                matches = list(hearings_dir.glob(f'{hid}_*.md'))
                if matches:
                    hearing_file = matches[0]
            if hearing_file.exists():
                self._enrich_from_file(hearing, hearing_file)
            self.hearings[hid] = hearing

    def _parse_hearing_file(self, path: Path) -> Optional[Hearing]:
        """Parse a single hearing file."""
        text = path.read_text()
        # Extract ID from filename.
        hid_m = re.match(r'(H-\d+)', path.stem)
        if not hid_m:
            return None
        hid = hid_m.group(1)
        name_m = re.search(r'^#\s+Hearing.*?:\s*(.+)$', text, re.MULTILINE)
        name = name_m.group(1).strip() if name_m else hid
        date_m = re.search(r'\*Date:\s*([^\*\n]+)', text)
        date = date_m.group(1).strip() if date_m else ''
        files_m = re.search(r'\*Files?:\s*([^\*\n]+)', text)
        files: set[str] = set()
        if files_m:
            files = set(f.strip() for f in files_m.group(1).split(',') if f.strip())
        hearing = Hearing(id=hid, name=name, date=date, files_covered=files)
        self._enrich_from_file(hearing, path)
        return hearing

    def _enrich_from_file(self, hearing: Hearing, path: Path) -> None:
        """Set structural section flags and extract amendment refs from file content."""
        text = path.read_text()
        hearing.has_attorney_a = bool(re.search(
            r'^##\s+Attorney[-\s]A\s+(argued|position)', text, re.IGNORECASE | re.MULTILINE
        ))
        hearing.has_attorney_b = bool(re.search(
            r'^##\s+Attorney[-\s]B\s+(argued|position)', text, re.IGNORECASE | re.MULTILINE
        ))
        hearing.has_justice_ruled = bool(re.search(
            r'^##\s+Justice\s+(ruled|ruling)', text, re.IGNORECASE | re.MULTILINE
        ))
        # Files mentioned in the body.
        body_files = re.findall(r'src/(?:signals|algorithm|events|analysis|plot)\.py', text)
        hearing.files_covered.update(body_files)
        # Layer 2 shorthand.
        if re.search(r'Layer\s*2', text, re.IGNORECASE):
            hearing.files_covered.update({'src/signals.py', 'src/algorithm.py'})
        # Amendment references.
        for m in re.finditer(r'Amendment\s+(\d+)', text, re.IGNORECASE):
            hearing.amendment_refs.add(int(m.group(1)))

    def _parse_monolithic_case_law(self) -> None:
        """Parse case_law.md for hearing entries not already loaded from files."""
        path = self.repo_root / 'docs' / 'governance' / 'case_law.md'
        if not path.exists():
            return
        text = path.read_text()
        # Split on Hearing headers: ## Hearing H-NNN or ## H-NNN
        blocks = re.split(r'\n(?=##\s+(?:Hearing\s+)?H-\d+)', text)
        for block in blocks:
            hid_m = re.search(r'##\s+(?:Hearing\s+)?(H-\d+)', block)
            if not hid_m:
                continue
            hid = hid_m.group(1)
            if hid in self.hearings:
                continue  # already loaded from fragmented file
            name_m = re.search(r'##\s+(?:Hearing\s+)?H-\d+[:\s]+(.+)', block)
            name = name_m.group(1).strip() if name_m else hid
            date_m = re.search(r'\*?Date:\s*([^\*\n]+)', block)
            date = date_m.group(1).strip() if date_m else ''
            hearing = Hearing(id=hid, name=name, date=date)
            # Reuse file enrichment logic on the block text.
            class _FakePath:
                def read_text(self_):  # noqa: N805
                    return block
            self._enrich_from_file(hearing, _FakePath())  # type: ignore[arg-type]
            self.hearings[hid] = hearing

    # ── Query helpers ─────────────────────────────────────────────────────────

    def primitives(self) -> list[Primitive]:
        a1 = self.amendments.get(1)
        return a1.primitives if a1 else []

    def amendment_1_ratified(self) -> bool:
        a1 = self.amendments.get(1)
        return bool(a1 and a1.status == 'RATIFIED' and a1.primitives)

    def valid_layer2_hearings(self) -> list[Hearing]:
        """Return complete Hearings that cover src/signals.py or src/algorithm.py."""
        return [h for h in self.hearings.values() if h.is_complete() and h.covers_layer2()]

    def incomplete_hearings(self) -> list[Hearing]:
        return [h for h in self.hearings.values() if not h.is_complete()]
