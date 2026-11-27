#!/usr/bin/env python3
"""One tested writer for a run's records: the run ledger, the phase log and the blocker register.

  run.py --ws W --run R plan ITEM...            read each item from the tracker slot, write the run ledger, print the lanes
  run.py --ws W --run R state [ITEM]            open blockers, where every item is, what can be dispatched now
  run.py --ws W --run R write FILE|-            apply a batch to the three files, as one commit of those files
  run.py --ws W --run R dispatch ITEM --brief F --worktree DIR
                                                check the item may start, bind its worktree, write its sandbox
                                                settings, print the command that starts its worker
  run.py --ws W --run R confirm ITEM            the close-out checklist, read from the item's own records
  run.py --ws W --run R follow                  move each tracker item to the state its last phase earns
  run.py --ws W --run R rails                   the rules a controller keeps, as the start hook says them

R is an epic run or, for a single item worked by one session, the item's own key. The files are
sessions/<R>/run-ledger.md, phase-log.md and blockers.md.

A batch is JSON, {"message": "<commit subject>", "records": [...]}, each record one of:
  {"op": "block", "missing": .., "items": .., "owner": .., "resume": .., "ask": ..}   a new blocker row; ask optional
  {"op": "edit", "id": "3", "status": "cleared", "note": .., "owner": .., ...}       any cell of a row
  {"op": "move", "item": "W-4", "to": "Coding", "why": .., "from": ..}                "from" defaults to the last move
  {"op": "item", "item": "W-4", "set": {"worker": .., "branch": .., "review": .., "next": ..}}
Nothing is written unless the whole batch passes. The clock stamps every line.

A blocker is keyed by the missing thing, never by the item: one row names every item that waits on it. A move
goes only along the ladder below or to parked, Open or Abandoned, and a move back to Coding or Local checks from
Review request or later opens its why with a cause token (ci: review: qa: po: reopen: ext: scope:).
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import approval
import common
from untrusted import shown

LADDER = ('Intake', 'Coding', 'Local checks', 'Review request', 'Waiting build', 'Reading build', 'Waiting review',
          'Triaging findings', 'Deploy to test', 'Waiting test deploy', 'Test checks', 'Evidence on item', 'Ready',
          'Peer review', 'Owner review', 'Ready for release', 'Merged', 'Released', 'Done')
OFF_LADDER = ('parked', 'Open', 'Abandoned')
BACK_TO, BACK_FROM = ('Coding', 'Local checks'), LADDER.index('Review request')
CAUSE = re.compile(r'^(ci|review|qa|po|reopen|ext|scope):')
ASKS = ('grant', 'secret', 'access', 'direction', 'scope', 'environment', 'reviewer', 'ci')
REG_CAP, LOG_CAP = 400, 200
CELLS = ('missing', 'items', 'owner', 'resume')
LEDGER_CELLS = ('title', 'needs', 'worker', 'branch', 'review', 'next')
ROW = re.compile(r'^\| (\d+) \| ')
MOVE = re.compile(r'^(\S+) (\S+) (.+?) -> (.+?)  (.*)$')
# What a person, never an agent, moves an item to
PERSONS = ('Merged', 'Released', 'Done')
# The tracker state each phase earns, by the first phase of each stretch; a team's own map goes under run: states:
STATES = {'Intake': 'in progress', 'Review request': 'in review', 'Ready for release': 'ready for release'}
BRIEF_SECTIONS = ('## Goal', '## Done when', '## Reads', '## Rails', '## Park', '## Report')
UNSETTLED = re.compile(r'\b(TBC|TBD|to confirm|to be confirmed|assumed)\b', re.I)
RAILS = """If you are driving a run (workers started in the background), these rules still bind after a compaction.
- You never implement. Work nobody did is a dispatch, not a job you pick up: send it to the worker that owns the
  item, or start one.
- You never poll by hand. Start one background waiter; nothing else to do means the tick is over.
- Wide reads go to a sub-agent that returns a digest: the sweep of open review requests, any screenshot, any long
  log. Their bytes do not enter this thread.
- Workers commit and report a commit id. You share.
- Your workers outlived the compaction. List the running sessions before you conclude anything about who is working.
- Records: `run.py state` to read, `run.py write` to write, then `run.py follow`, the only writer of tracker states.
  A tracker comment is final or parked on a person, nothing in between.
- A rule, a decision, a measured fact or a workaround goes into the workspace first; a brief names that file and
  never holds the only copy."""


class Refused(Exception):
    pass


def stamp(day=False):
    return datetime.now(timezone.utc).strftime('%Y-%m-%d' if day else '%Y-%m-%dT%H:%MZ')


def cell(value):
    return ' '.join(str(value).replace('|', '/').split())


class Run:
    def __init__(self, ws, run):
        if not re.fullmatch(r'[A-Za-z0-9][\w.-]{0,59}', run):
            raise Refused(f'a run is named like a folder: letters, digits, _ . - only, got {run!r}')
        self.ws, self.name, self.dir = Path(ws), run, Path(ws) / 'sessions' / run
        self.files = {n: self.dir / f'{n}.md' for n in ('run-ledger', 'phase-log', 'blockers')}

    def text(self, name):
        f = self.files[name]
        return f.read_text(encoding='utf-8') if f.is_file() else ''

    def blockers(self):
        rows = []
        for line in self.text('blockers').splitlines():
            if ROW.match(line):
                c = [x.strip() for x in line.strip().strip('|').split('|')]
                rows.append(dict(zip(('id', *CELLS, 'status'), c)))
        return rows

    def moves(self):
        return [m.groups() for m in map(MOVE.match, self.text('phase-log').splitlines()) if m]

    def phases(self):
        return {item: to for _, item, _, to, _ in self.moves()}

    def ledger(self):
        rows = {}
        for line in self.text('run-ledger').splitlines():
            c = [x.strip() for x in line.strip().strip('|').split('|')]
            if line.startswith('| ') and len(c) == 7 and c[0] not in ('item', '---'):
                rows[c[0]] = dict(zip(LEDGER_CELLS, c[1:]))
        return rows

    def waiting_on(self, item):
        """Why the item cannot be dispatched now, as a list; empty when it can."""
        ledger, phases, why = self.ledger(), self.phases(), []
        for need in ledger.get(item, {}).get('needs', '').split():
            if need not in ledger:
                why.append(f'{need} is outside this run: a blocker row or a person says when it is met')
            elif phases.get(need) not in LADDER[LADDER.index('Ready'):]:
                why.append(f"{need} is at {phases.get(need, 'Open')}, not yet Ready")
        why += [f"blocker {b['id']}: {b['missing']}" for b in self.blockers()
                if b['status'].startswith('open') and item in re.split(r'[\s,;]+', b['items'])]
        return why

    def render(self, ledger, log, register):
        head = '| item | title | needs | worker | branch | review | next |\n| --- | --- | --- | --- | --- | --- | --- |\n'
        out = {'run-ledger': f'# Run ledger: {self.name}\n\n' + head + ''.join(
            f"| {i} | " + ' | '.join(r.get(k, '') for k in LEDGER_CELLS) + ' |\n' for i, r in ledger.items())}
        out['phase-log'] = f'# Phase log: {self.name}\n\n' + ''.join(l + '\n' for l in log)
        out['blockers'] = (f'# Blockers: {self.name}\n\nOne row per missing thing, never per item.\n\n'
                           '| id | missing | items | owner | resume | status |\n| --- | --- | --- | --- | --- | --- |\n'
                           + ''.join('| ' + ' | '.join(b[k] for k in ('id', *CELLS, 'status')) + ' |\n' for b in register))
        return out

    def save(self, ledger, log, register, message):
        self.dir.mkdir(parents=True, exist_ok=True)
        for name, text in self.render(ledger, log, register).items():
            self.files[name].write_text(text, encoding='utf-8')
        if common.storage_of(self.ws) == 'git':
            paths = [str(f.relative_to(self.ws)) for f in self.files.values()]
            common.git(self.ws, 'add', '--', *paths)
            ok, out = common.git(self.ws, 'commit', '-q', '-m', message, '--', *paths)
            return ok or 'nothing to commit' in out
        return True


def apply(run, batch):
    """The three files after the batch, or Refused naming the first record that does not pass."""
    if not isinstance(batch, dict) or not str(batch.get('message') or '').strip() or not isinstance(batch.get('records'), list):
        raise Refused('a batch is {"message": "<commit subject>", "records": [...]}')
    ledger, register = run.ledger(), run.blockers()
    log = [l for l in run.text('phase-log').splitlines() if MOVE.match(l)]
    phases = run.phases()
    for n, r in enumerate(batch['records'], 1):
        op = r.get('op') if isinstance(r, dict) else None
        where = f'record {n} ({op})'
        if op == 'block':
            if any(not str(r.get(k) or '').strip() for k in CELLS):
                raise Refused(f"{where}: a blocker names what is missing, every item that waits, who owns it and the observable "
                              'event that resumes it')
            if r.get('ask') is not None and r['ask'] not in ASKS:
                raise Refused(f"{where}: ask is one of {', '.join(ASKS)}")
            row = {'id': str(max([int(b['id']) for b in register] or [0]) + 1), **{k: cell(r[k]) for k in CELLS},
                   'status': f'open {stamp(day=True)}' + (f" ask={r['ask']}" if r.get('ask') else '')}
            if len(' | '.join(row.values())) > REG_CAP:
                raise Refused(f'{where}: a blocker row is at most {REG_CAP} characters; the detail belongs in the item\'s record')
            register.append(row)
        elif op == 'edit':
            row = next((b for b in register if b['id'] == str(r.get('id'))), None)
            if not row:
                raise Refused(f"{where}: there is no blocker {r.get('id')}")
            row.update({k: cell(r[k]) for k in CELLS if r.get(k)})
            if r.get('status'):
                if r['status'] not in ('open', 'cleared'):
                    raise Refused(f'{where}: a status is open or cleared')
                ask = re.search(r' ask=\w+', row['status'])
                row['status'] = f"{r['status']} {stamp(day=True)}{ask.group(0) if ask else ''}" + (f": {cell(r['note'])}" if r.get('note') else '')
        elif op == 'move':
            item, to = str(r.get('item') or ''), str(r.get('to') or '')
            was = str(r.get('from') or phases.get(item) or 'Open')
            why = cell(r.get('why') or '')
            if not re.fullmatch(r'[\w.-]+', item) or to not in (*LADDER, *OFF_LADDER):
                raise Refused(f"{where}: a move names its item and a phase of the ladder ({', '.join(LADDER)}) or one of "
                              f"{', '.join(OFF_LADDER)}")
            if not why:
                raise Refused(f'{where}: a move says why')
            back = to in BACK_TO and was in LADDER and LADDER.index(was) >= BACK_FROM
            if back and not CAUSE.match(why):
                raise Refused(f'{where}: a move back to {to} from {was} opens its why with a cause token: ci: review: qa: po: reopen: '
                              'ext: scope:')
            line = f'{stamp()} {item} {was} -> {to}  {why}'
            if len(line) > LOG_CAP:
                raise Refused(f'{where}: a phase line is at most {LOG_CAP} characters; the detail belongs in the item\'s record')
            log.append(line)
            phases[item] = to
        elif op == 'item':
            item, given = str(r.get('item') or ''), r.get('set') or {}
            if not re.fullmatch(r'[\w.-]+', item) or not isinstance(given, dict) or any(k not in LEDGER_CELLS for k in given):
                raise Refused(f"{where}: an item record sets some of {', '.join(LEDGER_CELLS)}")
            ledger.setdefault(item, dict.fromkeys(LEDGER_CELLS, '')).update({k: cell(v) for k, v in given.items()})
        else:
            raise Refused(f'record {n}: op is one of block, edit, move, item')
    return ledger, log, register


def slot_rows(ws, slot, *args):
    """The rows a slot verb prints, read straight from the team's adapter; a slot that is not filled gives none."""
    prog = Path(ws) / 'slots' / slot
    if not prog.is_file():
        return None
    try:
        r = subprocess.run([str(prog), *args], cwd=ws, capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    rows = []
    for line in r.stdout.splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        rows += [row] if isinstance(row, dict) else []
    return rows


def plan(run, items):
    ledger = run.ledger()
    for item in items:
        rows = slot_rows(run.ws, 'tracker', 'read', item)
        if not rows:
            raise Refused(f'{item} could not be read from the tracker slot: fill the slot, or write its ledger row with an item record')
        ledger.setdefault(item, dict.fromkeys(LEDGER_CELLS, '')).update(
            title=cell(shown(rows[0].get('title'), 80)), needs=' '.join(str(n) for n in rows[0].get('needs') or []))
    run.save(ledger, [l for l in run.text('phase-log').splitlines() if MOVE.match(l)], run.blockers(), f'run {run.name}: plan')
    return lanes(ledger)


def lanes(ledger):
    """The items in the order the graph allows: each list can run at once, after the lists before it."""
    left, done, out = dict(ledger), set(), []
    while left:
        now = [i for i, r in left.items() if all(n in done or n not in ledger for n in r['needs'].split())]
        if not now:
            raise Refused(f"the items wait on each other in a circle: {', '.join(left)}")
        out.append(now)
        done.update(now)
        left = {i: r for i, r in left.items() if i not in now}
    return out


def state(run, item=None):
    ledger, phases, lines = run.ledger(), run.phases(), []
    if item:
        lines += [f'{item}: ' + ', '.join(f'{k} {v}' for k, v in ledger.get(item, {}).items() if v)]
        lines += [f'  {at} {was} -> {to}  {why}' for at, i, was, to, why in run.moves() if i == item]
        lines += [f'  waits: {w}' for w in run.waiting_on(item)]
        return lines
    opened = [b for b in run.blockers() if b['status'].startswith('open')]
    lines.append(f'open blockers: {len(opened)}')
    lines += [f"  {b['id']}: {b['missing']} (items {b['items']}; owner {b['owner']}; resumes when {b['resume']}; {b['status']})" for b in opened]
    for i, row in ledger.items():
        phase = phases.get(i, 'Open')
        waits = run.waiting_on(i) if phase == 'Open' else []
        mark = 'can be dispatched now' if phase == 'Open' and not waits else '; '.join(waits)
        lines.append(f'{i}: {phase}{worker_seen(run, i, row)}' + (f' ({mark})' if mark else ''))
    return lines


def worker_seen(run, item, row):
    """What is known of the item's worker. A printed start command is not a worker: the runtime may have stopped it at
    a prompt nobody saw, so only a session opened for the item says one is there."""
    opened = any(e.get('ev') == 'start' and e.get('subject') == item for e in common.load_events(run.ws)[0])
    if row.get('worker') or opened:
        return f" (worker {row.get('worker') or 'session open'}, {gates_seen(run.ws, item)})"
    if (run.dir / 'workers' / f'{item}.goal').is_file():
        return ' (start command printed, no worker session has opened for it: look at the runtime\'s own list of background sessions)'
    return ''


def gates_seen(ws, item):
    """Whether the gate hook has run in a session that filed under this item: the one sign a worker loaded the gates."""
    sids = {e.get('sid') for e in common.load_events(ws)[0] if e.get('ev') == 'start' and e.get('subject') == item}
    for f in common.state_dir(ws).glob('filed.*'):
        if sids & set(f.read_text(encoding='utf-8').split()):
            return 'gate hook seen in its session'
    return 'gate hook not seen in its session'


def bind(worktree, ws, run, item):
    """Tie a worktree outside the workspace to it, in the machine's own folder, where no checkout can carry it."""
    real = Path(worktree).resolve()
    f = common.config_dir() / 'bound' / hashlib.sha256(str(real).encode()).hexdigest()[:24]
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({'worktree': str(real), 'workspace': str(Path(ws).resolve()), 'run': run, 'item': item}), encoding='utf-8')


def sandbox(ws, item, tree):
    """The sandbox a worker on this item runs in. The spawn check compares a start's settings with this, so a file
    edited after dispatch wrote it starts nothing."""
    ws, tree = Path(ws).resolve(), Path(tree)
    cfg = common.config(ws).get('run')
    domains = common.listed(cfg, 'allowed_domains') if isinstance(cfg, dict) else []
    ok, gitdir = common.git(tree, 'rev-parse', '--path-format=absolute', '--git-dir')
    ok2, shared = common.git(tree, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    git_paths = [gitdir, *(f'{shared}/{d}' for d in ('objects', 'refs', 'logs'))] if ok and ok2 else []
    # A worker opens its own session and files under it: the ledger and the sitting's state, never the records a yes is read from
    state = common.state_dir(ws)
    return {'enabled': True, 'autoAllowBashIfSandboxed': True, 'allowUnsandboxedCommands': False,
            'filesystem': {'allowWrite': [str(tree), str(ws / 'sessions' / item), *git_paths, str(ws / 'telemetry' / 'events'), str(state)],
                           'denyWrite': ['~/.ssh', str(state / 'ask')]},
            'network': {'strictAllowlist': True, 'allowLocalBinding': True, 'allowedDomains': domains}}


def settings(ws, item, tree):
    """The whole settings file of a worker's start. The spawn check compares the file with this, key for key."""
    return {'sandbox': sandbox(ws, item, tree)}


def work_area(ws, worktree):
    """The folder a worker may be bound to: the top of a git worktree of a repository the team declared. A binding makes
    a folder count as the workspace's for the gate, so a broad folder is never one."""
    tree, ws, home = Path(os.path.realpath(worktree)), Path(os.path.realpath(ws)), Path(os.path.realpath(Path.home()))
    if tree == Path(tree.anchor):
        raise Refused('the file system root is never a work area')
    if tree == home or tree in home.parents:
        raise Refused(f'{tree} is the home folder or holds it: a work area is one worktree, never a folder that broad')
    if tree == ws:
        raise Refused('the workspace itself is not a work area: a worker works in a worktree of a code repository')
    if tree in ws.parents:
        raise Refused(f'{tree} holds the workspace: a work area is one worktree, never a folder that broad')
    ok, top = common.git(tree, 'rev-parse', '--path-format=absolute', '--show-toplevel') if tree.is_dir() else (False, '')
    if not ok or Path(os.path.realpath(top)) != tree:
        raise Refused(f'{worktree} is not a git worktree (its top folder): make one first (git worktree add)')
    shared = common.git(tree, 'rev-parse', '--path-format=absolute', '--git-common-dir')[1]
    repo = Path(os.path.realpath(shared))
    folder = repo.parent if repo.name == '.git' else repo
    address = common.git(tree, 'config', '--get', 'remote.origin.url')[1].rstrip('/')
    declared = [d.rstrip('/') for d in common.listed(approval.approved_config(ws), 'repositories')]
    if any(os.path.realpath(os.path.expanduser(d)) == str(folder) for d in declared):
        return tree
    if not address or address not in declared:
        raise Refused(f'the repository of {tree} is not one the team declared: a person lists the team\'s code repositories under '
                      '`repositories:` in workspace.yaml (a control file), by folder or by the address it is cloned from')
    # The address is the folder's own word for itself, and any folder can be given one: where this person keeps their
    # copies is what makes it theirs
    mine = [Path(os.path.realpath(a)) for a in common.areas()]
    if not any(folder == a or a in folder.parents for a in mine):
        raise Refused(f'{folder} carries a declared address but is in no working area declared on this machine: the person lists '
                      f'where their copies live, one full path per line, in {common.config_dir() / "areas"}, by hand')
    return tree


def dispatch(run, item, brief, worktree):
    ledger = run.ledger()
    if item not in ledger:
        raise Refused(f'{item} is not in the run ledger: plan it first')
    ready = run.dir / 'readiness.md'
    first = ready.read_text(encoding='utf-8').splitlines()[:1] if ready.is_file() else ['']
    if not re.search(r'Verdict:\s*READY(?! FOR)|Verdict:\s*READY FOR\b.*\b' + re.escape(item) + r'\b', first[0]):
        raise Refused(f'sessions/{run.name}/readiness.md does not say "Verdict: READY" for {item} on its first line: run the '
                      'readiness skill and get the person\'s answers before the first dispatch')
    if run.phases().get(item, 'Open') not in ('Open', 'parked'):
        raise Refused(f'{item} is at {run.phases()[item]}: a worker already has it. Send it back to that worker')
    waits = run.waiting_on(item)
    if waits:
        raise Refused(f"{item} cannot start: {'; '.join(waits)}")
    text = Path(brief).read_text(encoding='utf-8') if Path(brief).is_file() else ''
    missing = [s for s in BRIEF_SECTIONS if not re.search(rf'(?m)^{re.escape(s)}\s*$', text)]
    if missing:
        raise Refused(f"the brief lacks {', '.join(missing)} (template: the run mode's templates/brief.md)")
    loose = UNSETTLED.search(text)
    if loose:
        raise Refused(f'the brief still says "{loose.group(0)}": a worker cannot ask, so every open point is settled in the '
                      'readiness record before it starts')
    tree = work_area(run.ws, worktree)
    bind(tree, run.ws, run.name, item)
    work = run.dir / 'workers'
    work.mkdir(parents=True, exist_ok=True)
    (run.ws / 'sessions' / item).mkdir(parents=True, exist_ok=True)
    record = (run.ws / 'sessions' / item).resolve()
    (work / f'{item}.settings.json').write_text(json.dumps(settings(run.ws, item, tree), indent=1), encoding='utf-8')
    goal = (f'/goal Read {Path(brief).resolve()} as a file and do what it says. Done when the end state under "Done when" in '
            'that file is stated in this conversation with its evidence, or a clean park is stated: what is missing, who owns '
            'it, and the observable condition that resumes it.')
    (work / f'{item}.goal').write_text(goal + '\n', encoding='utf-8')
    # a start typed inside a session inherits the mark of a child session, and a worker so marked saves no transcript
    return ('env -u CLAUDE_CODE_CHILD_SESSION claude --bg "$(cat ' + str(work / f'{item}.goal') + ')" --permission-mode bypassPermissions --disallowed-tools '
            f'AskUserQuestion --autocompact 250000 --add-dir {tree} --add-dir {record} --plugin-dir {Path(__file__).resolve().parent.parent} '
            f'--settings {work / f"{item}.settings.json"}')


def confirm(run, item):
    """What the close-out checklist still lacks for this item, read from its own records and never re-run."""
    lacks, row = [], run.ledger().get(item, {})
    ends = [e for e in common.load_events(run.ws)[0] if e.get('ev') == 'end' and e.get('outcome') == 'done'
            and any(s.get('sid') == e.get('sid') and s.get('subject') == item for s in common.load_events(run.ws)[0] if s.get('ev') == 'start')]
    if not ends:
        lacks.append('no session on this item has ended done with how the goal was checked (event.py close --outcome done --goal-met)')
    import event
    qa = event.qa_problem(run.ws, item)
    if qa:
        lacks.append(qa.split('. ')[0])
    report = run.ws / 'sessions' / item / 'report.md'
    said = report.read_text(encoding='utf-8') if report.is_file() else ''
    if not said.strip():
        lacks.append(f'sessions/{item}/report.md is missing: the worker\'s last step writes its report there')
    elif not re.search(r'\b[0-9a-f]{7,40}\b', said):
        lacks.append('the report names no commit id')
    if re.search(r'\bNOT PROVEN\b', said):
        lacks.append('the report holds an acceptance point marked NOT PROVEN')
    if row.get('review'):
        rows = slot_rows(run.ws, 'code-host', 'status', row['review'])
        if rows is None:
            lacks.append(f"the code-host slot could not read {row['review']}: ask a person for its build and review state")
        elif rows:
            bad = [n for n, s in (rows[0].get('checks') or {}).items() if s != 'passed']
            lacks += [f"checks not passed on {row['review']}: {', '.join(bad)}"] if bad else []
            lacks += [f"{rows[0].get('open_findings')} findings still open on {row['review']}"] if rows[0].get('open_findings') else []
    else:
        lacks.append('the run ledger names no review request for this item')
    return lacks


def follow(run):
    """Move each tracker item to the state its last phase earns. Never past ready for release: the rest is a person's."""
    cfg = common.config(run.ws).get('run')
    states = {**STATES, **(cfg.get('states') if isinstance(cfg, dict) and isinstance(cfg.get('states'), dict) else {})}
    said = []
    for item, phase in run.phases().items():
        if phase not in LADDER or phase in PERSONS:
            continue
        want = next((states[p] for p in reversed(LADDER[:LADDER.index(phase) + 1]) if p in states), None)
        rows = slot_rows(run.ws, 'tracker', 'read', item)
        if rows is None:
            said.append(f'{item}: the tracker slot did not answer; ask a person to set it to "{want}"')
        elif rows and want and rows[0].get('state') != want and rows[0].get('state') != 'done':
            moved = slot_rows(run.ws, 'tracker', 'move', item, *want.split())
            said.append(f'{item}: {rows[0].get("state")} -> {want}' if moved else f'{item}: the tracker refused "{want}"')
    return said


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0], allow_abbrev=False)
    p.add_argument('--ws', required=True)
    p.add_argument('--run', required=True)
    sub = p.add_subparsers(dest='cmd', required=True)
    sub.add_parser('plan').add_argument('items', nargs='+')
    sub.add_parser('state').add_argument('item', nargs='?')
    sub.add_parser('write').add_argument('file')
    d = sub.add_parser('dispatch')
    d.add_argument('item')
    d.add_argument('--brief', required=True)
    d.add_argument('--worktree', required=True)
    sub.add_parser('confirm').add_argument('item')
    sub.add_parser('follow')
    sub.add_parser('rails')
    a = p.parse_args(argv)
    try:
        run = Run(a.ws, a.run)
        if a.cmd == 'rails':
            print(RAILS)
        elif a.cmd == 'plan':
            for n, lane in enumerate(plan(run, a.items), 1):
                print(f"step {n}: {', '.join(lane)}")
            print('Show the person these lanes, the shared surfaces and the first dispatch, and wait for their word.')
        elif a.cmd == 'state':
            print('\n'.join(state(run, a.item)))
        elif a.cmd == 'write':
            raw = sys.stdin.read() if a.file == '-' else Path(a.file).read_text(encoding='utf-8')
            try:
                batch = json.loads(raw)
            except ValueError as e:
                raise Refused(f'the batch is not JSON: {e}')
            if not run.save(*apply(run, batch), str(batch['message'])):
                raise Refused('the files were written but the commit was refused: commit them by path')
            print(f"wrote {len(batch['records'])} records to sessions/{run.name}/")
        elif a.cmd == 'dispatch':
            print(dispatch(run, a.item, a.brief, a.worktree))
        elif a.cmd == 'confirm':
            lacks = confirm(run, a.item)
            print('\n'.join(lacks) if lacks else f'{a.item}: every row of the close-out checklist is there')
            return 1 if lacks else 0
        elif a.cmd == 'follow':
            print('\n'.join(follow(run)) or 'the tracker already agrees with the phase log')
    except Refused as e:
        print(f'run: {e}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
