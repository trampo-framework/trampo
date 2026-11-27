#!/usr/bin/env python3
"""What every Trampo script shares: where the workspace is, what it is set up to do, who is at the keyboard,
and the ledger in <ws>/telemetry/events/<sid>.jsonl (one file per session, appended, never rewritten)."""
import json
import os
import re
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from untrusted import SID_RE, clean

HERE = Path(__file__).resolve().parent
TS = '%Y-%m-%dT%H:%M:%SZ'
IDENTITY_HINT = ('nobody is declared on this machine: on storage: git a person sets `git config user.name`; on storage: '
                 'files a person puts their name on the first line of ~/.config/trampo/user. Never the assistant')


def core_version():
    return json.loads((HERE.parent / '.claude-plugin' / 'plugin.json').read_text())['version']


def parse_yaml(text):
    """The subset workspace.yaml uses: scalars, one level of nested maps, and lists of scalars."""
    out, key = {}, None
    for raw in text.splitlines():
        line = raw.split(' #', 1)[0].rstrip()
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if not line.startswith(' '):
            k, _, v = line.partition(':')
            key, v = k.strip(), v.strip()
            out[key] = scalar(v) if v else None
        elif line.strip().startswith('- '):
            if not isinstance(out.get(key), list):
                out[key] = []
            out[key].append(scalar(line.strip()[2:].strip()))
        else:
            if not isinstance(out.get(key), dict):
                out[key] = {}
            k, _, v = line.strip().partition(':')
            out[key][k.strip()] = scalar(v.strip())
    return out


def scalar(v):
    v = v.strip('"\'')
    if v == '[]':
        return []
    return int(v) if re.fullmatch(r'-?\d+', v) else v


def find_workspace(start):
    for d in [Path(start), *Path(start).parents]:
        if (d / 'workspace.yaml').exists():
            return d
    return None


def bindings():
    """What `run.py dispatch` tied to a workspace on this machine: [{worktree, workspace, run, item}]."""
    out = []
    for f in sorted((config_dir() / 'bound').glob('*')):
        try:
            b = json.loads(f.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if isinstance(b, dict) and (Path(str(b.get('workspace'))) / 'workspace.yaml').exists():
            out.append(b)
    return out


def bound_workspace(start):
    """The workspace a dispatched worker's folder was tied to, or None: a worker in a code worktree is still the
    workspace's, and without this its hooks would find no workspace and check nothing."""
    here = Path(os.path.realpath(start))
    for b in bindings():
        tree = Path(str(b.get('worktree')))
        if here == tree or tree in here.parents:
            return Path(b['workspace'])
    return None


def sitting_workspace(session, ws=None):
    """Remember, or with no ws say, the workspace a sitting was last seen in. A shell that moves to another folder is
    still that sitting's, and without this its hooks would find no workspace there and check nothing."""
    name = re.sub(r'[^\w-]', '', str(session or ''))
    if not name:
        return None
    store = config_dir() / 'sittings' / name
    try:
        known = store.read_text(encoding='utf-8').strip()
    except OSError:
        known = ''
    if ws is None:
        return Path(known) if known and (Path(known) / 'workspace.yaml').exists() else None
    if known != str(ws):
        store.parent.mkdir(parents=True, exist_ok=True)
        store.write_text(str(ws), encoding='utf-8')
    return Path(ws)


def config(ws, text=None):
    f = Path(ws) / 'workspace.yaml'
    if text is None:
        text = f.read_text(encoding='utf-8') if f.exists() else ''
    return parse_yaml(text)


def storage_of(ws):
    return config(ws).get('storage')


def branch_of(ws):
    return str(config(ws).get('branch') or 'main')


def listed(cfg, key):
    value = cfg.get(key)
    return [str(v) for v in value] if isinstance(value, list) else []


def same(a, b):
    return str(a).strip().casefold() == str(b).strip().casefold()


def git(ws, *args, timeout=8):
    """(ok, stdout) of one git call in the workspace. fsmonitor is off: a hook must never start a daemon."""
    try:
        r = subprocess.run(['git', '-c', 'core.fsmonitor=false', '-C', str(ws), *args], capture_output=True, text=True,
                           timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return False, ''
    return r.returncode == 0, r.stdout.strip()


def config_dir():
    base = os.environ.get('XDG_CONFIG_HOME', '')
    return (Path(base) if os.path.isabs(base) else Path.home() / '.config') / 'trampo'


def areas():
    """The folders a person declared, by hand, as where they work on this machine: one full path per line."""
    try:
        lines = (config_dir() / 'areas').read_text(encoding='utf-8').splitlines()
    except OSError:
        return []
    return [l.strip() for l in lines if os.path.isabs(l.strip())]


def identity(ws):
    """Who is at the keyboard, as this machine says: the git user name on storage: git, and a name a person
    declared by hand where there is no git. Declared, never proven."""
    if storage_of(ws) != 'files':
        return git(ws, 'config', 'user.name')[1]
    name = os.environ.get('TRAMPO_USER', '').strip()
    if name:
        return name
    try:
        lines = (config_dir() / 'user').read_text(encoding='utf-8').splitlines()
    except OSError:
        return ''
    return next((l.strip() for l in lines if l.strip()), '')


def is_approver(ws, name, cfg=None):
    return bool(name) and any(same(name, a) for a in listed(cfg if cfg is not None else config(ws), 'approvers'))


def path_problem(ws, rel):
    """Why a workspace-relative path must not be read, written or removed, or None when it is safe."""
    rel = Path(str(rel)).as_posix()
    if rel.startswith('/') or '..' in Path(rel).parts:
        return f'path must stay inside the workspace: {rel}'
    # A link in a shared folder can point anywhere on the machine that opens it, so no part of the path may be one
    step = Path(ws)
    for part in Path(rel).parts:
        step = step / part
        if step.is_symlink():
            return (f'{rel} is or passes through a symbolic link ({step.relative_to(ws).as_posix()}): refused, nothing was '
                    'read or changed. A person replaces the link with the real file or folder')
    if Path(ws).resolve() not in (Path(ws) / rel).resolve().parents:
        return f'path must stay inside the workspace: {rel}'
    return None


def real(ws, rel):
    f = Path(ws) / str(rel)
    return f if rel and not path_problem(ws, rel) and f.is_file() else None


def state_dir(ws):
    """Per-machine state of one workspace copy: never committed, never synced on purpose."""
    return Path(ws) / '.trampo' / 'state'


def active(ws, session=None):
    """(sid, kind) of the ledger this assistant session files under, or None. One file per assistant session, so
    two sessions in one checkout never file each other's prompts; the shared file is the fallback."""
    if os.environ.get('TRAMPO_SID'):
        return os.environ['TRAMPO_SID'], None
    own = [f'active-sid.{session}'] if session and SID_RE.fullmatch(str(session)) else []
    for name in [*own, 'active-sid']:
        try:
            sid, _, kind = (state_dir(ws) / name).read_text(encoding='utf-8').strip().partition(' ')
        except OSError:
            continue
        if sid:
            return sid, kind.strip() or None
    return None


def ledger_files(ws):
    return [f for f in sorted((Path(ws) / 'telemetry' / 'events').glob('*.jsonl'))
            if not path_problem(ws, f'telemetry/events/{f.name}')]


def load_events(ws):
    """(events in time order, unreadable lines). A line a sync client copied twice counts once, by its event_id."""
    events, bad, seen = [], [], set()
    for f in ledger_files(ws):
        for n, line in enumerate(f.read_bytes().decode('utf-8', 'replace').splitlines(), 1):
            if not line.strip():
                continue
            try:
                e = json.loads(line)
            except ValueError:
                e = None
            if not isinstance(e, dict):
                bad.append(f'{f.name}:{n}')
                continue
            if e.get('event_id') and e['event_id'] in seen:
                continue
            seen.add(e.get('event_id'))
            events.append(clean(e))
    events.sort(key=lambda e: (e.get('ts', ''), e.get('ns', 0)))
    return events, bad


def session_events(ws, sid):
    return [e for e in load_events(ws)[0] if e.get('sid') == sid]


def append(ws, sid, event, ts=None):
    if not SID_RE.fullmatch(str(sid)) or str(sid).startswith('.'):
        raise SystemExit(f'a sid is a file name: letters, digits, _ . - only, got {sid!r}')
    meta = {'ts': ts or datetime.now(timezone.utc).strftime(TS), 'ns': time.time_ns(), 'event_id': uuid.uuid4().hex, 'sid': sid}
    # meta is spread twice: first for key order, last so no caller sets when or which session
    event = {**meta, **{k: v for k, v in event.items() if v is not None}, **meta}
    why = path_problem(ws, f'telemetry/events/{sid}.jsonl')
    if why:
        raise SystemExit(why)
    path = Path(ws) / 'telemetry' / 'events' / f'{sid}.jsonl'
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + '\n')
    return event


def hook_log(ws, row):
    """One line per hook decision, so a check's hit rate can be read before, and after, it is allowed to block."""
    try:
        state_dir(ws).mkdir(parents=True, exist_ok=True)
        with (state_dir(ws) / 'hook-log.jsonl').open('a', encoding='utf-8') as fh:
            fh.write(json.dumps({'ts': datetime.now(timezone.utc).strftime(TS), **row}) + '\n')
    except OSError:
        pass


def hook_mode(ws, name, default='block'):
    """block, log or off for one check, from `hooks:` in workspace.yaml. A new check ships as log."""
    value = (config(ws).get('hooks') or {}).get(name) if isinstance(config(ws).get('hooks'), dict) else None
    return value if value in ('block', 'log', 'off') else default


def stats_lines(events, since='', asof=''):
    """What `event.py stats` prints first: the totals line a review file quotes. Every count is of sessions, never of
    ledger lines: a session that ended twice is one session, under its last end. The line names its own window and
    the moment it was counted, so any copy of the ledger can count it again."""
    asof = asof or (str(events[-1].get('ts', '')) if events else '')
    events = [e for e in events if str(e.get('ts', '')) <= asof and e.get('sid')]
    final, said = {}, lambda c: ', '.join(f'{k} {n}' for k, n in sorted(c.items())) or 'none'
    for e in events:
        if e.get('ev') == 'end' and str(e.get('ts', ''))[:10] >= since:
            final[e['sid']] = e
    started = {e['sid'] for e in events if str(e.get('ts', ''))[:10] >= since}
    stopped = {e['sid'] for e in events if e.get('ev') == 'block'} & set(final)
    outcomes = {}
    for e in final.values():
        outcomes[str(e.get('outcome'))] = outcomes.get(str(e.get('outcome')), 0) + 1
    people = {str(e['who']).casefold() for e in events if e.get('who') and e['sid'] in started}
    n = len(final)
    return [f"stats {'since ' + since if since else 'all dates'}, as of {asof or 'an empty ledger'}: {n} sessions ended "
            f'({said(outcomes)}), {len(stopped)} of {n} stopped at least once, {len(started - set(final))} still open, '
            f'by {len(people)} named people, counted by session']

