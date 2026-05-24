"""
Library auto-pin for /toolchain init and /toolchain detect.

Queries arduino-cli for the latest stable version of a named library
so the user doesn't have to look it up manually.
"""

import re
import subprocess
from typing import Optional


def resolve(library_name: str) -> Optional[str]:
    """
    Returns the latest stable version string for the given Arduino library,
    or None if arduino-cli is not available or the library is not found.
    """
    try:
        result = subprocess.run(
            ['arduino-cli', 'lib', 'search', library_name, '--format', 'text'],
            capture_output=True, text=True, timeout=15
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None

    if result.returncode != 0:
        return None

    # Parse "Version: X.Y.Z" from the first matching library block
    versions = re.findall(r'Version:\s*(\d+\.\d+[\.\d]*)', result.stdout)
    if not versions:
        return None

    # Return the highest version found (simple string sort is sufficient for semver)
    versions_sorted = sorted(versions, key=lambda v: [int(x) for x in v.split('.')])
    return versions_sorted[-1]


def resolve_all(library_names: list[str]) -> dict[str, Optional[str]]:
    """
    Resolve multiple libraries. Returns {name: version_or_None}.
    """
    return {name: resolve(name) for name in library_names}


def format_suggestion(name: str, version: Optional[str]) -> str:
    if version:
        return f"[AUTO-PINNED — confirm] {name} v{version} (latest stable via arduino-cli)"
    return f"[MANUAL — arduino-cli not available] {name} — enter version manually"
