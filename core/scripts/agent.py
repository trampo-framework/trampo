#!/usr/bin/env python3
"""The timed loop an unattended agent runs: one tick, deterministic, with the decisions in code and the thinking in a launched worker.

  agent.py --ws W tick NAME       one tick of the card agent NAME, defined in agents/NAME.yaml
  agent.py --ws W monitor NAME    one tick of the agents monitor NAME: checks what the agents it watches should be doing
  agent.py --ws W release NAME    one tick of the release monitor NAME: checks each recently finished item's systems
  agent.py --ws W monitor|release NAME --dry-run
                                  a trial tick: prints what it would tell; posts, shares and remembers nothing
  agent.py --ws W wait NAME ITEM KEY   a worker's own word that ITEM waits on the answer to the question it asked as KEY
  agent.py --ws W pause NAME      stop NAME's ticks until `resume`; a person's switch
  agent.py --ws W resume NAME
  agent.py --ws W last NAME       the one word the last tick left

agents/NAME.yaml:
  kind: card | monitor
  assignee: the tracker name the agent's items are assigned to (default NAME)
  cap: most items worked at once (default 1)
  interval: minutes between ticks (default 15)
  launch: a program in the workspace that starts one worker for an item (args: ITEM), run by the tick
  watches: (monitor) one agent name per line
  stuck_hours / dirty_hours: (monitor) limits, default 8 and 1
  systems / window_hours: (release) the systems whose checks are read, and how long an item is watched after it is done (default 24)

The card agent picks up items assigned to it, claims an open one, starts a worker through `launch` while under the cap, and
records its tick. It never merges, approves, moves an item to done, reads production or creates an item: this script has no code path
that does, and the slots' own rules refuse the rest. A tick with nothing to do writes one word to
.trampo/state/agent-NAME.last and prints nothing else.
"""
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import approval
import common
from run import slot_rows
from untrusted import shown

WORDS = ('idle', 'paused', 'launched', 'waiting', 'capped', 'ready-for-release', 'no-tracker')
OUR_LIMIT_STATES = ('open', 'in progress')
DAY = 24 * 3600
# an idle agent shares its beat this often: each share is a commit, and a tick comes every few minutes
BEAT_SHARED = 3600
SYNC = Path(__file__).resolve().parent / 'sync.py'


def spec(ws, name):
    f = Path(ws) / 'agents' / f'{name}.yaml'
    if not f.is_file():
        raise SystemExit(f'agent.py: agents/{name}.yaml does not exist')
    cfg = common.parse_yaml(f.read_text(encoding='utf-8'))
    cfg.setdefault('assignee', name)
    cfg.setdefault('cap', 1)
    cfg.setdefault('interval', 15)
    return cfg


def mark(ws, name, suffix, text=None):
    f = common.state_dir(ws) / f'agent-{name}.{suffix}'
    if text is not None:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text, encoding='utf-8')
    return f


def load(ws, name, suffix):
    f = mark(ws, name, suffix)
    try:
        return json.loads(f.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}


def when(text):
    try:
        return datetime.strptime(str(text), '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return 0


def shared(ws, name):
    """The agent's state as the team's repository carries it, for a monitor that runs in another clone."""
    f = Path(ws) / 'sessions' / 'agents' / f'{name}.json'
    try:
        state = json.loads(f.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        state = {}
    return f, state if isinstance(state, dict) else {}


def level(ws):
    """Bring this clone level with the team's copy, when it has one. A failure is the caller's to mention, never to stop on."""
    if common.storage_of(ws) != 'git' or not common.git(ws, 'remote', 'get-url', 'origin')[0]:
        return True
    try:
        return subprocess.run([sys.executable, '-B', str(SYNC), str(ws)], capture_output=True, text=True, timeout=300).returncode == 0
    except subprocess.TimeoutExpired:
        return False


def share(ws, name, now, also=()):
    """Write the agent's state into the tracked file and send it: one commit for a tick that changed something, none
    for one that did not. The beat alone is shared once an hour."""
    f, old = shared(ws, name)
    state = {'pool': load(ws, name, 'pool'), 'waits': load(ws, name, 'waits'), 'paused': mark(ws, name, 'pause').exists()}
    if {k: old.get(k) for k in state} != state or now - when(old.get('beat')) >= BEAT_SHARED:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps({**state, 'beat': stamp(now)}, indent=1, sort_keys=True) + '\n', encoding='utf-8')
    if common.storage_of(ws) != 'git':
        return []
    paths = [str(p) for p in (f, *also) if Path(p).exists()]
    common.git(ws, 'add', '--', *paths)
    if common.git(ws, 'diff', '--cached', '--quiet', '--', *paths)[0]:
        return []
    if not common.git(ws, 'commit', '-q', '-m', f'agent {name}: state', '--', *paths)[0]:
        return [f'{name}: its state could not be committed']
    return [] if level(ws) else [f'{name}: its state is committed and was not shared this tick']


def stamp(now):
    return datetime.fromtimestamp(now, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def launch(ws, cfg, item):
    prog = Path(ws) / str(cfg.get('launch') or '')
    if not prog.is_file():
        return False, 'the agent definition names no launch program in the workspace'
    r = subprocess.run([str(prog), item], cwd=ws, capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
    return r.returncode == 0, (r.stderr or r.stdout).strip()[:200]


def tick(ws, name, now=None):
    now = now or time.time()
    cfg = spec(ws, name)
    mark(ws, name, 'beat', stamp(now))
    if mark(ws, name, 'pause').exists():
        return finish(ws, name, 'paused', share(ws, name, now))
    mine = slot_rows(ws, 'tracker', 'list', '--assignee', str(cfg['assignee']))
    if mine is None:
        return finish(ws, name, 'no-tracker', ['the tracker slot gave no answer: nothing is picked up this tick'])
    pool, waits, notes = load(ws, name, 'pool'), load(ws, name, 'waits'), []
    approvers = common.listed(approval.approved_config(ws), 'approvers')
    for row in slot_rows(ws, 'ask', 'poll') or []:
        if any(common.same(str(row.get('by') or ''), a) for a in approvers):
            waits = {i: k for i, k in waits.items() if k != row.get('key')}
        else:
            notes += [f"{i}: {shown(row.get('by'), 60)} replied to {k} and is not an approver, so the wait stays"
                      for i, k in waits.items() if k == row.get('key')]
    by_id = {r['id']: r for r in mine}
    pool = {i: at for i, at in pool.items() if by_id.get(i, {}).get('state') == 'in progress'}
    word = 'idle'
    for row in mine:
        item, state = row['id'], row['state']
        if state == 'ready for release':
            word = 'ready-for-release' if word == 'idle' else word
            continue
        if state not in OUR_LIMIT_STATES or item in pool:
            continue
        if item in waits:
            word = 'waiting' if word in ('idle', 'capped') else word
            continue
        if len(pool) + len(waits) >= int(cfg['cap']):
            word = 'capped' if word == 'idle' else word
            continue
        if state == 'open' and slot_rows(ws, 'tracker', 'claim', item) is None:
            notes.append(f'{item}: the claim was refused, so it is left alone')
            continue
        ok, said = launch(ws, cfg, item)
        if ok:
            pool[item] = stamp(now)
            word = 'launched'
            notes.append(f'{item}: worker started')
        else:
            notes.append(f'{item}: the worker did not start ({said})')
    mark(ws, name, 'pool', json.dumps(pool))
    mark(ws, name, 'waits', json.dumps(waits))
    return finish(ws, name, word, notes + share(ws, name, now))


def wait(ws, name, item, key):
    """A worker's word that its item waits on a person. The item leaves the pool, so the answer starts a worker for it
    again, and keeps its place under the cap until then."""
    spec(ws, name)
    pool, waits = load(ws, name, 'pool'), load(ws, name, 'waits')
    if item not in pool:
        raise SystemExit(f'agent.py: {name} has no worker on {item}, so there is nothing to hold')
    try:
        asked = {e.get('key') for es in approval.bridge_events(ws) for e in es if e.get('ev') == 'ask'}
    except (OSError, ValueError):
        asked = set()
    if key not in asked:
        raise SystemExit(f'agent.py: no question was asked from here as {key}: ask it through the ask-a-person slot first')
    waits[item] = key
    del pool[item]
    mark(ws, name, 'pool', json.dumps(pool))
    mark(ws, name, 'waits', json.dumps(waits))
    return 'waiting', [f'{item}: waits on the answer to {key}']


def finish(ws, name, word, notes):
    mark(ws, name, 'last', word)
    return word, notes


def age_hours(ws, rel, now):
    try:
        return (now - (Path(ws) / rel).stat().st_mtime) / 3600
    except OSError:
        return 0


def findings(ws, name, now, fetch=True):
    cfg = spec(ws, name)
    found = []
    if fetch:
        level(ws)
    stuck, dirty = float(cfg.get('stuck_hours', 8)), float(cfg.get('dirty_hours', 1))
    for watched in common.listed(cfg, 'watches'):
        w = spec(ws, watched)
        beat, far = mark(ws, watched, 'beat'), shared(ws, watched)[1]
        # an agent in this clone is read from its own files; one in another clone from what it shared, an hour coarser
        here = beat.exists() and beat.stat().st_mtime >= when(far.get('beat'))
        seen, grace = (beat.stat().st_mtime, 0) if here else (when(far.get('beat')), BEAT_SHARED)
        if now - seen > 2 * 60 * float(w['interval']) + grace:
            found.append((1, f'{watched}: no tick within twice its interval', f'alive:{watched}'))
        for item, at in (load(ws, watched, 'pool') if here else far.get('pool') or {}).items():
            launched = when(at)
            if now - launched > stuck * 3600:
                found.append((2, f'{watched}: {item} has been in progress over {cfg.get("stuck_hours", 8)} hours with no report', f'stuck:{item}'))
        if mark(ws, watched, 'pause').exists() or (not here and far.get('paused')):
            found.append((4, f'{watched} is paused', f'paused:{watched}'))
    ok, status = common.git(ws, 'status', '--porcelain')
    old = [l[3:] for l in status.splitlines() if age_hours(ws, l[3:], now) > dirty] if ok else []
    if old:
        found.append((3, f'{len(old)} files uncommitted for over {cfg.get("dirty_hours", 1)} hours, such as {old[0]}', 'dirty'))
    ok, ahead = common.git(ws, 'rev-list', '--count', '@{u}..HEAD')
    if ok and ahead.isdigit() and int(ahead) and age_hours(ws, '.git/HEAD', now) > dirty:
        found.append((3, f'{ahead} commits not shared for over {cfg.get("dirty_hours", 1)} hours', 'unshared'))
    return sorted(found)


def monitor(ws, name, now=None, dry=False):
    """`dry` is a trial tick: it says what it would tell, and posts, shares and remembers nothing."""
    now = now or time.time()
    if dry:
        return 'dry-run', [f'would tell: {text}' for _, text, _ in findings(ws, name, now, fetch=False)]
    mark(ws, name, 'beat', stamp(now))
    if mark(ws, name, 'pause').exists():
        return finish(ws, name, 'paused', [])
    found = findings(ws, name, now)
    told = load(ws, name, 'told')
    for _, text, key in found:
        if now - told.get(key, 0) < DAY:
            continue
        note = common.state_dir(ws) / f'agent-{name}.note'
        note.write_text(f'{text}\n', encoding='utf-8')
        sent = slot_rows(ws, 'ask', 'notify', str(note))
        if sent is not None:
            told[key] = now
        mark(ws, name, 'told', json.dumps(told))
        return finish(ws, name, 'told', [text])
    return finish(ws, name, 'quiet' if not found else 'known', [t for _, t, _ in found])


def release(ws, name, now=None, dry=False):
    now = now or time.time()
    cfg = spec(ws, name)
    if not dry:
        mark(ws, name, 'beat', stamp(now))
    watching, told, notes = load(ws, name, 'watching'), load(ws, name, 'told'), []
    for row in slot_rows(ws, 'tracker', 'list', '--state', 'done') or []:
        watching.setdefault(row['id'], now)
    for item, since in list(watching.items()):
        bad = []
        for system in common.listed(cfg, 'systems'):
            checks = slot_rows(ws, 'monitoring', 'checks', system)
            if not checks:
                bad.append(f'{system}: the monitoring slot reports no checks, so nothing can be called passing')
            bad += [f"{system}/{c['check']}: {c.get('detail') or c['state']}" for c in checks or [] if c['state'] != 'passing']
        over = now - since > float(cfg.get('window_hours', 24)) * 3600
        verdict = 'FAIL' if bad else 'PASS' if over else 'WATCHING'
        if dry:
            notes += [f'would tell: {item}: {b}' for b in bad if f'{item}:{b}' not in told] or [f'{item}: {verdict}, nothing to tell']
            continue
        rec = Path(ws) / 'sessions' / 'release-monitor' / f'{item}.md'
        rec.parent.mkdir(parents=True, exist_ok=True)
        rec.write_text(f'# Release watch: {item}\n\nVerdict: {verdict}\n\n' + ''.join(f'- {b}\n' for b in bad), encoding='utf-8')
        if bad and not all(f'{item}:{b}' in told for b in bad):
            note = common.state_dir(ws) / f'agent-{name}.note'
            note.write_text(f'Release watch FAIL for {item}\n' + ''.join(f'- {b}\n' for b in bad), encoding='utf-8')
            if slot_rows(ws, 'ask', 'notify', str(note)) is not None:
                told.update({f'{item}:{b}': now for b in bad})
                notes.append(f'{item}: FAIL told')
        if over and not bad:
            del watching[item]
    if dry:
        return 'dry-run', notes
    mark(ws, name, 'watching', json.dumps(watching))
    mark(ws, name, 'told', json.dumps(told))
    records = sorted((Path(ws) / 'sessions' / 'release-monitor').glob('*.md'))
    said = share(ws, name, now, records)
    return finish(ws, name, 'told' if notes else 'quiet', notes + said)


def main(argv=None):
    p = argparse.ArgumentParser(prog='agent.py')
    p.add_argument('--ws', default='.')
    p.add_argument('verb', choices=('tick', 'monitor', 'release', 'wait', 'pause', 'resume', 'last'))
    p.add_argument('name')
    p.add_argument('rest', nargs='*', help='wait: ITEM KEY')
    p.add_argument('--dry-run', action='store_true', help='monitor, release: a trial tick that posts, shares and remembers nothing')
    a = p.parse_args(argv)
    ws = Path(a.ws).resolve()
    if a.verb == 'wait':
        if len(a.rest) != 2:
            p.error('wait takes NAME ITEM KEY')
        print(wait(ws, a.name, *a.rest)[1][0])
    elif a.verb == 'pause':
        mark(ws, a.name, 'pause', stamp(time.time()))
    elif a.verb == 'resume':
        mark(ws, a.name, 'pause').unlink(missing_ok=True)
    elif a.verb == 'last':
        print(mark(ws, a.name, 'last').read_text(encoding='utf-8') if mark(ws, a.name, 'last').exists() else 'never')
    else:
        if a.dry_run and a.verb == 'tick':
            p.error('--dry-run is for monitor and release: a card tick claims items and starts workers')
        word, notes = {'tick': tick, 'monitor': monitor, 'release': release}[a.verb](ws, a.name, **({'dry': True} if a.dry_run else {}))
        print('\n'.join(notes) if notes else word)
    return 0


if __name__ == '__main__':
    sys.exit(main())
