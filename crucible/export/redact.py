"""
Redaction layer for corpus outputs.

Any field tagged with <!-- redact --> (inline HTML comment) or [REDACT] in
source documents is replaced with [REDACTED] before external output.

Usage:
  from crucible.export.redact import redact

  safe_text = redact(raw_markdown)

Redaction is non-destructive — the original corpus files are never modified.
The redaction pass is applied by wiki/renderer.py before writing docs/wiki/,
and by transcript exporters before any external file is generated.

Tags recognised (case-insensitive):
  [REDACT]              — replaces the tagged token
  <!-- redact -->       — replaces the HTML comment and any value on the same line
  `value`  <!-- redact -->  — replaces the value before the comment
"""

import re


_INLINE_VALUE_COMMENT = re.compile(
    r'`([^`]+)`\s*<!--\s*redact\s*-->',
    re.IGNORECASE,
)

_BARE_COMMENT = re.compile(
    r'<!--\s*redact\s*-->.*',
    re.IGNORECASE,
)

_BRACKET_TAG = re.compile(
    r'\[REDACT\]',
    re.IGNORECASE,
)


def redact(text: str) -> str:
    """
    Apply all redaction passes to text.
    Returns a new string with sensitive values replaced by [REDACTED].
    """
    # Replace `value` <!-- redact --> → `[REDACTED]`
    text = _INLINE_VALUE_COMMENT.sub('`[REDACTED]`', text)
    # Replace bare <!-- redact --> (and rest of line) → [REDACTED]
    text = _BARE_COMMENT.sub('[REDACTED]', text)
    # Replace [REDACT] tokens
    text = _BRACKET_TAG.sub('[REDACTED]', text)
    return text


def redact_file(path) -> str:
    """Read a file and return its redacted contents without modifying it."""
    from pathlib import Path
    return redact(Path(path).read_text())
