"""
Pre-flight pin conflict checker for /toolchain validate.

Loads the board database and checks the declared pin map against known
shared-function pins for the active board.
"""

import json
import re
from pathlib import Path
from typing import Optional


def _load_board_db() -> list[dict]:
    db_path = Path(__file__).resolve().parents[2] / '.claude' / 'toolchain' / 'boards.json'
    if not db_path.exists():
        return []
    return json.loads(db_path.read_text()).get('boards', [])


def _find_board(board_name: str, db: list[dict]) -> Optional[dict]:
    name_lower = board_name.lower()
    for entry in db:
        if entry['name'].lower() in name_lower or name_lower in entry['name'].lower():
            return entry
    return None


def _extract_pin_map(toolchain_config_text: str) -> dict[str, list[str]]:
    """
    Parse the Pin Map table from toolchain_config.md.
    Returns {nrf_pin: [signal_names]} mapping.
    """
    pin_map: dict[str, list[str]] = {}
    in_pin_section = False
    for line in toolchain_config_text.splitlines():
        if '## Pin Map' in line or '## Pins' in line:
            in_pin_section = True
            continue
        if in_pin_section and line.startswith('## '):
            break
        if in_pin_section and '|' in line:
            cols = [c.strip() for c in line.split('|')]
            # Table rows: | Signal | Arduino | nRF pin | Function | ...
            if len(cols) >= 4:
                signal = cols[1] if len(cols) > 1 else ''
                nrf_pin = cols[3] if len(cols) > 3 else ''
                if nrf_pin and re.match(r'P[01]\.\d+', nrf_pin):
                    pin_map.setdefault(nrf_pin, []).append(signal)
    return pin_map


def check(toolchain_config_text: str) -> list[dict]:
    """
    Returns a list of findings: {severity, pin, message}
    Severity is always WARNING (user must confirm, not automatically an error).
    """
    findings = []
    db = _load_board_db()
    if not db:
        return findings

    # Extract board name from toolchain_config
    board_name = ''
    for line in toolchain_config_text.splitlines():
        if line.strip().startswith('- **Board:**') or line.strip().startswith('Board:'):
            board_name = re.sub(r'.*:\s*', '', line).strip()
            break

    if not board_name:
        return findings

    board = _find_board(board_name, db)
    if not board:
        return findings

    pin_map = _extract_pin_map(toolchain_config_text)
    declared_pins = set(pin_map.keys())

    for conflict in board.get('known_pin_conflicts', []):
        conflict_pin = conflict['pin']
        if conflict_pin in declared_pins:
            signals = pin_map[conflict_pin]
            findings.append({
                'severity': 'WARNING',
                'pin': conflict_pin,
                'message': (
                    f"Pin {conflict_pin} declared as '{', '.join(signals)}' — "
                    f"on {board['name']}, this pin is also used for: "
                    f"{', '.join(conflict['functions'])}. "
                    f"{conflict['warning']}"
                ),
            })

    return findings
