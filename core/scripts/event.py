#!/usr/bin/env python3
"""The Trampo ledger and the journal.

  event.py open    --ws DIR --kind KIND --subject NAME [--session ID] [--source S] [--parent SID] [--note TEXT]
                   (start a ledger for this subject, or pick up the one left open, and name it for the prompt hook)
  event.py close   --ws DIR [--session ID] (--outcome O [--goal-met HOW] [--fp F] [--prior P] | --park --cause C [--ask A]) [--note TEXT]
                   (end the ledger, or park it on a person with no end; safe to run twice)
  event.py emit    --ws DIR --sid SID --kind KIND --ev EV [--subject NAME] [--parent SID] [--cause TAG] [--subtag TEXT]
                   [--ask CLASS] [--by agent|review] [--source S] [--risk R] [--prior P] [--fp SYSTEM:CLASS]
                   [--outcome O] [--goal-met HOW] [--refs a,b] [--min N] [--note TEXT] [--usage JSON]
                   [--worker ID] [--model NAME] [--effort LEVEL] [--what W] [--severity S]
  event.py report  --ws DIR [--since DAY] [--until DAY]   (sessions, touches by cause, blocks, outcomes, repeated failure classes)
  event.py waiting --ws DIR                               (every block nobody has cleared, oldest first)
  event.py whoami  --ws DIR                               (who this machine says is at the keyboard)
  event.py journal --ws DIR --sid SID --path REL (--from FILE | --remove | --diff | --restore | --adopt --accepted-by NAME)
                   [--approval proposals/X.md]            (storage: files only: every memory write, with its whole text)

The lists each field takes are in core/schemas/event.schema.json; the rules are in protocols/write.md.
"""
import argparse
import difflib
import hashlib
import json
import os
import re
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import common
from common import append, config, identity, load_events, path_problem, session_events, state_dir, stats_lines, storage_of
from untrusted import DATA, SID_RE, lines as file_lines, outlast_reader, shown

KINDS = ('adhoc', 'card', 'triage', 'run', 'review', 'monitor')
EVS = ('start', 'touch', 'block', 'clear', 'spawn', 'end', 'usage', 'wrong')
# Written only by the code that checks them: the gate hook records a person's yes, the journal its own writes
OWN_WRITER = {'approve': "the gate hook, when it reads an approver's own yes", 'write': 'event.py journal', 'remove': 'event.py journal'}
# `untagged` is what the prompt hook writes before the close gives a touch its cause
CAUSES = ('criteria', 'direction', 'verification', 'tooling', 'collision', 'approval-gate', 'intake', 'other', 'untagged')
ASKS = ('grant', 'secret', 'access', 'direction', 'scope', 'environment', 'reviewer', 'ci')
BYS = ('agent', 'review')
# A class of work is channel plus fp, so a free-text channel would split one class in two
SOURCES = ('tracker', 'chat', 'email', 'monitoring', 'person', 'other')
RISKS = ('low', 'medium', 'high')
PRIORS = ('found', 'missed', 'none')
OUTCOMES = ('done', 'parked', 'abandoned', 'no-action', 'card-raised', 'handed-off')
EFFORTS = ('off', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max')
WHATS = ('direction', 'action')
SEVERITIES = ('safety', 'quality', 'velocity')
NOTE_CAP, SUBTAG_CAP = 140, 40
NOT_A_PERSON = ('loop', 'peer', 'notification')
SPAWN_FIELDS = ('worker', 'model', 'effort')
FIELDS = ('parent', 'subject', 'cause', 'subtag', 'ask', 'by', 'source', 'risk', 'prior', 'fp', 'outcome', 'refs', 'min', 'note',
          'usage', *SPAWN_FIELDS, 'what', 'severity')
SUBJECT = re.compile(r'[A-Za-z0-9_-][A-Za-z0-9_.-]{0,59}')
SESSION_VAR = 'CLAUDE_CODE_SESSION_ID'


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest() if text is not None else ''


def stamp():
    return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M')


def modes_sha(ws):
    """A short hash of the team's working instructions, so a review can compare sessions before and after an edit."""
    h = hashlib.sha256()
    for f in sorted((Path(ws) / 'modes').glob('*.md')):
        if not path_problem(ws, f'modes/{f.name}'):
            h.update(f.name.encode() + b'\0' + f.read_bytes() + b'\0')
    return h.hexdigest()[:12]


def fp_type(s):
    if not re.fullmatch(r'[\w.-]+:[\w.-]+', s):
        raise argparse.ArgumentTypeError(f'--fp is <system>:<failure-class>, got {s!r}')
    return s


def usage_type(s):
    try:
        obj = json.loads(s)
    except ValueError:
        obj = None
    flat = (str, int, float, bool, type(None))
    if not isinstance(obj, dict) or not all(isinstance(v, flat) or (isinstance(v, list) and all(isinstance(x, flat) for x in v))
                                            for v in obj.values()):
        raise argparse.ArgumentTypeError('--usage is a flat JSON object: values are scalars or lists of scalars')
    return obj


def day_type(s):
    try:
        datetime.strptime(s, '%Y-%m-%d')
    except ValueError:
        raise argparse.ArgumentTypeError(f'a day is YYYY-MM-DD, got {s!r}')
    return s


def emit_problem(ws, a):
    """Why this event may not be written, or None."""
    if a.ev in OWN_WRITER:
        return f'{a.ev} is never written by hand: only {OWN_WRITER[a.ev]} writes it'
    if a.note is not None and len(a.note) > NOTE_CAP:
        return f'--note is at most {NOTE_CAP} characters, got {len(a.note)}; the detail belongs in the session record'
    if a.subtag is not None and (a.ev not in ('touch', 'block') or len(a.subtag) > SUBTAG_CAP):
        return f'--subtag sharpens a cause: it goes on a touch or a block and is at most {SUBTAG_CAP} characters'
    if a.ask is not None and a.ev != 'block':
        return '--ask classes the human ask a block records, so it goes on a block'
    if a.min is not None and a.min < 0:
        return '--min is minutes, 0 or more'
    if (a.ev == 'usage') != (a.usage is not None):
        return '--usage goes on a usage event, and a usage event needs it'
    if a.ev != 'spawn' and any(getattr(a, k) is not None for k in SPAWN_FIELDS):
        return '--worker, --model and --effort describe what a spawn opened, so they go on a spawn'
    if (a.ev == 'wrong') != (a.what is not None) or (a.ev == 'wrong') != (a.severity is not None):
        return '--what and --severity describe a wrong direction or action: a wrong needs both and nothing else takes them'
    if a.ev == 'block' and a.cause in (None, 'untagged'):
        return f"a block needs --cause ({', '.join(c for c in CAUSES if c != 'untagged')}): a wait nobody can attribute is not counted"
    if a.ev == 'end':
        mine = [e.get('ev') for e in session_events(ws, a.sid)]
        if 'start' not in mine:
            return (f'no start under sid {a.sid}, so there is nothing to end. A session that never opened a ledger is '
                    'backfilled first: event.py open, with --note backfilled')
        if 'end' in mine:
            return f'sid {a.sid} was already ended. More work on the subject opens a new ledger: event.py open'
        if a.outcome not in OUTCOMES:
            return f"an end needs --outcome, one of: {', '.join(OUTCOMES)}"
    done = a.ev == 'end' and a.outcome == 'done'
    if a.goal_met is not None and not done:
        return '--goal-met goes only on an end with --outcome done'
    if done and not (a.goal_met or '').strip():
        return ('a done end needs --goal-met "<how it was checked>": done means the goal in the record, in the '
                "requester's words, is met. If the work delivered less, park it and say what remains, or the requester "
                'narrows the goal on the record first')
    return None


def emit(ws, a):
    why = emit_problem(ws, a)
    if why:
        sys.exit(why)
    ev = {'kind': a.kind, 'ev': a.ev, **{k: getattr(a, k) for k in FIELDS}, 'who': identity(ws) or None}
    if a.goal_met:
        ev['goal_met'] = a.goal_met.strip()
    if a.ev == 'start':
        ev.update(core_version=common.core_version(), modes_sha=modes_sha(ws))
    return append(ws, a.sid, ev)


def emit_args(**given):
    """An emit as the other commands write one: every field the parser would set, None unless given."""
    return argparse.Namespace(**{**dict.fromkeys((*FIELDS, 'goal_met')), **given})


def waiting(ws):
    """Every block nobody has cleared, oldest first. A clear or an end settles the blocks of its session."""
    open_now, subject = {}, {}
    for e in load_events(ws)[0]:
        if e.get('ev') == 'start':
            subject[e.get('sid')] = e.get('subject')
        if e.get('ev') == 'block':
            open_now.setdefault(e.get('sid'), []).append(e)
        elif e.get('ev') in ('clear', 'end'):
            open_now.pop(e.get('sid'), None)
    now = datetime.now(timezone.utc)

    def days(e):
        try:
            return (now - datetime.strptime(e.get('ts', ''), common.TS).replace(tzinfo=timezone.utc)).days
        except ValueError:
            return 0
    out = [{'sid': e.get('sid'), 'subject': e.get('subject') or subject.get(e.get('sid')), 'cause': e.get('cause'), 'ask': e.get('ask'),
            'note': e.get('note'), 'since': e.get('ts'), 'who': e.get('who'), 'days': days(e)} for es in open_now.values() for e in es]
    return sorted(out, key=lambda w: w['since'] or '')


def active_file(ws, session):
    return state_dir(ws) / (f'active-sid.{session}' if session and SID_RE.fullmatch(session) else 'active-sid')


def open_session(ws, a):
    if not SUBJECT.fullmatch(a.subject):
        sys.exit('--subject is a short plain name (letters, digits, _ . -): it becomes the ledger file name and the folder of the record')
    events = load_events(ws)[0]
    now = common.active(ws, a.session)
    if now:
        filed = next((e.get('subject') for e in events if e.get('sid') == now[0] and e.get('ev') == 'start'), None)
        if filed == a.subject:
            return f'open {now[0]} {now[1] or a.kind}'
        sys.exit(f'this assistant session already files under {now[0]} ({filed}). Close it first (event.py close), or keep '
                 'working under it. Never overwrite it, or the prompt hook files this work under the other subject')
    starts = [e for e in events if e.get('ev') == 'start' and e.get('subject') == a.subject]
    last = starts[-1]['sid'] if starts else None
    left_open = last and not any(e.get('ev') == 'end' for e in events if e.get('sid') == last)
    if left_open:
        sid, said = last, f'resumed {last} {a.kind} (left open, nothing written)'
    else:
        sid = f'{a.subject}-{stamp()}'
        while (Path(ws) / 'telemetry' / 'events' / f'{sid}.jsonl').exists():
            sid += 'x'
        note = ' '.join(x for x in (f'resumes {last}' if last else '', a.note or '') if x) or None
        emit(ws, emit_args(sid=sid, kind=a.kind, ev='start', subject=a.subject, source=a.source, parent=a.parent, note=note))
        said = f'opened {sid} {a.kind}' + (f' (after {last})' if last else '')
    f = active_file(ws, a.session)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(f'{sid} {a.kind}\n', encoding='utf-8')
    return said


def untagged(events):
    """A person's prompts the hook counted that the close has not given a cause yet: each tagged touch stands for one of
    them. A loop wake, another agent's message and a notification are counted and never wait for a cause."""
    c = Counter(e.get('cause') or 'untagged' for e in events if e.get('ev') == 'touch' and e.get('prompt_origin') not in NOT_A_PERSON)
    return max(0, c['untagged'] - (sum(c.values()) - c['untagged']))


VERDICT_LINE = re.compile(r'(?m)^Verdict:(.*)$')
VERDICTS = ('PASS', 'FAIL', 'CANNOT-VERIFY')
# a skip carries its reason on the same line: "Verdict: SKIPPED: no local path, ..."
SKIPPED = re.compile(r'SKIPPED: *(\S.*)')
SKIP_GATE = 'close a card with QA skipped'


def qa_verdict(ws, subject):
    """(path, last verdict word or None, whether the report exists). A skip with its reason reads as SKIPPED."""
    rel = f'sessions/{subject}/qa-report.md'
    report = Path(ws) / rel
    if not report.is_file():
        return rel, None, False
    lines = VERDICT_LINE.findall(report.read_text(encoding='utf-8', errors='replace'))
    last = lines[-1].strip() if lines else None
    return rel, ('SKIPPED' if last and SKIPPED.fullmatch(last) else 'SKIPPED with no reason' if last == 'SKIPPED' else last), True


def skip_approved(ws, subject):
    """Whether an approver's yes to closing this card with QA skipped is on record. Only the gate hook writes approve
    lines, so this is the same trust as any other approval."""
    import approval
    approvers = common.listed(approval.approved_config(ws), 'approvers')
    return any(e.get('ev') == 'approve' and e.get('gate') == SKIP_GATE and e.get('key') == subject
               and any(common.same(e.get('by') or '', a) for a in approvers) for e in load_events(ws)[0])


def qa_problem(ws, subject):
    """Why a card may not close as done: the last "Verdict:" line of its QA report is not PASS. This reads one line of a
    file the session itself can write. It cannot tell whether QA ran or who ran it."""
    rel, last, there = qa_verdict(ws, subject)
    park = 'If QA cannot be run now, park the card and say what it waits on (close --park): do not close it as done'
    if not there:
        return (f'{rel} is missing, and a card closes as done only on a QA verdict of PASS. Have an independent helper check '
                f'the card against its criteria and append its pass to that file, ending with the line "Verdict: PASS". {park}')
    if last == 'PASS' or (last == 'SKIPPED' and skip_approved(ws, subject)):
        return None
    if last == 'SKIPPED':
        return (f'QA for {subject} was recorded as skipped ("Verdict: SKIPPED: <reason>") in {rel}, and no approver\'s yes to closing it that way is on '
                'record. Either QA runs and its last line is "Verdict: PASS", or an approver says yes to closing '
                f'{subject} as done with QA skipped, typed in this session (the close command then asks for it). {park}')
    if last is None:
        return (f'{rel} holds no line "Verdict: PASS": each QA pass ends with one line, "Verdict: " and one of '
                f'{", ".join(VERDICTS)}, at the start of the line. {park}')
    if last not in VERDICTS:
        return (f'the last "Verdict:" line of {rel} is not one of {", ".join(VERDICTS)} written exactly, or SKIPPED: '
                '<reason>, so it cannot be read. '
                'The QA helper writes the line again as its last line')
    return (f'the last QA verdict in {rel} is {last}, and a card closes as done only on PASS. '
            + ('Fix what failed and have QA run again' if last == 'FAIL' else
               'QA could not check it: update the runbook it lacked and have QA run again') + f'. {park}')


RUNBOOK_LINE = re.compile(r'(?mi)^runbook:[ \t]*([^<\s].*)$')


def runbook_line(ws, sid):
    """(refusal, warning) for a card closing as done, from the "runbook:" line of its record. A line that names a runbook
    that is not a file is a false statement and refuses; a forgotten line only warns (owner's decision). Whether the
    facts are in the files is the mode's rule, not read here."""
    subject = next((e['subject'] for e in session_events(ws, sid) if e.get('subject')), '')
    record = Path(ws) / 'sessions' / subject / 'session.md'
    if not subject or not record.is_file():
        return None, None
    m = RUNBOOK_LINE.search(record.read_text(encoding='utf-8', errors='replace'))
    said = m.group(1).strip() if m else ''
    paths = re.findall(r'runbooks/[\w./-]+\.md', said)
    lost = [p for p in paths if '..' in p.split('/') or not (Path(ws) / p).is_file()]
    if lost:
        return (f'the "runbook:" line of {record.relative_to(ws)} names what is not a file here: {", ".join(lost)}. Write the '
                'fact into the runbook, or correct the line, then close'), None
    if said.lower().rstrip('.') == 'none learned' or paths or (said and not (Path(ws) / 'runbooks').is_dir()):
        return None, None
    return None, (f'warning: {record.relative_to(ws)} has no "runbook:" line that says where this card\'s system facts went. '
                  'Write "runbook: <paths of the runbooks changed>" or "runbook: none learned" in its close-out'
                  + ('' if (Path(ws) / 'runbooks').is_dir() else ', or "runbook: left in <where>" since there is no runbooks folder'))


def close_session(ws, a):
    now = common.active(ws, a.session)
    if not now:
        return ('nothing to close: this assistant session files under no open ledger. Either it was closed already, or it never '
                'opened one: ask the person once whether to backfill it (event.py open --note backfilled)')
    sid, kind = now[0], now[1] or 'adhoc'
    left = untagged(session_events(ws, sid))
    tags = f' {left} untagged touches: tag each prompt that changed the work (emit --ev touch --cause <cause> --by agent).' if left else ''
    if a.park:
        emit(ws, emit_args(sid=sid, kind=kind, ev='block', cause=a.cause, ask=a.ask, note=a.note))
        return f'parked {sid}: no end is written, the ledger stays open and the same subject picks it up.{tags}'
    card_done = kind == 'card' and a.outcome == 'done'
    subject = next((e['subject'] for e in session_events(ws, sid) if e.get('subject')), '')
    why, warn = (qa_problem(ws, subject), None) if card_done else (None, None)
    if card_done and not why:
        why, warn = runbook_line(ws, sid)
    if why:
        sys.exit(why)
    emit(ws, emit_args(sid=sid, kind=kind, ev='end', outcome=a.outcome, goal_met=a.goal_met, fp=a.fp, prior=a.prior, note=a.note))
    active_file(ws, a.session).unlink(missing_ok=True)
    return f'closed {sid} ({a.outcome}).{tags}' + (f'\n{warn}' if warn else '')


DATED_SUBJECT = re.compile(r'\d{4}-\d{2}-\d{2}-(.+)')


def in_window(e, since, until):
    return (not since or e.get('ts', '') >= since) and (not until or e.get('ts', '') < until)


def report(ws, since=None, until=None):
    events = [e for e in load_events(ws)[0] if e.get('ev') != 'usage' and in_window(e, since, until)]
    by_sid = {}
    for e in events:
        by_sid.setdefault(e.get('sid'), []).append(e)
    kind_of = {sid: next((e['kind'] for e in es if e.get('kind')), None) for sid, es in by_sid.items()}
    fmt = lambda c: ', '.join(f'{k} {v}' for k, v in sorted(c.items())) or 'none'
    out = []
    for kind in KINDS:
        sids = [s for s, k in kind_of.items() if k == kind]
        if not sids:
            continue
        causes = []
        for s in sids:
            c = Counter(e.get('cause') or 'untagged' for e in by_sid[s] if e.get('ev') == 'touch')
            c['untagged'] = untagged(by_sid[s])
            causes.append(+c)
        touches = [sum(c.values()) for c in causes]
        mine = [e for s in sids for e in by_sid[s]]
        out += [f'{kind}: sessions {len(sids)}, touches/session mean {sum(touches) / len(touches):.2f} median '
                f"{statistics.median(touches):g}, blocks {sum(e.get('ev') == 'block' for e in mine)}, "
                f"spawns {sum(e.get('ev') == 'spawn' for e in mine)}",
                f'  touches by cause: {fmt(sum(causes, Counter()))}',
                f"  prompts by origin: {fmt(Counter(e.get('prompt_origin') or 'unknown' for e in mine if e.get('ev') == 'touch' and e.get('cause') == 'untagged'))}",
                f"  outcomes: {fmt(Counter(e['outcome'] for e in mine if e.get('ev') == 'end' and e.get('outcome')))}"]
    seen = {}
    for e in events:
        if e.get('fp'):
            seen.setdefault(re.sub(r'[\s_]+', '-', str(e['fp']).strip().casefold()), set()).add(e.get('sid'))
        # an incident is named for its day and its failure: the same failure on another day is the same class
        dated = DATED_SUBJECT.fullmatch(str(e.get('subject') or '')) if e.get('ev') == 'start' else None
        if dated:
            seen.setdefault(dated.group(1).casefold(), set()).add(e.get('sid'))
    repeats = [f"  {fp}: {len(sids)} sessions ({', '.join(sorted(map(str, sids)))})" for fp, sids in sorted(seen.items()) if len(sids) > 1]
    if repeats:
        out += [f'repeats, one failure class in more than one session ({DATA}):', *repeats]
    return out or ['no events']


def replay(events):
    """Fold the journal's write and remove lines into {path: text}. A prev_sha that does not match the replayed
    state means two sessions edited from the same base: a sync client's conflict."""
    state, conflicts = {}, []
    for e in events:
        if e.get('ev') not in ('write', 'remove') or not e.get('path'):
            continue
        p, cur = e['path'], state.get(e['path'])
        if (p in state or not e.get('prev_sha')) and e.get('prev_sha', '') != sha(cur):
            conflicts.append(f"{p} (session {e.get('sid')} at {e.get('ts')})")
        state[p] = e.get('text') if e['ev'] == 'write' else None
    return state, conflicts


def journal_write(ws, sid, rel, new_text, extra=None, prior_from_journal=False):
    target = Path(ws) / rel
    prior = replay(load_events(ws)[0])[0].get(rel) if prior_from_journal else (target.read_text(encoding='utf-8') if target.exists() else None)
    base = {'path': rel, 'prev_sha': sha(prior), 'who': identity(ws) or None, **(extra or {})}
    if new_text is None:
        target.unlink(missing_ok=True)
        return append(ws, sid, {**base, 'ev': 'remove'})
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(new_text, encoding='utf-8')
    return append(ws, sid, {**base, 'ev': 'write', 'text': new_text})


def control_approval(ws, sid, rel, approval):
    import approval as rules
    return rules.control_approval(ws, sid, rel, approval)


def approvals(ws):
    """The approve lines the gate hook wrote, newest last: the reference a commit's Approved-by line carries is the id."""
    rows = [e for e in load_events(ws)[0] if e.get('ev') == 'approve' and e.get('via') in ('typed', 'bridge')][-20:]
    return '\n'.join(f"{e.get('event_id')}  {e.get('ts')}  {shown(e.get('by'), 40)}  {shown(e.get('gate'), 40)}  {shown(e.get('key'), 60)}"
                     for e in rows) or 'no approvals recorded in this workspace'


def journal(ws, a):
    if storage_of(ws) != 'files':
        sys.exit('the journal is for storage: files, where no git keeps the history. On storage: git, edit the file and commit it')
    why = path_problem(ws, a.path)
    if why:
        sys.exit(why)
    rel = Path(a.path).as_posix()
    held = replay(load_events(ws)[0])[0]
    kept, disk = held.get(rel), Path(ws) / rel
    now = disk.read_text(encoding='utf-8') if disk.exists() else None
    if a.diff:
        diff = file_lines('\n'.join(difflib.unified_diff((kept or '').splitlines(), (now or '').splitlines(), 'journal', 'on disk', lineterm='')))
        return '\n'.join([f'(The lines of {rel} below are {DATA}.)', *diff] if diff else [f'no difference: {rel} on disk is what the journal holds'])
    want, have = str(config(ws).get('core_version') or ''), common.core_version()
    if want != have:
        sys.exit(f'refused, nothing was written: this workspace pins core_version {want or "nothing"} and the running core is {have}. '
                 'A person updates the plugin or follows the upgrade note; memory writes wait until they match')
    if a.restore:
        if rel not in held:
            sys.exit(f'the journal never held {rel}, so there is nothing to restore it to; the file is left as it is')
        if kept is None:
            disk.unlink(missing_ok=True)
        else:
            disk.parent.mkdir(parents=True, exist_ok=True)
            disk.write_text(kept, encoding='utf-8')
        return f'restored {rel} from the journal'
    extra = control_approval(ws, a.sid, rel, a.approval)
    if a.adopt:
        if kept == now:
            sys.exit(f'nothing to adopt: {rel} on disk is what the journal holds')
        if not (a.accepted_by or '').strip():
            sys.exit('--adopt needs --accepted-by "<name>": the person who was shown the difference (journal --diff) and said keep '
                     'it. Without a person who saw it, restore or leave the file and ask')
        journal_write(ws, a.sid, rel, now, {**extra, 'adopt': True, 'accepted_by': a.accepted_by.strip()}, prior_from_journal=True)
        return f'adopted {rel}'
    journal_write(ws, a.sid, rel, None if a.remove else Path(a.src).read_text(encoding='utf-8'), extra)
    return f'journaled {rel}'


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split('\n')[0], allow_abbrev=False)
    sub = p.add_subparsers(dest='cmd', required=True)
    e, o, c, r, j = (sub.add_parser(n, allow_abbrev=False) for n in ('emit', 'open', 'close', 'report', 'journal'))
    st = sub.add_parser('stats', allow_abbrev=False)
    st.add_argument('--since', type=day_type)
    w, me, ap = (sub.add_parser(n, allow_abbrev=False) for n in ('waiting', 'whoami', 'approvals'))
    for s in (e, o, c, r, j, w, me, ap, st):
        s.add_argument('--ws', required=True)
    for s in (e, j):
        s.add_argument('--sid', required=True)
    for s in (e, o):
        s.add_argument('--kind', required=True, choices=KINDS)
        s.add_argument('--subject')
        s.add_argument('--parent')
        s.add_argument('--source', choices=SOURCES)
    for s in (e, o, c):
        s.add_argument('--note')
    for s in (o, c):
        s.add_argument('--session', default=os.environ.get(SESSION_VAR) or None,
                       help='the assistant session id; the prompt hook files under the ledger named for it')
    for s in (e, c):
        s.add_argument('--cause', choices=CAUSES)
        s.add_argument('--ask', choices=ASKS)
        s.add_argument('--outcome')
        s.add_argument('--goal-met')
        s.add_argument('--fp', type=fp_type)
        s.add_argument('--prior', choices=PRIORS)
    e.add_argument('--ev', required=True, choices=(*EVS, *OWN_WRITER))
    e.add_argument('--subtag')
    e.add_argument('--by', choices=BYS)
    e.add_argument('--risk', choices=RISKS)
    e.add_argument('--refs', type=lambda s: [x.strip() for x in s.split(',') if x.strip()])
    e.add_argument('--min', type=int)
    e.add_argument('--usage', type=usage_type)
    e.add_argument('--worker')
    e.add_argument('--model')
    e.add_argument('--effort', choices=EFFORTS)
    e.add_argument('--what', choices=WHATS)
    e.add_argument('--severity', choices=SEVERITIES)
    c.add_argument('--park', action='store_true', help='the session waits on a person: a block is written and no end')
    r.add_argument('--since', type=day_type)
    r.add_argument('--until', type=day_type)
    j.add_argument('--path', required=True)
    j.add_argument('--approval', help='the approved proposal a write to a control file applies')
    g = j.add_mutually_exclusive_group(required=True)
    g.add_argument('--from', dest='src')
    g.add_argument('--remove', action='store_true')
    g.add_argument('--diff', action='store_true', help='what differs between the journal and the file on disk; changes nothing')
    g.add_argument('--adopt', action='store_true', help='keep the file on disk, after a person saw the difference and said so')
    g.add_argument('--restore', action='store_true', help="put the journal's text back, after a person saw the difference and said no")
    j.add_argument('--accepted-by')
    a = p.parse_args(argv)

    if a.cmd == 'emit':
        emit(a.ws, argparse.Namespace(**{**vars(emit_args()), **vars(a)}))
    elif a.cmd == 'open':
        if not a.subject:
            sys.exit('open needs --subject')
        print(open_session(a.ws, a))
    elif a.cmd == 'close':
        if a.park == bool(a.outcome):
            sys.exit('close takes --outcome <outcome>, or --park --cause <what it waits on>, never both')
        print(close_session(a.ws, a))
    elif a.cmd == 'stats':
        print('\n'.join(stats_lines(load_events(a.ws)[0], a.since or '') + report(a.ws, a.since)))
    elif a.cmd == 'report':
        print('\n'.join(report(a.ws, a.since, a.until)))
    elif a.cmd == 'waiting':
        for q in waiting(a.ws):
            print(f"waiting {q['days']} days, since {str(q['since'])[:10]}: {q['subject'] or q['sid']}, {q['cause']}"
                  f"{', ' + str(q['note']) if q['note'] else ''} ({DATA})")
    elif a.cmd == 'whoami':
        if not identity(a.ws):
            sys.exit(common.IDENTITY_HINT)
        print(identity(a.ws))
    elif a.cmd == 'approvals':
        print(approvals(a.ws))
    elif a.cmd == 'journal':
        print(journal(a.ws, a))


if __name__ == '__main__':
    outlast_reader()
    main()
