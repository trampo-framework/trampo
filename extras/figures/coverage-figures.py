#!/usr/bin/env python3
"""Relative agent-coverage and quality figures from a workspace's git history (docs/wiki/Measured-results.md).

    coverage-figures.py <repo> --ref <ref> --runbooks <dir> [<dir> ...] --sessions <dir> [--registers <file> ...]
                        [--systems <system runbook dir>] [--self-test]

Every figure is read at two points of the ref's history: the last commit before the window starts and the last
commit before it ends, both in UTC.

- Runbooks: markdown files directly under the given runbook directories.
- Card records: `<sessions>/<card key>/session.md`, in the ISO week of the commit that added it. One cites a
  runbook when its text at the window end names a file under a runbook directory.
- Found on the way: the out-of-scope registers at the window end. An entry is a `- id:` line; each dated line under
  it is a sighting. A sighting dated in the window is a finding; it is a repeat unless it is its entry's first. A
  card record found something when its key is named at the head of a sighting dated in the window.
- Outcomes: each entry whose first sighting is in the window, as its status and decision lines read at the tip of the
  ref. Fixed: the status starts with fixed or fix merged and is not unmerged. Any recorded decision: carded, fixed,
  any status other than open, or a decision line other than none.
- System coverage: a card record's systems are the repos in its `Repo` header row. A repo has a system runbook when a
  file under the system runbook directory is named after it, or the directory's README index row names it as a
  backing repo. Read at the start and at each week end, over all the window's records; and per week, over that
  week's records only.
Prints only relative figures, never counts.
"""
import argparse
import collections
import datetime
import re
import subprocess

START, END = '2026-10-02', '2026-11-21'
YEAR, FIRST_WEEK, LAST_WEEK = 2026, 41, 47
BLOCK = 3
CARD_RECORD = re.compile(r'([A-Z][A-Z0-9]+-[0-9]+)/session\.md$')
CARD_KEY = re.compile(r'\b[A-Z][A-Z0-9]+-[0-9]+\b')
SIGHTING = re.compile(r'^\s+- (\d{4}-\d\d-\d\d)\b(.*)')
SIGHTING_HEAD = 50
STATUS = re.compile(r'(?:^|\s)status: (.*?)(?=\s{2,}[a-z][a-z ]*: |$)')
STATUS_LINE = re.compile(r'(?:\s+|- )status: (.*)')
FIXED = re.compile(r'(fixed|fix merged)\b(?!.*\b(unmerged|not merged)\b)')
REPO_ROW = re.compile(r'^\| *Repos? *\| *(.*?) *\|\s*$', re.M)
REPO_HEAD_END = re.compile(r'worktree|\(|\bPR\b|\bbase\b|\bbranch\b|:|\bread only\b')
REPO_SEP = re.compile(r'[,;+]|\band\b')
SLUG = re.compile(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$')
NOT_A_REPO = {'none', 'read'}
COVERAGE_TARGET = 0.9


def git(repo, *args):
    return subprocess.run(['git', '-C', repo, *args], capture_output=True, text=True, check=True).stdout


def rev_before(repo, ref, day):
    return git(repo, 'rev-list', '-1', f'--before={day}T00:00:00Z', ref).strip()


def week(day):
    return datetime.date.fromisoformat(day).isocalendar()[1]


def in_window(day):
    return START <= day < END


def runbook_count(repo, rev, dirs):
    names = git(repo, 'ls-tree', '--name-only', rev, '--', *[d.rstrip('/') + '/' for d in dirs]).split('\n')
    return collections.Counter(n.rsplit('/', 1)[0] for n in names if n.endswith('.md'))


def first_added(repo, rev, paths):
    """Date of the commit that first added each path."""
    first, day = {}, None
    for line in git(repo, 'log', '--reverse', '--no-renames', '--diff-filter=A', '--name-only', '--format=C %cI', rev,
                    '--', *paths).splitlines():
        if line.startswith('C '):
            day = line[2:12]
        elif line.strip():
            first.setdefault(line.strip(), day)
    return first


def pct(part, whole):
    return f'{100 * part / whole:.1f}%'


def entries(text):
    """Per register entry: its dated sighting lines as (day, text), its status and its decision line."""
    out, current = [], None
    for line in text.splitlines():
        if line.startswith('- id: '):
            current = [[], (m[1] if (m := STATUS.search(line[6:])) else None), None]
            out.append(current)
        elif line.startswith('#'):
            current = None
        elif current is None:
            continue
        elif m := SIGHTING.match(line):
            current[0].append((m[1], m[2]))
        elif current[1] is None and (m := STATUS_LINE.match(line)):
            current[1] = m[1]
        elif line.startswith('- decision:'):
            current[2] = line[len('- decision:'):].strip()
    return [tuple(e) for e in out]


def sightings(text):
    return [e[0] for e in entries(text)]


def outcome(status, decision):
    """(fixed, fixed or carded, any recorded decision) for one register entry."""
    status, decision = (status or '').strip().lower(), (decision or 'none').strip().lower()
    fixed = bool(FIXED.match(status))
    carded = fixed or status.startswith('carded')
    return fixed, carded, carded or (status != '' and not status.startswith('open')) or not decision.startswith('none')


def repos_named(record):
    """Repository names in a card record's `Repo` header row, owner prefixes dropped."""
    m = REPO_ROW.search(record)
    if not m:
        return set()
    head = REPO_HEAD_END.split(m[1])[0]
    names = {t.strip().strip('`').rsplit('/', 1)[-1] for t in REPO_SEP.split(head)}
    return {n for n in names if SLUG.match(n)} - NOT_A_REPO


def runbook_repos(paths, readme):
    """Names a system runbook resolves by: its file name, and the backing repos its row in the index names."""
    names = {p.rsplit('/', 1)[-1][:-3] for p in paths if p.endswith('.md')}
    for row in readme.splitlines():
        cells = row.split('|')
        if len(cells) > 4 and cells[1].strip().startswith('['):
            names |= {t.rsplit('/', 1)[-1] for t in re.findall(r'`([^`]+)`', cells[3])
                      if SLUG.match(t.rsplit('/', 1)[-1]) and t.count('/') <= 1}
    return names


def first_reaching(series, threshold):
    return next((label for label, share in series if share >= threshold), None)


def found_on_the_way(repo, end, registers, cards):
    entries = [e for r in registers for e in sightings(git(repo, 'show', f'{end}:{r}')) if e]
    found = [s for e in entries for s in e if in_window(s[0])]
    new = sum(1 for e in entries if in_window(min(day for day, _ in e)))
    named = {k for _, text in found for k in CARD_KEY.findall(text[:SIGHTING_HEAD])}
    print(f'Card records that recorded a finding outside their scope: {pct(len(cards & named), len(cards))}')
    print(f'Findings that were a sighting on an existing entry: {pct(len(found) - new, len(found))}')


def week_end(w):
    return min((datetime.date.fromisocalendar(YEAR, w, 1) + datetime.timedelta(days=7)).isoformat(), END)


def system_coverage(repo, ref, systems, records):
    """Share of the window's card records whose named repos all resolve to a system runbook, at each point."""
    systems = systems.rstrip('/')

    def covered(day):
        rev = rev_before(repo, ref, day)
        return runbook_repos(git(repo, 'ls-tree', '--name-only', rev, '--', systems + '/').split(),
                             git(repo, 'show', f'{rev}:{systems}/README.md'))

    named = [(w, r) for w, r in records if r]
    every = set().union(*(r for _, r in named))
    points = [(f'{START} (start)', START)] + [(f'end of week {w}', week_end(w)) for w in range(FIRST_WEEK, LAST_WEEK + 1)]
    sets = {label: covered(day) for label, day in points}
    series = [(label, sum(r <= sets[label] for _, r in named) / len(named)) for label, _ in points]
    print(f'Card records in the window whose systems all had a system runbook ({pct(len(named), len(records))} '
          f'of records name a repo):')
    for label, share in series:
        print(f'  {label}: {100 * share:.1f}%')
    first, last = points[0][0], points[-1][0]
    print(f'Systems the card records named that had a system runbook: {pct(len(every & sets[first]), len(every))} '
          f'at the start, {pct(len(every & sets[last]), len(every))} at the {last}')
    reached = first_reaching(series, COVERAGE_TARGET)
    print(f'First point at or above {COVERAGE_TARGET:.0%}: {reached}' if reached else
          f'{COVERAGE_TARGET:.0%} not reached; highest {100 * max(s for _, s in series):.1f}%')
    print('At the time of the work, each week\'s card records whose systems all had a runbook at that week\'s end:')
    for w in range(FIRST_WEEK, LAST_WEEK + 1):
        mine = [r for wk, r in named if wk == w]
        print(f'  week {w}: {pct(sum(r <= sets[f"end of week {w}"] for r in mine), len(mine))}')


def finding_outcomes(repo, ref, registers):
    """What the register entries first raised in the window carry now, read at the tip of the ref."""
    tip = git(repo, 'log', '-1', '--format=%cI', ref)[:10]
    raised = [(min(day for day, _ in e[0]), outcome(e[1], e[2]))
              for r in registers for e in entries(git(repo, 'show', f'{ref}:{r}')) if e[0]]

    def shares(lo, hi):
        o = [x for day, x in raised if lo <= day < hi]
        return ', '.join(f'{name} {pct(sum(x[i] for x in o), len(o))}'
                         for i, name in enumerate(('fixed', 'fixed or carded', 'any recorded decision')))

    print(f'Register entries first raised in the window, as recorded on {tip}: {shares(START, END)}')
    early = (datetime.date.fromisocalendar(YEAR, FIRST_WEEK, 1).isoformat(), week_end(FIRST_WEEK + BLOCK - 1))
    late = (datetime.date.fromisocalendar(YEAR, LAST_WEEK - BLOCK + 1, 1).isoformat(), END)
    print(f'  raised in weeks {FIRST_WEEK} to {FIRST_WEEK + BLOCK - 1}: {shares(*early)}')
    print(f'  raised in weeks {LAST_WEEK - BLOCK + 1} to {LAST_WEEK}: {shares(*late)}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('repo')
    ap.add_argument('--ref', default='HEAD')
    ap.add_argument('--runbooks', nargs='+', required=True)
    ap.add_argument('--sessions', required=True)
    ap.add_argument('--registers', nargs='*', default=[])
    ap.add_argument('--systems', help='the system runbook directory, with its README index')
    args = ap.parse_args()
    repo, start, end = args.repo, rev_before(args.repo, args.ref, START), rev_before(args.repo, args.ref, END)

    print(f'Runbooks the agents replay, {START} = 100:')
    before, after = runbook_count(repo, start, args.runbooks), runbook_count(repo, end, args.runbooks)
    total0, total1 = sum(before.values()), sum(after.values())
    for d in args.runbooks:
        d = d.rstrip('/')
        print(f'  {d}: {round(100 * after[d] / before[d])} ({after[d] / before[d]:.1f} times)')
    print(f'  all: {round(100 * total1 / total0)} ({total1 / total0:.1f} times)')
    for w in range(FIRST_WEEK, LAST_WEEK + 1):
        n = sum(runbook_count(repo, rev_before(repo, args.ref, week_end(w)), args.runbooks).values())
        print(f'    end of week {w}: {round(100 * n / total0)}')

    cite = re.compile('|'.join(re.escape(d.rstrip('/')) + r'/[a-z0-9][a-z0-9._-]*\.md' for d in args.runbooks))
    per_week = collections.defaultdict(lambda: [0, 0])
    cards, records = set(), []
    for path, day in first_added(repo, end, [args.sessions]).items():
        if (m := CARD_RECORD.search(path)) and in_window(day):
            text = git(repo, 'show', f'{end}:{path}')
            cards.add(m[1])
            records.append((week(day), repos_named(text)))
            per_week[week(day)][0] += 1
            per_week[week(day)][1] += bool(cite.search(text))

    def share(weeks):
        return pct(sum(per_week[w][1] for w in weeks), sum(per_week[w][0] for w in weeks))

    print(f'Card records citing a runbook, weeks {FIRST_WEEK} to {FIRST_WEEK + BLOCK - 1}: '
          f'{share(range(FIRST_WEEK, FIRST_WEEK + BLOCK))}, weeks {LAST_WEEK - BLOCK + 1} to {LAST_WEEK}: '
          f'{share(range(LAST_WEEK - BLOCK + 1, LAST_WEEK + 1))}')
    if args.registers:
        found_on_the_way(repo, end, args.registers, cards)
        finding_outcomes(repo, args.ref, args.registers)
    if args.systems:
        system_coverage(repo, args.ref, args.systems, records)


def self_test():
    record = '| Card | X-1 |\n| Repo | `org/alpha-api`, worktree `/w/alpha-api`, branch `b` |\n'
    assert repos_named(record) == {'alpha-api'}
    assert repos_named('| Repo | beta, gamma-web (PR 3) |\n') == {'beta', 'gamma-web'}
    assert repos_named('| Repos | none changed |\n') == set()
    assert repos_named('| Card | X-2 |\n') == set()
    readme = ('| Runbook | System | Backing repo(s) | Local | Role |\n'
              '| [one.md](one.md) | One | `org/delta-svc` + `epsilon` (`src/x/*`) | `~/r` | api |\n')
    assert runbook_repos(['d/one.md', 'd/README.md'], readme) == {'one', 'README', 'delta-svc', 'epsilon'}
    assert first_reaching([('w1', 0.5), ('w2', 0.91), ('w3', 0.95)], 0.9) == 'w2'
    assert first_reaching([('w1', 0.5)], 0.9) is None
    text = ('## Entries\n### a\n- id: KI-1   systems: x   status: fixed 2026-10-09, abc1234\n- decision: none\n'
            '- sightings:\n  - 2026-10-08 X-1 found\n'
            '### b\n- id: KI-2   systems: y `status: z`\n   status: open\n- decision: 2026-11-01, owner: minor, park\n'
            '- sightings:\n  - 2026-10-20 X-2 found\n  - 2026-11-02 X-3 again\n'
            '### c\n- id: KI-3   systems: z   status: carded X-9   risk: low\n- decision: none. Options: a\n'
            '### d\n- id: KI-4   systems: z   status: fixed on the b branch (PR 9, unmerged)\n- decision: none\n')
    got = entries(text)
    assert [[day for day, _ in e[0]] for e in got] == [['2026-10-08'], ['2026-10-20', '2026-11-02'], [], []]
    assert [outcome(e[1], e[2]) for e in got] == [(True, True, True), (False, False, True), (False, True, True),
                                                 (False, False, True)]
    assert outcome('open', 'none') == (False, False, False)
    assert outcome(None, None) == (False, False, False)
    assert sightings(text) == [e[0] for e in got]
    print('self-test: ok')


if __name__ == '__main__':
    import sys
    self_test() if '--self-test' in sys.argv else main()
