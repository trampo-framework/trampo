#!/usr/bin/env python3
"""Relative throughput figures from a telemetry ledger directory (docs/wiki/Measured-results.md).

    throughput-figures.py <telemetry-events-dir> --unattended <sid-prefix> [<sid-prefix> ...] [--self-test]

A done card session is a `card` session with an `end` event whose outcome is `done`, counted once, in the ISO week
of its first such end. It is unattended when its parent sid starts with one of the given prefixes (the sid prefixes
of the unattended agents' runs). Its human turns are what `human_turns` counts; the three-week blocks compare them
per done session, by group, and per week. Prints only relative figures, never counts.
"""
import argparse
import collections
import datetime
import json
import pathlib

YEAR, FIRST_WEEK, LAST_WEEK = 2026, 41, 47
BLOCK = 3


def load_events(events_dir):
    events = []
    for path in sorted(pathlib.Path(events_dir).glob('*.jsonl')):
        for line in path.read_text(encoding='utf-8').splitlines():
            try:
                events.append(json.loads(line))
            except ValueError:
                continue
    return events


def done_card_ends(events):
    kind, parent, ends = {}, {}, {}
    for e in events:
        sid = e.get('sid')
        if e.get('kind'):
            kind.setdefault(sid, e['kind'])
        if e.get('parent'):
            parent.setdefault(sid, e['parent'])
    for e in events:
        sid = e.get('sid')
        if e.get('ev') == 'end' and e.get('outcome') == 'done' and kind.get(sid) == 'card':
            if sid not in ends or e['ts'] < ends[sid]['ts']:
                ends[sid] = e
    return [(sid, e['ts'], e.get('parent') or parent.get(sid) or '') for sid, e in ends.items()]


def human_turns(events, sids):
    """Per session: prompts a person typed into it plus the asks it raised, or None when the ledger cannot tell.

    The prompt count is the latest `usage` event's `prompts_human` (read from the transcript); without one, the
    touches whose `prompt_origin` is `human`, if the session has any touch carrying an origin at all."""
    usage, human, origin, asks = {}, collections.Counter(), set(), collections.Counter()
    for e in events:
        sid = e.get('sid')
        if sid not in sids:
            continue
        if e.get('ev') == 'usage' and (sid not in usage or e['ts'] >= usage[sid][0]):
            usage[sid] = (e['ts'], (e.get('usage') or {}).get('prompts_human'))
        elif e.get('ev') == 'touch' and 'prompt_origin' in e:
            origin.add(sid)
            human[sid] += e['prompt_origin'] == 'human'
        elif e.get('ev') == 'block':
            asks[sid] += 1
    turns = {}
    for sid in sids:
        prompts = usage[sid][1] if sid in usage else None
        if prompts is None and sid in origin:
            prompts = human[sid]
        turns[sid] = None if prompts is None else prompts + asks[sid]
    return turns


def weighted_mean(parts):
    return sum(weight * value for weight, value in parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('events_dir')
    ap.add_argument('--unattended', nargs='+', required=True)
    args = ap.parse_args()

    events = load_events(args.events_dir)
    per_week = collections.defaultdict(lambda: [0, 0])
    done = {}
    for sid, ts, par in done_card_ends(events):
        year, week, _ = datetime.date.fromisoformat(ts[:10]).isocalendar()
        if year == YEAR and FIRST_WEEK <= week <= LAST_WEEK:
            per_week[week][0] += 1
            per_week[week][1] += par.startswith(tuple(args.unattended))
            done[sid] = (week, par.startswith(tuple(args.unattended)))

    base = per_week[FIRST_WEEK][0]
    print(f'Done card sessions per ISO week, week {FIRST_WEEK} = 100:')
    for week in range(FIRST_WEEK, LAST_WEEK + 1):
        print(f'  week {week}: {round(100 * per_week[week][0] / base)}')
    ratio = per_week[LAST_WEEK][0] / base
    print(f'Week {LAST_WEEK} against week {FIRST_WEEK}: {ratio:.2f} times, {round(100 * (ratio - 1))}% more')

    def share(weeks):
        done = sum(per_week[w][0] for w in weeks)
        return 100 * sum(per_week[w][1] for w in weeks) / done

    first = share(range(FIRST_WEEK, FIRST_WEEK + BLOCK))
    last = share(range(LAST_WEEK - BLOCK + 1, LAST_WEEK + 1))
    print(f'Unattended share of done card sessions, weeks {FIRST_WEEK} to {FIRST_WEEK + BLOCK - 1}: {first:.1f}%, '
          f'weeks {LAST_WEEK - BLOCK + 1} to {LAST_WEEK}: {last:.1f}%, change {last - first:+.1f} points')
    attention(done, human_turns(events, set(done)))


def attention(done, turns):
    blocks = {'first': range(FIRST_WEEK, FIRST_WEEK + BLOCK), 'last': range(LAST_WEEK - BLOCK + 1, LAST_WEEK + 1)}
    stats = {}
    for name, weeks in blocks.items():
        sids = [s for s, (w, _) in done.items() if w in weeks]
        known = [s for s in sids if turns[s] is not None]
        groups = {}
        for label, flag in (('unattended', True), ('attended', False)):
            mine = [s for s in known if done[s][1] == flag]
            share = sum(done[s][1] == flag for s in sids) / len(sids)
            groups[label] = (share, sum(turns[s] for s in mine) / len(mine), sum(turns[s] == 0 for s in mine) / len(mine))
        stats[name] = (len(known) / len(sids), groups, sum(turns[s] == 0 for s in known) / len(known), len(sids))
    f, l = stats['first'], stats['last']
    span = (f'weeks {FIRST_WEEK} to {FIRST_WEEK + BLOCK - 1} against weeks {LAST_WEEK - BLOCK + 1} to {LAST_WEEK}')
    print(f'Human turns per done card session (prompts a person typed into it plus asks it raised), {span}:')
    for label in ('unattended', 'attended'):
        a, b = f[1][label][1], l[1][label][1]
        print(f'  {label}: {a:.1f} to {b:.1f} ({100 * (b / a - 1):+.0f}%)')
    a, b = (weighted_mean([(g[0], g[1]) for g in x[1].values()]) for x in (f, l))
    print(f'  all, each group weighted by its share of done sessions: {a:.1f} to {b:.1f} ({100 * (b / a - 1):+.0f}%)')
    print(f'  done sessions whose turns the ledger can tell: {100 * f[0]:.0f}% and {100 * l[0]:.0f}%')
    print(f'Done card sessions with no human turn, {span}: all {100 * f[2]:.1f}% to {100 * l[2]:.1f}%, '
          f'unattended {100 * f[1]["unattended"][2]:.1f}% to {100 * l[1]["unattended"][2]:.1f}%, '
          f'attended {100 * f[1]["attended"][2]:.1f}% to {100 * l[1]["attended"][2]:.1f}%')
    print(f'Done card sessions per week, {span}: {l[3] / f[3]:.2f} times; human turns spent on them per week: '
          f'{l[3] * b / (f[3] * a):.2f} times')



def self_test():
    events = [
        {'sid': 'a', 'ev': 'usage', 'ts': '2026-10-06T01:00:00Z', 'usage': {'prompts_human': 4}},
        {'sid': 'a', 'ev': 'usage', 'ts': '2026-10-06T02:00:00Z', 'usage': {'prompts_human': 2}},
        {'sid': 'a', 'ev': 'touch', 'prompt_origin': 'human'},
        {'sid': 'a', 'ev': 'block', 'cause': 'tooling'},
        {'sid': 'b', 'ev': 'touch', 'prompt_origin': 'human'},
        {'sid': 'b', 'ev': 'touch', 'prompt_origin': 'peer'},
        {'sid': 'c', 'ev': 'touch', 'prompt_origin': 'notification'},
        {'sid': 'd', 'ev': 'touch', 'cause': 'untagged'},
        {'sid': 'e', 'ev': 'usage', 'ts': '2026-10-06T01:00:00Z', 'usage': {}},
    ]
    assert human_turns(events, {'a', 'b', 'c', 'd', 'e'}) == {'a': 3, 'b': 1, 'c': 0, 'd': None, 'e': None}
    assert weighted_mean([(0.75, 2.0), (0.25, 10.0)]) == 4.0
    print('self-test: ok')


if __name__ == '__main__':
    import sys
    self_test() if '--self-test' in sys.argv else main()
