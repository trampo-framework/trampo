#!/usr/bin/env python3
"""Script support for the first load and for replay.

  runbooks.py pin SOURCE [SOURCE...]         name each code repository at its commit, each document folder at today
  runbooks.py inventory-check FILE           every feature row cites file and line, or says it was inferred
  runbooks.py flows WORKSPACE [--reset]      each flow with its status; --reset returns a flow edited after its replay
  runbooks.py verify WORKSPACE FLOW RECORD   set a flow to verified from the record of a passing replay

Nothing here runs a system, fetches, checks out or writes outside the workspace. Standard library only.
"""
import os
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import health  # noqa: E402

CITE = re.compile(r'[\w./-]+:\d+')
TOP_SHOWN = 12


def git(repo, *args):
    # git status refreshes the index unless told not to, and a first load never writes to what it reads
    r = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True, env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'})
    return r.stdout.strip() if r.returncode == 0 else None


def pin(source, today=None):
    """What a stamp cites for one source: its folder name and its commit, never where it sits on this machine."""
    source = Path(source).resolve()
    ref = git(source, 'rev-parse', '--short=12', 'HEAD') if (source / '.git').exists() else None
    if ref:
        names = (git(source, 'ls-tree', '-r', '--name-only', ref) or '').splitlines()
        dirty = len((git(source, 'status', '--porcelain') or '').splitlines())
        kind = 'code'
    else:
        names = sorted(f.relative_to(source).as_posix() for f in source.rglob('*') if f.is_file() and not f.is_symlink())
        ref, dirty, kind = today or time.strftime('%Y-%m-%d'), 0, 'documents'
    top = Counter(n.split('/', 1)[0] + '/' if '/' in n else '(top level)' for n in names)
    return {'name': source.name, 'kind': kind, 'ref': ref, 'files': len(names), 'dirty': dirty, 'top': top.most_common(TOP_SHOWN)}


def render_pins(pins):
    out = []
    for p in pins:
        out.append(f'{p["name"]}@{p["ref"]}  {p["kind"]}, {p["files"]} files: ' + ', '.join(f'{n} {c}' for n, c in p['top']))
        if p['kind'] == 'code':
            out.append(f'  read every file as `git show {p["ref"]}:<path>` in your copy of {p["name"]}, never from the working folder'
                       + (f'; {p["dirty"]} uncommitted changes there are not part of this commit' if p['dirty'] else ''))
        out.append(f'  stamp: _Written <date> from {p["kind"]} at {p["name"]}@{p["ref"]}; not yet replayed._')
    return '\n'.join(out)


def inventory_problems(text):
    out = []
    if not re.search(r'(?m)^Read at: *[\w.-]+@\S+', text):
        out.append('no "Read at: <source>@<commit>" line: an inventory says which commit of each source it was read from')
    out += [f'line {n} names a machine-local path: name a source by its folder name and commit'
            for n, line in enumerate(text.splitlines(), 1) if health.LOCAL_PATH.search(line)]
    for line in text.splitlines():
        cells = [c.strip() for c in line.strip().strip('|').split('|')]
        if not line.lstrip().startswith('|') or len(cells) < 2 or cells[0] in ('Feature', '') or set(cells[0]) <= set('-: '):
            continue
        if not CITE.search(cells[1]) and '(inferred)' not in cells[1]:
            out.append(f'"{cells[0]}" has no entry point with a file and a line: cite <source>:<path>:<line>, or mark it (inferred)')
    return out


def replay_setting(ws):
    """(on or off, the test environment's name), from `runbooks:` in workspace.yaml. Absent is off."""
    f = Path(ws) / 'workspace.yaml'
    block = re.search(r'(?m)^runbooks:[^\n]*\n((?:[ \t]+[^\n]*\n?|\n)*)', f.read_text(encoding='utf-8') if f.is_file() else '')
    keys = dict(re.findall(r'(?m)^[ \t]+(\w+):[ \t]*([^#\n]*)', block.group(1))) if block else {}
    env = keys.get('test_environment', '').strip().strip('"\'')
    return ('on' if keys.get('replay', '').strip() == 'on' else 'off'), ('' if env in ('none', '[]') else env)


def set_front(text, **values):
    for key, value in values.items():
        line = f'{key.replace("_", "-")}: {value}'
        head, sep, rest = text.partition('\n---\n')
        pattern = rf'(?m)^{re.escape(key.replace("_", "-"))}:.*$'
        head = re.sub(pattern, lambda _: line, head) if re.search(pattern, head) else head + '\n' + line
        text = head + sep + rest
    return text


def inside(ws, rel):
    path = (Path(ws) / rel).resolve()
    return path if Path(ws).resolve() in path.parents else None


def verify(ws, flow_rel, record_rel, today=None):
    """Why the flow was not set to verified, or None once it was."""
    on, env = replay_setting(ws)
    if on != 'on':
        return ('replay is off in this workspace, so no flow becomes verified here. A person turns it on under runbooks: in '
                'workspace.yaml once the team has a test environment to run against')
    if not env:
        return 'replay is on and workspace.yaml names no test environment under runbooks: a person names the one replays may use'
    flow, record = inside(ws, flow_rel), inside(ws, record_rel)
    if not flow or not record:
        return 'the flow and its replay record are named by their paths inside the workspace'
    if not flow.is_file():
        return f'no flow at {flow_rel}'
    if not record.is_file():
        return f'no replay record at {record_rel}: only the record of a replay by a second agent sets a flow to verified'
    said = record.read_text(encoding='utf-8', errors='ignore')
    if Path(flow_rel).name not in said:
        return f'{record_rel} does not name {Path(flow_rel).name}: it is the record of another flow'
    verdict = re.search(r'(?m)^Verdict: *(.+)$', said)
    if not verdict or not re.match(r'PASS as written\b', verdict.group(1)):
        return (f'{record_rel} says the flow did not pass as written ({verdict.group(1).strip() if verdict else "no Verdict line"}). '
                'Apply the edits the record supports, keep not-yet-replayed, and replay again')
    text = flow.read_text(encoding='utf-8')
    flow.write_text(set_front(text, status='verified', last_replay=f'{today or time.strftime("%Y-%m-%d")} {record_rel}',
                              steps_hash=health.steps_hash(text)), encoding='utf-8')
    return None


def flow_rows(ws):
    rows = []
    for f in health.runbook_files(ws):
        if f.parent.name != 'flows':
            continue
        meta = health.front(f.read_text(encoding='utf-8', errors='ignore'))[0]
        status, problem = health.flow_state(ws, f)
        rows.append({'flow': f'runbooks/flows/{f.name}', 'status': status, 'waits': meta.get('waits', ''),
                     'last': meta.get('last-replay', ''), 'stale': bool(problem), 'path': f})
    return rows


def main(argv):
    if len(argv) >= 2 and argv[0] == 'pin':
        print(render_pins([pin(s) for s in argv[1:]]))
        return 0
    if len(argv) == 2 and argv[0] == 'inventory-check':
        problems = inventory_problems(Path(argv[1]).read_text(encoding='utf-8'))
        print('\n'.join(problems) or 'every row cites its entry point')
        return 1 if problems else 0
    if len(argv) >= 2 and argv[0] == 'flows':
        on, env = replay_setting(argv[1])
        print(f'replay: {on}' + (f', on {env}' if on == 'on' and env else ''))
        for r in flow_rows(argv[1]):
            if r['stale'] and '--reset' in argv[2:]:
                r['path'].write_text(set_front(r['path'].read_text(encoding='utf-8'), status=health.STATUSES[0]), encoding='utf-8')
                r['status'], r['stale'] = health.STATUSES[0] + ' (reset: edited after its replay, or no record)', False
            print(f'{r["flow"]}  {r["status"]}{"  STALE" if r["stale"] else ""}  waits: {r["waits"] or "none"}  last replay: {r["last"] or "none"}')
        return 0
    if len(argv) == 4 and argv[0] == 'verify':
        why = verify(*argv[1:])
        print(why or f'{argv[2]} is verified')
        return 1 if why else 0
    print(__doc__)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
