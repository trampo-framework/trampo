#!/usr/bin/env python3
"""What the health check reports about a workspace's runbooks.

  health.py WORKSPACE

The core's doctor loads this file when the part is installed beside it; run alone it prints the same lines. Standard
library only: it must load on a machine that has this part and nothing else.
"""
import hashlib
import re
import sys
from pathlib import Path

STATUSES = ('not-yet-replayed', 'verified')
LABELS = ('(observed)', '(traced from code)')
STAMP = re.compile(r'_Written \d{4}-\d{2}-\d{2} from (?:code|documents) at [\w.-]+@(?:[0-9a-f]{7,40}|\d{4}-\d{2}-\d{2}); '
                   r'not yet replayed\._')
# ponytail: a guess from the shape of a home or temp folder. A path on a remote host that looks like one is caught
# too, and `~/` is not. Upgrade path: a per-team allow list in the index file.
LOCAL_PATH = re.compile(r'(?:/Users/|/home/|[A-Za-z]:\\Users\\|/private/tmp/|/var/folders/)[\w.-]+')
WORKSPACE_PATHS = re.compile(r'workspace\.yaml|slot\.py|\b(?:memory|sessions|runbooks|modes|incidents|slots|telemetry|people|proposals)/[\w<]')


def front(text):
    """(front matter as a dict, the rest). No front matter gives an empty dict."""
    m = re.match(r'---\n(.*?)\n---\n', text, re.S)
    if not m:
        return {}, text
    pairs = (line.partition(':') for line in m.group(1).splitlines() if ':' in line)
    return {k.strip(): v.split(' #', 1)[0].strip() for k, _, v in pairs}, text[m.end():]


def section(text, name):
    m = re.search(rf'(?ms)^## +{re.escape(name)}[^\n]*\n(.*?)(?=^## |\Z)', text)
    return m.group(1) if m else ''


def steps(text):
    """(heading, body) of each `### ` step under `## Steps`."""
    parts = re.split(r'(?m)^### +(.+)$', section(text, 'Steps'))
    return list(zip(parts[1::2], parts[2::2]))


def steps_hash(text):
    """What a passing replay ran. Prose outside `## Steps` is not in it, so correcting a note keeps the flow verified."""
    plain = '\n'.join(line.rstrip() for line in section(text, 'Steps').strip().splitlines())
    return hashlib.sha256(plain.encode()).hexdigest()[:16]


def file_problems(rel, text):
    """[(level, message)] for one runbook, from its text alone."""
    out = [('FAIL', f'{rel}:{n} names a machine-local path ({m.group(0)}...). A runbook is read on every machine: cite code as '
                    '<source>@<commit>:<path>:<line> and a workspace file by its path from the workspace root')
           for n, line in enumerate(text.splitlines(), 1) for m in [LOCAL_PATH.search(line)] if m]
    meta, body = front(text)
    if rel.startswith('flows/'):
        if meta.get('status') not in STATUSES:
            out.append(('FAIL', f'{rel}: status must be one of {", ".join(STATUSES)}, got {meta.get("status")!r}'))
        found = steps(text)
        if not found:
            out.append(('FAIL', f'{rel} has no numbered steps under "## Steps": a flow is steps an agent can follow literally'))
        for head, step in found:
            if not head.rstrip().endswith(LABELS):
                out.append(('FAIL', f'{rel}: step "{head.strip()}" is not labelled. End its heading with (observed), seen on the test '
                                    'environment, or (traced from code), read from source and not driven'))
            elif head.rstrip().endswith(LABELS[1]) and not STAMP.search(step):
                out.append(('FAIL', f'{rel}: step "{head.strip()}" is traced from code and carries no stamp. End it with '
                                    '_Written <date> from code at <source>@<commit>; not yet replayed._ so nobody reads it as fact'))
    else:
        if meta.get('basis') not in ('code', 'documents', 'observed'):
            out.append(('FAIL', f'{rel} does not say whether it was observed or written from code: set basis: in its front matter '
                                'to observed, code or documents'))
        elif meta['basis'] != 'observed' and not STAMP.search(body):
            out.append(('FAIL', f'{rel} is written from {meta["basis"]} and carries no stamp. Put _Written <date> from '
                                f'{meta["basis"]} at <source>@<commit>; not yet replayed._ under its title'))
        if not re.search(r'(?m)^## +Local\b', body):
            out.append(('WARN', f'{rel} has no "## Local" section: say whether the system runs locally, how, and which flows can '
                                'run against the local copy'))
    return out


def proposal_problems(text):
    """A drafted skill loads on machines with no copy of the workspace, and is added only on a person's approval."""
    meta, body = front(text)
    out = []
    draft = section(body, 'Draft')
    named = sorted({m.group(0) for m in WORKSPACE_PATHS.finditer(draft)} | {m.group(0) for m in LOCAL_PATH.finditer(draft)})
    if named:
        out.append(f'the drafted skill depends on the workspace or on one machine ({", ".join(named)}): it must load where there is '
                   'no copy of either. Put what it needs in the skill itself')
    if meta.get('status') == 'added' and not meta.get('approved-by'):
        out.append('marked added with no approver: a person approves each drafted skill by name before it is added, and '
                   'approved-by: carries their name')
    return out


def runbook_files(ws):
    top = Path(ws) / 'runbooks'
    return [f for kind in ('systems', 'flows') for f in sorted((top / kind).glob('*.md'))
            if not f.is_symlink() and f.name != 'README.md']


def flow_state(ws, f):
    """(status, problem or '') of one flow against its replay record."""
    text = f.read_text(encoding='utf-8', errors='ignore')
    meta = front(text)[0]
    if meta.get('status') != 'verified':
        return meta.get('status', ''), ''
    record = (meta.get('last-replay') or 'none').split()[-1]
    path = (Path(ws) / record).resolve()
    if record == 'none' or Path(ws).resolve() not in path.parents or not path.is_file():
        return 'verified', ('is marked verified with no replay record: last-replay: must name the record of a passing replay, by '
                            'its path from the workspace root. Only a replay by a second agent sets verified; set it back to '
                            'not-yet-replayed')
    if meta.get('steps-hash') != steps_hash(text):
        return 'verified', ('is marked verified and a step was edited after its replay: the replay did not run that text. Set it '
                            'back with runbooks.py flows <workspace> --reset, then replay it')
    return 'verified', ''


def check(ws):
    """(fails, warns)."""
    ws = Path(ws)
    fails, warns = [], []
    index = ws / 'runbooks' / 'README.md'
    listed = index.read_text(encoding='utf-8', errors='ignore') if index.is_file() else ''
    for f in runbook_files(ws):
        rel = f.relative_to(ws / 'runbooks').as_posix()
        if rel not in listed:
            warns.append(f'runbooks/{rel} is not in the index: add its line to runbooks/README.md, or nobody finds it')
        for level, said in file_problems(rel, f.read_text(encoding='utf-8', errors='ignore')):
            (fails if level == 'FAIL' else warns).append(f'runbooks/{said}')
        if rel.startswith('flows/'):
            problem = flow_state(ws, f)[1]
            if problem:
                fails.append(f'runbooks/{rel} {problem}')
    for f in sorted((ws / 'proposals').glob('skill-*.md')):
        if not f.is_symlink():
            fails += [f'proposals/{f.name}: {p}' for p in proposal_problems(f.read_text(encoding='utf-8', errors='ignore'))]
    return fails, warns


def main(argv):
    if len(argv) != 1 or argv[0].startswith('-'):
        print(__doc__)
        return 2
    fails, warns = check(argv[0])
    for w in warns:
        print(f'WARN  {w}')
    for f in fails:
        print(f'FAIL  {f}')
    print(f'{len(fails)} failures, {len(warns)} warnings')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
