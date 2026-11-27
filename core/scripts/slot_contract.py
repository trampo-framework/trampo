#!/usr/bin/env python3
"""Check a workspace's slot adapters against the contract in protocols/slots.md.

  slot_contract.py <workspace> [--slot NAME]... [--write]

Without --write only the reading verbs are called. With --write it also creates one item, one question, one
notice and one review request, each titled "contract check": point it at a test project, never at the team's live
one. The product's mock adapter passes the same checks in the product's tests, so an adapter that passes here can
stand where the mock stood.

Exit: 0 every check passed, 1 at least one failed (one line each), 2 the call itself is wrong.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

SLOTS = ('tracker', 'ask', 'code-host', 'monitoring')
ITEM = ('id', 'state', 'assignee', 'title', 'needs')
REVIEW = ('review', 'branch', 'state', 'author', 'approvals', 'checks', 'open_findings', 'behind')
ASK_RECORD = {'ask': ('key', 'subject', 'options', 'at'), 'answer': ('key', 'id', 'by', 'text', 'at'), 'withdrawn': ('key', 'at')}


class Check:
    def __init__(self, ws, slot):
        self.ws, self.slot, self.problems = Path(ws), slot, []

    def call(self, *args, status=0, fields=None, one=False):
        """Run one verb; its rows as dicts. A wrong exit status, a line that is not a JSON object or a row without
        the contract's fields is a problem."""
        said = f"{self.slot} {' '.join(args)}"
        try:
            r = subprocess.run([str(self.ws / 'slots' / self.slot), *args], cwd=self.ws, capture_output=True, text=True, timeout=60,
                               stdin=subprocess.DEVNULL)
        except (OSError, subprocess.TimeoutExpired) as e:
            self.problems.append(f'{said}: could not be run ({e})')
            return []
        if r.returncode != status:
            self.problems.append(f'{said}: exit {r.returncode}, the contract says {status}: {r.stderr.strip()[:120]}')
            return []
        rows = []
        for line in r.stdout.splitlines() if status == 0 else []:
            try:
                row = json.loads(line)
            except ValueError:
                row = None
            if not isinstance(row, dict):
                self.problems.append(f'{said}: prints a line that is not one JSON object: {line[:80]!r}')
                return []
            rows.append(row)
        for row in rows:
            missing = [f for f in fields or () if f not in row]
            if missing:
                self.problems.append(f'{said}: a row lacks {", ".join(missing)}')
        if one and len(rows) != 1:
            self.problems.append(f'{said}: prints {len(rows)} rows, the contract says exactly one')
        return rows

    def draft(self, text):
        f = tempfile.NamedTemporaryFile('w', suffix='.md', delete=False, encoding='utf-8')
        f.write(text)
        f.close()
        return f.name

    def expect(self, ok, what):
        if not ok:
            self.problems.append(f'{self.slot}: {what}')


def tracker(c, write):
    c.call('list', fields=ITEM)
    c.call('search', 'contract', fields=ITEM)
    if not write:
        return
    made = c.call('create', c.draft('title: contract check\n\nMade by the contract check. Safe to close.\n'), fields=('id',), one=True)
    key = made[0]['id'] if made and 'id' in made[0] else None
    if not key:
        return
    c.call('read', key, fields=(*ITEM, 'body', 'comments'), one=True)
    claimed = c.call('claim', key, fields=ITEM, one=True)
    c.expect(claimed and claimed[0].get('assignee'), 'claim leaves the item with no assignee')
    c.call('comment', key, c.draft('a comment from the contract check\n'), one=True)
    read = c.call('read', key, one=True)
    c.expect(read and any('contract check' in str(x.get('text')) for x in read[0].get('comments') or []), 'a comment posted is not read back')
    states = {r.get('state') for r in c.call('list', fields=ITEM)}
    moved = c.call('move', key, 'done', fields=ITEM, one=True)
    c.expect(moved and moved[0].get('state') != (claimed or [{}])[0].get('state'), f'move does not change the state (states seen: {sorted(map(str, states))})')
    c.expect(any(r.get('id') == key for r in c.call('list', '--assignee', str((claimed or [{}])[0].get('assignee')))), 'list --assignee does not find the item claimed')


def ask(c, write):
    c.call('poll', fields=('id', 'key', 'by', 'text'))
    if not write:
        return
    made = c.call('ask', 'contract-check', c.draft('Is the contract check reaching you?\n\na) yes\nb) no\n'), fields=('key',), one=True)
    key = made[0].get('key') if made else None
    c.call('notify', c.draft('A notice from the contract check. No answer is needed.\n'), one=True)
    if key:
        c.call('withdraw', key)
    events = []
    for f in sorted((c.ws / '.trampo/state/ask').glob('*.jsonl')):
        events += [json.loads(l) for l in f.read_text(encoding='utf-8').splitlines() if l.strip()]
    for ev, fields in ASK_RECORD.items():
        mine = [e for e in events if e.get('ev') == ev and (ev == 'answer' or e.get('key') == key)]
        c.expect(ev == 'answer' or mine, f'no "{ev}" line for the ask in .trampo/state/ask/: the gate hook reads its answers there')
        for e in mine:
            c.expect(all(f in e for f in fields), f'a "{ev}" record lacks one of {", ".join(fields)}')
    asked = [e for e in events if e.get('ev') == 'ask' and e.get('key') == key]
    c.expect(not asked or asked[0].get('options') == [['a', 'yes'], ['b', 'no']], 'the ask record does not carry the options as [letter, text] pairs')


def code_host(c, write):
    c.call('list', fields=REVIEW)
    if not write:
        return
    made = c.call('open-review', 'contract-check', c.draft('contract check\n\nOpened by the contract check. Safe to close.\n'), fields=('review',), one=True)
    ref = made[0].get('review') if made else None
    if not ref:
        return
    c.call('status', ref, fields=REVIEW, one=True)
    c.call('describe', ref, c.draft('contract check, described\n\nSecond text.\n'))
    c.call('comment', ref, c.draft('severity: note\nA finding from the contract check.\n'), one=True)
    found = c.call('findings', ref, fields=('id', 'by', 'state', 'severity', 'text'))
    c.expect(found, 'a finding posted is not read back')
    c.expect(any(r.get('review') == ref for r in c.call('list', fields=REVIEW)), 'list does not show the review request just opened')


def monitoring(c, write):
    for alarm in c.call('alarms', fields=('id', 'system', 'state', 'fired', 'title'))[:1]:
        c.call('alarm', str(alarm.get('id')), fields=('id', 'system', 'state', 'fired'), one=True)
    c.call('checks', 'contract-check', fields=('system', 'check', 'state', 'at'))
    c.call('query', c.draft('system: contract-check\nsince: 2000-01-01T00:00:00Z\n'), fields=('system', 'at', 'text'))
    c.call('query', c.draft('contains: everything\n'), status=1)


CHECKS = {'tracker': tracker, 'ask': ask, 'code-host': code_host, 'monitoring': monitoring}


def check(ws, slots=SLOTS, write=False):
    """Every way the workspace's adapters fall short of the contract, one line each."""
    problems = []
    for slot in slots:
        c = Check(ws, slot)
        if not (Path(ws) / 'slots' / slot).is_file():
            problems.append(f'{slot}: slots/{slot} is not there')
            continue
        c.call('no-such-verb', status=3)
        CHECKS[slot](c, write)
        problems += c.problems
    return problems


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    write = '--write' in argv
    slots = [argv[i + 1] for i, a in enumerate(argv[:-1]) if a == '--slot']
    rest = [a for i, a in enumerate(argv) if a != '--write' and a != '--slot' and (i == 0 or argv[i - 1] != '--slot')]
    if len(rest) != 1 or any(s not in SLOTS for s in slots):
        print(__doc__, file=sys.stderr)
        return 2
    problems = check(rest[0], slots or SLOTS, write)
    print('\n'.join(problems) if problems else f"the {', '.join(slots or SLOTS)} adapters meet the contract" + ('' if write else ' (reading verbs only; --write checks the rest)'))
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
