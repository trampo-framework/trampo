#!/usr/bin/env python3
"""The evidence rules of a review, applied in code to a findings file before anything is posted.

  review_check.py FINDINGS.json --worktree DIR --diff DIFF [--comments COMMENTS.json] [--post-cap N]

Prints one line per finding, KEEP or DROP with the rule that dropped it, and exits 1 when any finding was dropped.
A finding is kept only when its path exists at the head commit, its line quotes the file exactly, it sits within
10 lines of a changed hunk (or names the other end of a cross-file defect), a claim of absence carries the search
that proved it, and it was not refuted earlier on code that has not changed since. A nit is never posted and at
most N findings are (default 12), highest severity first.
"""
import argparse
import json
import re
import sys
from pathlib import Path

SEVERITY = ('BLOCKER', 'MAJOR', 'MINOR', 'NIT')
NIT_CLASSES = ('naming', 'formatting', 'style', 'preference')
ABSENCE = re.compile(r'(?i)\b(does not exist|doesn\'t exist|never called|is not handled|not validated|is not validated|was removed|is missing|no caller)\b')
NEAR = 10
HUNK = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@')


def changed(diff):
    """{path: [(first, last)]} of the new-side line ranges each file's hunks cover."""
    out, path = {}, None
    for line in diff.splitlines():
        if line.startswith('+++ '):
            path = line[4:].removeprefix('b/') if line[4:] != '/dev/null' else None
        elif path and (m := HUNK.match(line)):
            start, n = int(m[1]), int(m[2] or 1)
            out.setdefault(path, []).append((start, start + max(n, 1) - 1))
    return out


def norm(text):
    return ' '.join(str(text).split())


def judge(f, tree, hunks, refuted):
    path, line = str(f.get('path', '')), f.get('line')
    if f.get('severity') not in SEVERITY:
        return 'severity is not one of ' + ', '.join(SEVERITY)
    if f.get('severity') != 'NIT' and f.get('category') in NIT_CLASSES:
        return 'a naming, formatting, style or preference finding is a nit, not ' + str(f.get('severity'))
    if f.get('severity') == 'NIT' and f.get('category') not in NIT_CLASSES:
        return 'a nit carries a nit class as its category'
    file = (tree / path).resolve()
    if not path or Path(path).is_absolute() or tree.resolve() not in file.parents or not file.is_file():
        return 'anchored at head: the path does not exist at the head commit'
    lines = file.read_text(encoding='utf-8', errors='replace').splitlines()
    end = int(f.get('end_line') or line or 0)
    if not isinstance(line, int) or line < 1 or end > len(lines) or end < line:
        return 'anchored at head: the line is not in the file at head'
    if norm(f.get('evidence_quote', '')) != norm('\n'.join(lines[line - 1:end])):
        return 'quoted: evidence_quote is not the text of the cited lines at head'
    if not any(a - NEAR <= line <= b + NEAR for a, b in hunks.get(path, [])):
        other = f.get('cross_file')
        if not (other and (tree / str(other.get('path', ''))).is_file()):
            return 'near the change: the cited line is more than 10 lines from every hunk'
    if ABSENCE.search(f"{f.get('title', '')} {f.get('body', '')}") and not f.get('grep_evidence'):
        return 'absence is proven by a search: a claim that something does not exist carries grep_evidence'
    if (path, line) in refuted:
        return 'a finding already refuted on this code is not raised again'
    return None


def refuted_spots(comments, tree):
    """(path, line) of earlier findings a reply refuted, kept only while the line still reads as it did."""
    spots = set()
    for c in comments:
        if c.get('refuted') and c.get('path') and isinstance(c.get('line'), int):
            file = tree / c['path']
            if file.is_file():
                lines = file.read_text(encoding='utf-8', errors='replace').splitlines()
                if c['line'] <= len(lines) and norm(lines[c['line'] - 1]) == norm(c.get('quote', '')):
                    spots.add((c['path'], c['line']))
    return spots


def check(findings, tree, diff, comments=(), cap=12):
    tree, hunks = Path(tree), changed(diff)
    refuted = refuted_spots(comments, tree)
    rows, kept = [], []
    for i, f in enumerate(findings.get('findings', []), 1):
        why = judge(f, tree, hunks, refuted)
        rows.append((i, f, why))
        if not why and f.get('severity') != 'NIT':
            kept.append((i, f))
    kept.sort(key=lambda t: (SEVERITY.index(t[1]['severity']), t[0]))
    post = {i for i, _ in kept[:cap]}
    return [(i, f, why or ('KEEP' if i in post else 'over the cap' if f.get('severity') != 'NIT' else 'a nit is recorded, never posted'))
            for i, f, why in rows], post


def main(argv=None):
    p = argparse.ArgumentParser(prog='review_check.py')
    p.add_argument('findings')
    p.add_argument('--worktree', required=True)
    p.add_argument('--diff', required=True)
    p.add_argument('--comments')
    p.add_argument('--post-cap', type=int, default=12)
    a = p.parse_args(argv)
    comments = json.loads(Path(a.comments).read_text(encoding='utf-8')) if a.comments else []
    rows, post = check(json.loads(Path(a.findings).read_text(encoding='utf-8')), a.worktree,
                       Path(a.diff).read_text(encoding='utf-8'), comments, a.post_cap)
    dropped = 0
    for i, f, why in rows:
        verdict = 'KEEP' if why == 'KEEP' else 'DROP'
        dropped += verdict == 'DROP' and f.get('severity') != 'NIT'
        print(f"{i}: {verdict} {f.get('path')}:{f.get('line')} {f.get('severity')}" + ('' if verdict == 'KEEP' else f' ({why})'))
    return 1 if dropped else 0


if __name__ == '__main__':
    sys.exit(main())
