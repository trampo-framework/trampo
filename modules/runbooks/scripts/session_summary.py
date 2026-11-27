#!/usr/bin/env python3
"""Summarise a folder of assistant session transcripts as names and counts, and nothing else.

  session_summary.py FOLDER [--min N] [--out FILE]

FOLDER is the one a person names; there is no default, and nothing outside it is read. The summary holds tool,
connector, skill and program names, how often each was used, how often each failed, and a fixed label for why. It
holds no prompt, no reply, no argument, no file path and no result text, so it can be written into a shared workspace.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

# A name is a plain identifier with no run of digits long enough to be a number that identifies something
NAME = re.compile(r'(?!.*\d{6})[A-Za-z][A-Za-z0-9_.:-]{0,59}')
SHELL_TOOLS = ('Bash', 'shell')
LABELS = {
    'not installed': re.compile(r'(?i)command not found|not installed|is not recognized'),
    'not available': re.compile(r'(?i)no such tool|tool not found|unknown tool|not available|not connected|failed to connect'),
    'no access': re.compile(r'(?i)permission denied|unauthori[sz]ed|forbidden|access denied|not authori[sz]ed'),
}
OTHER = 'failed, reason not classified'
FIXED_WORDS = ('Tool', 'Calls', 'Failed', 'Connector', 'Skill', 'Program', 'Runs', 'Tool or program', 'What', 'Count', OTHER)


def blocks(line):
    try:
        content = json.loads(line).get('message', {}).get('content')
    except (ValueError, AttributeError):
        return []
    return [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []


def program(command):
    """The program a shell command starts with, by its bare name. Arguments are never read."""
    # ponytail: first command only, split on spaces. A pipeline's later programs and a quoted path are not counted;
    # a shell parser would count them
    for word in str(command).split():
        if '=' in word or word in ('sudo', 'env', 'time'):
            continue
        name = word.rsplit('/', 1)[-1]
        return name if NAME.fullmatch(name) else None
    return None


def why(block):
    content = block.get('content')
    text = content if isinstance(content, str) else ' '.join(str(c.get('text', '')) for c in content or [] if isinstance(c, dict))
    return next((label for label, pattern in LABELS.items() if pattern.search(text)), OTHER)


def summarise(folder, minimum=3):
    tools, connectors, skills, programs, missing = {}, Counter(), Counter(), Counter(), Counter()
    sessions = unnamed = 0
    for f in sorted(p for p in Path(folder).rglob('*.jsonl') if p.is_file() and not p.is_symlink()
                    and not any(d.is_symlink() for d in p.parents if Path(folder) in d.parents)):
        sessions += 1
        calls = {}
        for line in f.read_text(encoding='utf-8', errors='ignore').splitlines():
            for b in blocks(line):
                if b.get('type') == 'tool_use':
                    name = str(b.get('name', ''))
                    if not NAME.fullmatch(name):
                        unnamed += 1
                        continue
                    given = b.get('input') if isinstance(b.get('input'), dict) else {}
                    tools.setdefault(name, {'calls': 0, 'failed': 0})['calls'] += 1
                    subject = name
                    if name.startswith('mcp__') and name.count('__') >= 2:
                        connectors[name.split('__')[1]] += 1
                    elif name == 'Skill' and NAME.fullmatch(str(given.get('skill', ''))):
                        skills[given['skill']] += 1
                    elif name in SHELL_TOOLS:
                        subject = program(given.get('command', ''))
                        if subject:
                            programs[subject] += 1
                    calls[b.get('id')] = (name, subject)
                elif b.get('type') == 'tool_result' and b.get('is_error') and b.get('tool_use_id') in calls:
                    name, subject = calls[b['tool_use_id']]
                    tools[name]['failed'] += 1
                    if subject:
                        missing[(subject, why(b))] += 1
    named = {p: n for p, n in programs.items() if n >= minimum}
    return {'sessions': sessions, 'tools': tools, 'connectors': dict(connectors), 'skills': dict(skills), 'programs': named,
            'missing': sorted((s, label, n) for (s, label), n in missing.items() if s in named or s in tools),
            'unnamed': unnamed, 'minimum': minimum}


def table(heads, rows):
    return ['| ' + ' | '.join(heads) + ' |', '|' + ' --- |' * len(heads), *('| ' + ' | '.join(map(str, r)) + ' |' for r in rows), '']


def render(s):
    by_count = lambda d: sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))  # noqa: E731
    out = ['# Session summary', '', f'Sessions read: {s["sessions"]}. Tool calls with a name that is not a plain identifier: {s["unnamed"]}.',
           'Only names and counts are kept: no prompt, reply, argument, path or result text.', '', '## Tools', '']
    out += table(('Tool', 'Calls', 'Failed'), sorted(((n, c['calls'], c['failed']) for n, c in s['tools'].items()), key=lambda r: (-r[1], r[0])))
    out += ['## Connectors', ''] + table(('Connector', 'Calls'), by_count(s['connectors']))
    out += ['## Skills', ''] + table(('Skill', 'Calls'), by_count(s['skills']))
    out += [f'## Shell programs run {s["minimum"]} or more times', ''] + table(('Program', 'Runs'), by_count(s['programs']))
    out += ['## What was missing', ''] + table(('Tool or program', 'What', 'Count'), s['missing'])
    return '\n'.join(out)


def main(argv):
    args = [a for n, a in enumerate(argv) if not a.startswith('--') and (n == 0 or argv[n - 1] not in ('--min', '--out'))]
    if len(args) != 1 or not Path(args[0]).is_dir():
        print(__doc__)
        return 2
    minimum = int(argv[argv.index('--min') + 1]) if '--min' in argv else 3
    said = render(summarise(args[0], minimum))
    if '--out' in argv:
        out = Path(argv[argv.index('--out') + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(said, encoding='utf-8')
    else:
        print(said)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
