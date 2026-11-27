#!/usr/bin/env python3
"""Check a Trampo workspace's health.

  doctor.py WORKSPACE [--rebuild]

Exit 1 on any FAIL. On storage: files the journal in telemetry/events/ is what a missing or changed memory file
is checked against, and --rebuild puts back what is missing. Size and routing only warn: a team tunes the caps.
"""
import os
import re
import sys
from pathlib import Path

import common
from common import config, listed, load_events, path_problem
from untrusted import shown, suggest

SYNC_ROOT_MARKERS = ('/dropbox', '/onedrive', '/library/cloudstorage/', '/mobile documents/', '/google drive', '/icloud')
SECRET_PATTERNS = [
    ('a cloud access key', re.compile(r'\bAKIA[0-9A-Z]{16}\b')),
    ('a private key', re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----')),
    ('a code-host token', re.compile(r'\bgh[pousr]_[A-Za-z0-9]{36,}\b')),
    ('an api key', re.compile(r'\bsk-[A-Za-z0-9_-]{20,}\b')),
    ('a password assignment', re.compile(r'(?i)\b(password|passwd|secret|token)\s*[:=]\s*\S{6,}')),
]
# ponytail: regex guesses, not detection. English street words and common phone shapes only, and a
# person's name is never caught. Upgrade path: a per-team pattern list in workspace.yaml, or a PII library.
PERSONAL_PATTERNS = [
    ('an email address', re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+')),
    ('a phone number', re.compile(r'(?<![\w.+-])(?:\+\d[\d ()-]{7,}\d|\(?0\d[\d ()-]{6,}\d|\d{3}[ .-]\d{3}[ .-]\d{4})(?![\w-])')),
    ('a street address', re.compile(r'\b\d{1,5}[A-Za-z]? (?:[A-Z][a-z]+ ){1,3}'
                                    r'(?:Street|St|Road|Rd|Lane|Ln|Court|Ct|Avenue|Ave|Drive|Dr|Close|Place|Pl|Way)\b')),
]
# Dates and times are digits and dashes too, and every record is full of them
TIMESTAMP = re.compile(r'\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?)?')
TEXT_SUFFIXES = ('.md', '.yaml', '.yml', '.json', '.txt')
LIVE_STATE = re.compile(r'(?i)\b(enabled|disabled|deployed|turned (on|off)|switched (on|off)|is (on|off)|scheduled|runs every|current version)\b')
STAMP = re.compile(r'(?m)^As of \d{4}-\d{2}-\d{2} \([^)]+\); re-check: (.+)$')
SENSITIVE_SHOWN = 10
# Documents, archives, screenshots and recordings: where exports of real data and pictures of real screens end up
NOT_FOR_GIT = ('pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'key', 'numbers', 'pages', 'zip', 'tar', 'gz', 'tgz', '7z',
               'png', 'jpg', 'jpeg', 'gif', 'heic', 'webp', 'mov', 'mp4', 'har')


def words(path):
    return len(path.read_text(encoding='utf-8', errors='ignore').split())


OWN_FOLDERS = ('.git', '.trampo')


def walk(ws):
    """(real files, links) under the workspace. A link is listed and never followed, so no scan reads anything
    outside the workspace. `.git` and this copy's own state are not the team's text."""
    files, links = [], []
    for here, dirs, names in os.walk(ws):
        for name in list(dirs):
            if name in OWN_FOLDERS or (Path(here) / name).is_symlink():
                dirs.remove(name)
                if name not in OWN_FOLDERS:
                    links.append(Path(here) / name)
        for name in names:
            (links if (Path(here) / name).is_symlink() else files).append(Path(here) / name)
    return sorted(files), sorted(links)


def entries(text):
    """(heading, body) of each `## ` entry of a memory file."""
    parts = re.split(r'(?m)^## +(.+)$', text)
    return list(zip(parts[1::2], parts[2::2]))


def unstamped_claims(text):
    """Headings that claim live state with no `As of <date> (<source>); re-check: <command>` line under them. The claim
    is the heading: matching the body would flag every How to apply that mentions a deploy."""
    return [head for head, body in entries(text) if LIVE_STATE.search(head) and not STAMP.search(body)]


def check_sensitive(ws, files, patterns):
    hits = []
    for f in files:
        if f.suffix not in TEXT_SUFFIXES:
            continue
        for n, line in enumerate(f.read_text(encoding='utf-8', errors='ignore').splitlines(), 1):
            plain = TIMESTAMP.sub(' ', line)
            for kind, pat in patterns:
                if pat.search(plain):
                    hits.append(f'{f.relative_to(ws).as_posix()}:{n} looks like {kind}. Nothing sensitive lives in the workspace: '
                                'take it out, or keep a reference to where the real thing is stored')
    return hits[:SENSITIVE_SHOWN] + ([f'... and {len(hits) - SENSITIVE_SHOWN} more lines that look sensitive'] if len(hits) > SENSITIVE_SHOWN else [])


def check_journal(ws, events, rebuild):
    import event
    fails = []
    state, conflicts = event.replay(events)
    fails += [f'concurrent edit, merge by hand from the journal: {shown(c)}' for c in conflicts]
    for p, text in state.items():
        why = path_problem(ws, p)
        if why:
            fails.append(f'journal: {shown(why)}')
            continue
        f = ws / p
        if rebuild and text is not None and not f.exists():
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(text, encoding='utf-8')
        if (f.read_text(encoding='utf-8') if f.exists() else None) != text:
            fails.append(f'{shown(p)} differs from its journal: a person may have edited it by hand, or a sync client kept another '
                         f"copy. Read the difference ({suggest('event.py journal --ws . --sid <sid> --path {p} --diff', p=p)}), show "
                         'it to a person in plain words and ask whether to keep it. Yes: --adopt --accepted-by "<who said yes>". '
                         'No: --restore. Never overwrite it unseen')
    return fails


def check_file_types(ws):
    """Files git would take that the workspace never keeps by default. Only what the ignore file lets through is named."""
    ok, out = common.git(ws, 'ls-files', '-z', '--cached', '--others', '--exclude-standard', '--', *(f'*.{x}' for x in NOT_FOR_GIT))
    return [f'{shown(p, 120)}: documents, archives, screenshots and recordings never go into git by default. Keep it in the '
            'team\'s evidence store and commit only a reference, add its type to .gitignore, or, when it is meant for the '
            'workspace, a person says so and adds it by name' for p in out.split('\0') if ok and p]


def check_incidents(ws):
    """An incident folder is a record only with its three files and its row in the index every triage is found by."""
    top = ws / 'incidents'
    index = (top / 'index.md').read_text(encoding='utf-8', errors='ignore') if (top / 'index.md').is_file() else ''
    fails = []
    for d in sorted(x for x in top.iterdir() if x.is_dir() and not x.is_symlink()) if top.is_dir() else []:
        fails += [f'incidents/{d.name}/{name} is missing: an incident folder holds README.md, analysis.md and actions.md'
                  for name in ('README.md', 'analysis.md', 'actions.md') if not (d / name).is_file()]
        if d.name not in index:
            fails.append(f'incidents/{d.name}/ has no row in incidents/index.md: every triage gets one, in the commit that creates the folder')
    return fails


# The totals line of `event.py stats`, as a review file quotes it. It names its own window, so it is counted again
STATS_LINE = re.compile(r'stats (?:all dates|since (\d{4}-\d{2}-\d{2})), as of (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z): '
                        r'[^\n`]*?counted by session')
REVIEW_SECTIONS = ('Repeated causes', 'Standing warnings')


def check_reviews(ws, events, files):
    """Every review file holds both required sections, and the newest quotes a totals line the ledger still gives."""
    fails = []
    reviews = sorted(f for f in files if f.parent == ws / 'retros' and f.suffix == '.md')
    for f in reviews:
        rel, text = f.relative_to(ws).as_posix(), f.read_text(encoding='utf-8', errors='ignore')
        for name in REVIEW_SECTIONS:
            if not re.search(rf'(?ims)^##\s+{re.escape(name)}\s*$\s*\S', text):
                fails.append(f'{rel} has no "{name}" section, or it is empty: '
                             + ('each repeat with its sessions and what would stop it, or that none was found and how many '
                                'sessions were compared' if name == REVIEW_SECTIONS[0] else
                                'each health check warning that outlived a review window, with the fix made or the person asked'))
        if f != reviews[-1]:
            continue
        quoted = STATS_LINE.search(text)
        true = common.stats_lines(events, quoted.group(1) or '', quoted.group(2))[0] if quoted else ''
        if not quoted:
            fails.append(f'{rel} quotes no totals line. Every number in a review comes from a command: run '
                         'event.py stats --ws . and copy its first line into the file, word for word')
        elif quoted.group(0) != true:
            fails.append(f'{rel}: the totals line it quotes does not match the ledger, which gives: {true}. '
                         "Work written before that time may have arrived from a colleague's copy since the review. "
                         'Run event.py stats --ws . again and copy its first line word for word; correct every number '
                         'in the file that was taken from the old one')
    return fails


NO_BACKSTOP = re.compile(r'(?i)(?:nothing|none|no|not yet|n/?a|tbd|todo|unknown|\?+)(?: yet| so far| for now)?[\s.!]*')


def extra_checks(ws, cfg, events, files):
    """(fails, warns) from the modules that own a file's rules."""
    import approval
    fails, warns = approval.grant_findings(ws, cfg)
    gated = cfg.get('gated_commands') if isinstance(cfg.get('gated_commands'), dict) else {}
    backstops = cfg.get('backstops') if isinstance(cfg.get('backstops'), dict) else {}
    for g, pattern in gated.items():
        try:
            blank = not isinstance(pattern, str) or not pattern.strip() or not re.compile(pattern)
        except re.error:
            blank = True
        if blank:
            fails.append(f'gated_commands: "{shown(g, 80)}" has no pattern the hook can read, so it gates nothing: a person writes '
                         'the pattern over the words of the command that performs the action, or removes the line')
            continue
        for slot in ('tracker', 'ask', 'code-host', 'monitoring'):
            f = Path(ws) / 'slots' / slot
            if 'slot' in pattern and slot in pattern and (not f.is_file() or 'is not filled in' in f.read_text(encoding='utf-8', errors='ignore')):
                warns.append(f'the gated action "{shown(g, 80)}" is written over the {slot} slot, and the {slot} slot is not filled in: '
                             'nothing performs the action through it, so the pattern gates nothing. Fill the slot, or write the '
                             'pattern over the command or the file path the action really uses')
    warns += [f'the gated action "{shown(g, 80)}" names no backstop: its hook is a check against a confused assistant, and a '
              'reworded command gets past it. An approver says what stops the action outside the hook (a credential the '
              'assistant does not hold, a rule on the other system) and adds it under backstops: in workspace.yaml'
              for g in gated if not str(backstops.get(g) or '').strip()]
    warns += [f'the backstop of the gated action "{shown(g, 80)}" is recorded as "{shown(str(backstops[g]).strip(), 40)}": that is an '
              'honest answer and not a backstop. Until an approver names what stops the action outside the hook, a reworded '
              'command is stopped by nothing'
              for g in gated if NO_BACKSTOP.fullmatch(str(backstops.get(g) or '').strip())]
    return fails + approval.unapproved_control_writes(ws, events), warns


def part_checks(ws):
    """(fails, warns, names) from each installed part that ships scripts/health.py: under modules/ beside the core in a
    clone, beside the core's version folder in the plugin cache. Only this product's parts at the core's version load."""
    import importlib.util
    import json
    core = Path(__file__).resolve().parent.parent
    found = core.parent.glob('modules/*/scripts/health.py') if (core.parent / 'modules').is_dir() else core.parent.parent.glob('*/*/scripts/health.py')
    fails, warns, names = [], [], []
    for f in sorted(found):
        try:
            meta = json.loads((f.parent.parent / '.claude-plugin' / 'plugin.json').read_text())
        except (OSError, ValueError):
            continue
        if not str(meta.get('name', '')).startswith('trampo-') or meta.get('version') != common.core_version():
            continue
        spec = importlib.util.spec_from_file_location('health_' + re.sub(r'\W', '_', meta['name']), f)
        part = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(part)
        f2, w2 = part.check(ws)
        fails, warns, names = fails + f2, warns + w2, names + [meta['name']]
    return fails, warns, names


def check(ws, rebuild=False):
    ws = Path(ws).resolve()
    fails, warns = [], []
    if not (ws / 'workspace.yaml').exists():
        return [f'no workspace.yaml in {ws}'], []
    cfg = config(ws)
    storage, caps = cfg.get('storage'), cfg.get('caps') if isinstance(cfg.get('caps'), dict) else {}
    if storage not in ('files', 'git'):
        fails.append(f'storage must be files or git, got {storage!r}')
    if storage == 'git' and any(m in str(ws).lower() + '/' for m in SYNC_ROOT_MARKERS):
        fails.append('storage: git inside a synced folder; sync clients corrupt .git, use storage: files')
    pinned = str(cfg.get('core_version', ''))
    if pinned != common.core_version():
        fails.append(f'core version mismatch: workspace pins {pinned!r}, installed {common.core_version()!r}; on storage: files '
                     'memory writes are refused until they match')
    for key in ('gates', 'approvers'):
        if cfg.get(key) is not None and not isinstance(cfg[key], list):
            fails.append(f'{key}: in workspace.yaml must be a list, one "- item" per line; a person fixes it')
    if (cfg.get('gates') or cfg.get('gated_commands')) and not listed(cfg, 'approvers'):
        fails.append('workspace.yaml has gates and no approvers:, so nobody can approve a gated action; a person adds '
                     '`approvers:` with one name per line')

    for f in sorted((ws / 'agents').glob('*.yaml')):
        who = {f.stem, str(common.parse_yaml(f.read_text(encoding='utf-8')).get('assignee', ''))}
        fails += [f'{a} is an approver and also an agent (agents/{f.name}): an agent never gives the yes that gates its own actions'
                  for a in listed(cfg, 'approvers') if any(common.same(a, w) for w in who if w)]

    files, links = walk(ws)
    fails += [f'{l.relative_to(ws).as_posix()} is a symbolic link. A link can point anywhere on the machine that opens it, so nothing '
              'behind it was read. A person replaces it with the real file or folder, or removes it' for l in links]
    events, bad = load_events(ws)
    fails += [f'unreadable ledger line {b}' for b in bad]
    if storage == 'files':
        fails += check_journal(ws, events, rebuild)
        files = walk(ws)[0] if rebuild else files

    index = ws / 'memory.md'
    if index not in files:
        fails.append('memory.md, the index of the category indexes, is missing')
    in_memory = [f for f in files if f.relative_to(ws).parts[0] == 'memory' and f.suffix == '.md']
    # a category index is memory/<category>/<category>.md, routed to from memory.md
    indexes = [index] * (index in files) + [f for f in in_memory if f.stem == f.parent.name]
    known = ''.join(i.read_text(encoding='utf-8', errors='ignore') for i in indexes)
    for f in indexes:
        if 'index_words' in caps and words(f) > caps['index_words']:
            warns.append(f"{f.relative_to(ws).as_posix()} has {words(f)} words, over the {caps['index_words']} the team set for an "
                         'index: move rows into a category index before compressing any prose')
    for f in in_memory:
        rel = f.relative_to(ws).as_posix()
        if f in indexes:
            continue
        if 'file_words' in caps and words(f) > caps['file_words'] and '/archive/' not in rel:
            warns.append(f"{rel} has {words(f)} words, over the {caps['file_words']} the team set: when three or more entries share "
                         'a subject the file is not named for, move them out unchanged; compress prose only with a person\'s yes')
        if rel not in known and '/archive/' not in rel:
            warns.append(f'{rel} is in no index, so no read trigger routes to it: add its row to its category index')
        fails += [f'{rel}: "{shown(head, 120)}" claims live state without an "As of <date> (<source>); re-check: <command>" line'
                  for head in unstamped_claims(f.read_text(encoding='utf-8', errors='ignore'))]

    secrets = check_sensitive(ws, files, SECRET_PATTERNS)
    (fails if storage == 'files' else warns).extend(secrets)
    warns += check_sensitive(ws, files, PERSONAL_PATTERNS)
    if storage == 'git':
        warns += check_file_types(ws)
        try:
            import prepush  # here, not at the top: prepush imports this file
            warns += prepush.strays(ws)
        except Exception:
            pass
    fails += check_incidents(ws)
    fails += check_reviews(ws, events, files)
    f2, w2 = extra_checks(ws, cfg, events, files)
    f3, w3, parts = part_checks(ws)
    if (ws / 'runbooks').is_dir() and 'trampo-runbooks' not in parts:
        w3.append('runbooks/ exists and the runbooks part is not installed beside this core at its version, so no runbook was '
                  'checked. Install or update it, or run its own scripts/health.py on this folder')
    return fails + f2 + f3, warns + w2 + w3


def main(argv):
    if not argv or argv[0].startswith('-'):
        print(__doc__)
        return 2
    fails, warns = check(argv[0], rebuild='--rebuild' in argv[1:])
    for w in warns:
        print(f'WARN  {w}')
    for f in fails:
        print(f'FAIL  {f}')
    print(f'{len(fails)} failures, {len(warns)} warnings')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
