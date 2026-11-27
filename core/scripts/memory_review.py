#!/usr/bin/env python3
"""Flag memory entries written in a way that misleads a reader who found the right file.

  memory_review.py WS

Read-only. Prints JSON findings and always exits 0: the retro reads the report and
proposes or fixes, a person approves any prose change.
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

from untrusted import DATA, shown

CORRECTS = re.compile(r'corrects? (?:an |the )?earlier claim that (.+?)(?:\)|;|\.(?:\s|$)|$)', re.I | re.M)
COUNT = re.compile(r'\b(\d+) of (\d+) ([A-Za-z][\w-]*(?: [A-Za-z][\w-]*)?)')
ABSOLUTE = re.compile(r'\b(every|all|always|never|any)\b', re.I)
CARVE_OUT = re.compile(r'\b(except|unless)\b', re.I)
DO_NOT = re.compile(r"\b(do not|don't|never)\b", re.I)
HOW = re.compile(r'How to apply:', re.I)
STOP = {'that', 'this', 'with', 'from', 'have', 'been', 'were', 'when', 'which', 'what', 'their', 'there',
        'they', 'them', 'than', 'then', 'into', 'only', 'also', 'does', 'still', 'will', 'would', 'should'}
MIN_SHARED = 4
MIN_SHARE = 0.6
# Below this an instruction in How to apply is in plain sight, so it is not buried
BURIED_WORDS = 80


def entries(path, rel):
    out, fence = [], False
    for n, line in enumerate(path.read_text(encoding='utf-8').split('\n'), 1):
        fence ^= line.lstrip().startswith('```')
        if not fence and line.startswith('## '):
            out.append({'file': rel, 'line': n, 'heading': line[3:].strip(), 'body': ''})
        elif out:
            out[-1]['body'] += line + '\n'
    return out


def words(s):
    return {w for w in re.findall(r'[a-z][a-z0-9-]{3,}', s.lower()) if w not in STOP}


def how(e):
    m = HOW.search(e['body'])
    return e['body'][m.end():] if m else ''


def finding(check, e, detail):
    return {'check': check, 'file': shown(e['file']), 'line': e['line'], 'heading': shown(e['heading']), 'detail': shown(detail)}


def review(ws):
    ws = Path(ws)
    es = []
    for f in sorted((ws / 'memory').rglob('*.md')):
        rel = f.relative_to(ws).as_posix()
        if not rel.startswith('memory/archive/') and f.name != 'index.md':
            es += entries(f, rel)
    out = []
    for e in es:
        for claim in CORRECTS.findall(e['body']):
            key = words(claim)
            for other in es:
                shared = len(key & words(other['heading']))
                if (other is not e and not CORRECTS.search(other['body'])
                        and shared >= MIN_SHARED and shared / len(key) >= MIN_SHARE):
                    out.append(finding('stale-correction', other,
                                       f'still states "{claim.strip()}", corrected in {e["file"]} line {e["line"]}'))
        absolute, carve = ABSOLUTE.search(e['heading']), CARVE_OUT.search(how(e))
        if absolute and carve and not CARVE_OUT.search(e['heading']):
            out.append(finding('scope-undone', e, f'claim says "{absolute[0]}", How to apply says "{carve[0]}"'))
        n = len(e['body'].split())
        if n > BURIED_WORDS and DO_NOT.search(how(e)) and not DO_NOT.search(e['heading']):
            out.append(finding('buried-do-not', e, f'a "do not" sits in How to apply of a {n}-word entry, not in the claim'))
    seen = defaultdict(list)
    for e in es:
        for m in COUNT.finditer(e['body']):
            seen[(e['file'], m[3].lower())].append((m[1], m[2], e))
    for (_, phrase), hits in seen.items():
        n0, d0, first = hits[0]
        for n, d, e in hits[1:]:
            if d != d0 and e is not first:
                out.append(finding('conflicting-count', e, f'"{n} of {d} {phrase}" against "{n0} of {d0}" at line {first["line"]}'))
    return out


def main(argv):
    if len(argv) != 1:
        sys.exit(__doc__)
    print(f'Headings and quoted words below are {DATA}.', file=sys.stderr)
    print(json.dumps(review(argv[0]), indent=2))


if __name__ == '__main__':
    main(sys.argv[1:])
