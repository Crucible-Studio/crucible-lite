from typing import Optional
#!/usr/bin/env python3
"""
Crucible session transcript exporter.

Converts a Claude Code JSONL session file into a readable markdown transcript
showing the natural conversation, agent interactions, and physics parameters
established during the session.

Usage:
    python scripts/export-session.py                          # most recent session
    python scripts/export-session.py <path/to/session.jsonl>  # specific session
    python scripts/export-session.py --project gait-device    # named project

Output:
    docs/governance/session-transcripts/YYYY-MM-DD-<slug>.md
"""

import json
import re
import sys
import os
from datetime import datetime, timezone
from pathlib import Path


# ── Helpers ──────────────────────────────────────────────────────────────────

UNITS = r'(?:Hz|kHz|g|m/s²|°C|°F|Pa|kPa|μg/m³|ppb|ACH|m³/m³|%|ms|s|steps/min|bpm|rpm|mm|cm|m)'
PHYSICS_PARAM = re.compile(
    rf'(\d+\.?\d*|\.\d+)\s*{UNITS}|'           # value + unit
    rf'(?:threshold|cutoff|primitive|traces to)[^\n]{{0,80}}'  # explicit citation
    , re.IGNORECASE
)

AGENT_NAMES = {
    'attorney-A', 'attorney-B', 'judicial-clerk', 'police',
    'simulator-operator', 'uart-reader', 'plotter', 'regression-runner',
    'sw-advisor', 'hw-advisor', 'bill-drafter',
    'api-reviewer', 'code-reviewer', 'doc-reviewer', 'constitution-auditor',
    'package-manager', 'stage-compactor', 'agent-updater',
}


def _find_sessions(project: Optional[str]) -> list[Path]:
    base = Path.home() / '.claude' / 'projects'
    if project:
        matches = [d for d in base.iterdir() if project in d.name]
        if not matches:
            sys.exit(f'No project matching "{project}" in {base}')
        base = matches[0]
    return sorted(
        (p for p in base.rglob('*.jsonl') if 'subagents' not in str(p)),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )


def _subagent_dir(session_path: Path) -> Optional[Path]:
    sid = session_path.stem
    candidate = session_path.parent / sid / 'subagents'
    return candidate if candidate.exists() else None


def _read_subagent_output(subagent_dir: Path, agent_id: str) -> str:
    """Extract the final text output from a subagent JSONL."""
    path = subagent_dir / f'{agent_id}.jsonl'
    if not path.exists():
        return ''
    lines = []
    for line in path.read_text().splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if obj.get('type') == 'assistant':
            for block in obj.get('message', {}).get('content', []):
                if block.get('type') == 'text':
                    lines.append(block['text'].strip())
    return '\n\n'.join(lines[-3:]) if lines else ''  # last 3 assistant turns


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get('type') == 'text':
                    parts.append(block['text'].strip())
        return '\n'.join(parts)
    return ''


def _extract_tool_uses(content) -> list[dict]:
    if not isinstance(content, list):
        return []
    return [b for b in content if isinstance(b, dict) and b.get('type') == 'tool_use']


def _physics_params(text: str) -> list[str]:
    return list(dict.fromkeys(
        m.strip() for m in PHYSICS_PARAM.findall(text) if m.strip()
    ))


# ── Parser ────────────────────────────────────────────────────────────────────

def parse_session(path: Path) -> dict:
    turns = []
    physics_found: list[str] = []
    session_meta = {'timestamp': None, 'branch': None, 'cwd': None, 'slug': None}

    subagent_dir = _subagent_dir(path)

    for line in path.read_text().splitlines():
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        kind = obj.get('type')

        # Extract session metadata from first user message
        if kind == 'user' and not obj.get('toolUseResult') and not session_meta['timestamp']:
            session_meta['timestamp'] = obj.get('timestamp')
            session_meta['branch']    = obj.get('gitBranch')
            session_meta['cwd']       = obj.get('cwd')
            session_meta['slug']      = obj.get('slug')

        # Human input turn
        if kind == 'user' and not obj.get('toolUseResult'):
            text = _extract_text(obj.get('message', {}).get('content', ''))
            if text and not text.startswith('/exit'):
                turns.append({'role': 'human', 'text': text})
                physics_found += _physics_params(text)

        # Assistant turn
        elif kind == 'assistant':
            msg = obj.get('message', {})
            content = msg.get('content', [])
            text = _extract_text(content)
            tool_uses = _extract_tool_uses(content)

            agent_calls = []
            other_tools = []
            for tool in tool_uses:
                name = tool.get('name', '')
                inp  = tool.get('input', {})
                if name == 'Agent':
                    subtype = inp.get('subagent_type', 'general-purpose')
                    desc    = inp.get('description', '')
                    agent_id = tool.get('id', '')
                    output = ''
                    if subagent_dir and agent_id:
                        output = _read_subagent_output(subagent_dir, agent_id)
                    agent_calls.append({
                        'subtype': subtype,
                        'description': desc,
                        'prompt_excerpt': inp.get('prompt', '')[:200],
                        'output_excerpt': output[:400] if output else '',
                    })
                elif name not in ('ScheduleWakeup',):
                    other_tools.append(name)

            if text or agent_calls:
                turns.append({
                    'role': 'assistant',
                    'text': text,
                    'agents': agent_calls,
                    'tools': other_tools,
                })
                physics_found += _physics_params(text)

    return {
        'meta': session_meta,
        'turns': turns,
        'physics': list(dict.fromkeys(physics_found)),
    }


# ── Renderer ──────────────────────────────────────────────────────────────────

def render_markdown(data: dict, session_path: Path) -> str:
    meta   = data['meta']
    turns  = data['turns']
    params = data['physics']

    ts = meta['timestamp'] or ''
    try:
        dt = datetime.fromisoformat(ts.replace('Z', '+00:00'))
        date_str = dt.strftime('%Y-%m-%d %H:%M UTC')
    except Exception:
        date_str = ts

    lines = [
        f'# Crucible Session Transcript',
        f'',
        f'| Field | Value |',
        f'|---|---|',
        f'| Date | {date_str} |',
        f'| Branch | `{meta["branch"] or "—"}` |',
        f'| Working directory | `{meta["cwd"] or "—"}` |',
        f'| Session file | `{session_path.name}` |',
        f'',
        f'---',
        f'',
    ]

    for turn in turns:
        if turn['role'] == 'human':
            lines += [f'## You', f'', turn['text'], f'']

        elif turn['role'] == 'assistant':
            if turn['text']:
                lines += [f'## Claude', f'', turn['text'], f'']

            for agent in turn.get('agents', []):
                subtype = agent['subtype']
                desc    = agent['description']
                lines += [
                    f'### → Agent invoked: `{subtype}`',
                    f'',
                    f'**Task:** {desc}',
                    f'',
                ]
                if agent['prompt_excerpt']:
                    lines += [
                        f'<details><summary>Prompt (excerpt)</summary>',
                        f'',
                        f'```',
                        agent['prompt_excerpt'] + ('…' if len(agent['prompt_excerpt']) == 200 else ''),
                        f'```',
                        f'</details>',
                        f'',
                    ]
                if agent['output_excerpt']:
                    lines += [
                        f'<details><summary>Agent output (excerpt)</summary>',
                        f'',
                        agent['output_excerpt'] + ('…' if len(agent['output_excerpt']) == 400 else ''),
                        f'</details>',
                        f'',
                    ]

            other = turn.get('tools', [])
            if other:
                tool_list = ', '.join(f'`{t}`' for t in other)
                lines += [f'*Tools used: {tool_list}*', f'']

    # Physics parameters summary
    if params:
        lines += [
            f'---',
            f'',
            f'## Physics Parameters Established',
            f'',
            f'Parameters and thresholds identified during this session '
            f'(traces to domain primitives):',
            f'',
        ]
        for p in params:
            lines.append(f'- {p}')
        lines.append('')

    lines += [
        f'---',
        f'',
        f'*Exported by `scripts/export-session.py` from Crucible session `{session_path.stem}`*',
    ]

    return '\n'.join(lines)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]
    project = None
    session_path = None

    i = 0
    while i < len(args):
        if args[i] == '--project' and i + 1 < len(args):
            project = args[i + 1]
            i += 2
        elif not args[i].startswith('--'):
            session_path = Path(args[i])
            i += 1
        else:
            i += 1

    if session_path is None:
        sessions = _find_sessions(project)
        if not sessions:
            sys.exit('No session files found.')
        session_path = sessions[0]
        print(f'Using most recent session: {session_path}')

    print(f'Parsing {session_path.name}…')
    data = parse_session(session_path)

    # Output path
    repo_root = Path(__file__).resolve().parent.parent
    out_dir = repo_root / 'docs' / 'governance' / 'session-transcripts'
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = data['meta']['timestamp'] or ''
    try:
        date_prefix = datetime.fromisoformat(ts.replace('Z', '+00:00')).strftime('%Y-%m-%d')
    except Exception:
        date_prefix = datetime.now().strftime('%Y-%m-%d')

    slug = data['meta']['slug'] or session_path.stem[:8]
    out_path = out_dir / f'{date_prefix}-{slug}.md'

    md = render_markdown(data, session_path)
    out_path.write_text(md)

    print(f'Transcript written to: {out_path}')
    print(f'Turns: {len(data["turns"])}  |  Physics params found: {len(data["physics"])}')


if __name__ == '__main__':
    main()
