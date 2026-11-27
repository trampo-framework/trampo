#!/usr/bin/env python3
"""The hooks the plugin registers, one command each: hooks.py <name>, with the hook's JSON on stdin.

Each is a check against a confused assistant, not a wall: it reads typed text and the session's own records, and
docs/decisions.md lists the known ways around each one and the backstop a team keeps outside it. A hook that cannot
tell lets the call through; the boundary that refuses when unsure is git's pre-push hook (prepush.py).
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import approval
import common
import shellread
from untrusted import shown

FILE_TOOLS = {'Write': 'file_path', 'Edit': 'file_path', 'MultiEdit': 'file_path', 'NotebookEdit': 'notebook_path'}
SHELL_TOOL = re.compile(r'^(Bash|mcp__.*__ctx_(execute|execute_file|batch_execute))$')
DECLARES = re.compile(r'(?<!\w)TRAMPO_USER\s*=')
DECLARED_FILES = ['trampo/user', 'trampo/areas', 'trampo/bound']
GIT_CONFIG_FILES = [r'\.git/config', r'\.gitconfig', r'\.config/git/config']
ASK_FILE = re.compile(r'state/ask/([\w.-]+)')
AGENT_STATE = r'(?:state/agent-[\w.-]+|sessions/agents/[\w.-]+)'
LEDGER_FILE = r'''telemetry/events/[^\s;&|<>"']*\.jsonl'''
PROPOSAL = re.compile(r'proposals/([\w.-]+)\.md')
SETS_HOME = re.compile(r'(?<!\w)(?:home|claude_config_dir)\b[\]\s]*=(?!=)')
STUB_NAME = re.compile(r'pre-push|prepare-commit-msg', re.I)
STUB_TEXT = r'hooks/(?:pre-push|prepare-commit-msg)'
PATH_WORD = re.compile(r'''[^\s;&|<>"'=()]+''')
TRANSCRIPT_FILE = r'''/[^\s;&|<>"']*\.jsonl'''
# the words of a file name a person would call the file by: a code whole, a longer word by its start
DESCRIBES = re.compile(r'[A-Za-z]+-\d+|[A-Za-z]{5,}')
RELATIVE_JSONL = re.compile(r'''[^\s;&|<>"'=()]+\.jsonl''', re.I)


def shell_text(tool, given):
    """The text a shell-capable tool was handed, or None for any other tool."""
    if not SHELL_TOOL.match(tool):
        return None
    batch = [str(c.get('command', '')) for c in given.get('commands') or [] if isinstance(c, dict)]
    return '\n'.join([str(given.get('command') or ''), str(given.get('code') or ''), *batch]).strip()


def within(path, top):
    """The path relative to top, or None outside it. A folder is the one the disk says it is: where the disk ignores
    letter case, another spelling of top is top."""
    path, top = Path(os.path.realpath(path)), Path(os.path.realpath(top))
    for up in (path, *path.parents):
        if up == top or (up.name.casefold() == top.name.casefold() and up.exists() and top.exists() and os.path.samefile(up, top)):
            return path.relative_to(up)
    return None


def inside(path, top):
    return within(path, top) is not None


def transcript_of(data):
    try:
        return Path(data.get('transcript_path') or '').read_text(encoding='utf-8', errors='replace')
    except OSError:
        return ''


def subject_of(ws, sid):
    return next((e['subject'] for e in common.session_events(ws, sid) if e.get('subject')), '')


def record(ws, session, **fields):
    here = common.active(ws, session)
    if here:
        common.append(ws, here[0], {'ev': 'approve', **fields})


def ask(ws, data, gate, key, text, **fields):
    """None when an approver's latest word on `key` is a yes, else why not. The yes is recorded with the proof that ties it
    to the message or bridge reply read here: only this hook writes an approve line, and nothing else counts one."""
    also, since, action = fields.pop('also', ()), fields.pop('since', 0), fields.pop('action', ())
    why, by, via, ref, proof = approval.decide(ws, key, transcript_of(data), text, also=also, since=since, action=action)
    if not why:
        record(ws, data.get('session_id'), gate=gate, by=by, via=via, ref=ref, key=key, sitting=data.get('session_id'),
               **proof, **fields)
    return why


def declared_why(cmd, path):
    said = ('who is at the keyboard and which folders are working areas are declared by a person, by hand, in '
            f'{common.config_dir()}: the assistant never writes them. Ask the person to do it')
    if path and inside(path, common.config_dir()):
        return said
    if cmd and (DECLARES.search(shellread.live(cmd)) or shellread.shell_write(cmd, DECLARED_FILES)
                or shellread.shell_write(cmd, [str(common.config_dir() / n) for n in ('user', 'areas')])):
        return said
    if cmd and (shellread.sets_git_name(cmd) or shellread.shell_write(cmd, GIT_CONFIG_FILES, raw=True)):
        return ('who is at the keyboard is the git user name, declared by a person: the assistant never changes it, in the '
                'repository, the global config or the files behind them. Ask the person to do it')
    return None


def records_why(ws, cmd, path):
    asks = common.state_dir(ws) / 'ask'
    names = {f.name for f in approval.bridge_files(ws)} | set(ASK_FILE.findall(cmd or ''))
    if (path and inside(path, asks)) or (cmd and names and shellread.shell_write(cmd, sorted(names))):
        return ('the ask-a-person records are written only by the team\'s bridge adapter: an answer a session could write '
                'would be a yes it gave itself. Read them, never write them')
    state = common.state_dir(ws)
    if (path and ((inside(path, state) and Path(path).name.startswith('agent-')) or inside(path, Path(ws) / 'sessions' / 'agents'))) \
            or (cmd and shellread.shell_write(cmd, [AGENT_STATE], raw=True)):
        return ('an unattended agent\'s state is written only by its own tick and by agent.py: a worker that must wait '
                'says so with agent.py wait <agent> <item> <question key>')
    return None


def transcripts_why(cmd, path, cwd):
    """The runtime's transcripts are where a typed yes is read from. Only `.jsonl` files are refused: the runtime
    keeps other files of its own in the same folders, and sessions write those."""
    top = approval.transcripts_dir()
    said = 'the runtime writes its own transcripts, and a person\'s yes is read from them: a session never writes one'
    # case is ignored throughout: a file system that ignores it opens the same file under another spelling
    real = os.path.realpath(top).lower() + os.sep

    def within(p):
        return os.path.realpath(p).lower().startswith(real)
    if path and str(path).lower().endswith('.jsonl') and within(path):
        return said
    if not cmd:
        return None
    names = [re.escape(t) + TRANSCRIPT_FILE for t in {str(top), os.path.realpath(top)}] + [r'\.claude/projects' + TRANSCRIPT_FILE]
    names += [re.escape(t) for t in RELATIVE_JSONL.findall(cmd) if within(os.path.join(cwd, os.path.expanduser(t)))]
    return said if shellread.shell_write(cmd, [f'(?i:{n})' for n in names], raw=True) else None


def stub_why(ws, cmd, path, cwd):
    said = ('git\'s hook is installed by the session start step, or by a person: it names where the runtime\'s transcripts '
            'are read, so a session never writes it, and never runs its installer with a home or config folder of its own')
    flat = re.sub(r'''['"\\]''', '', shellread.spoken(cmd)).lower() if cmd else ''
    if SETS_HOME.search(flat) and 'prepush' in flat and 'install' in flat:
        return said
    # any repository's hook, named by its folder, in the text with its quotes removed and its case folded
    bare = re.sub(r'''['"\\]''', '', cmd or '').casefold()
    if (path and re.search(STUB_TEXT + '$', os.path.realpath(path).casefold())) or shellread.shell_write(bare, [STUB_TEXT], raw=True):
        return said
    try:
        import prepush
    except Exception:
        return None
    # git is asked about the stubs that pass on to the machine's hooks only when the text names a hook at all
    passing = prepush.passing(ws) if re.search('|'.join(prepush.HOOK_NAMES), f'{bare} {path or ""}') else []
    name = re.compile('|'.join([STUB_NAME.pattern] + passing), re.I)
    if not name.search(f'{bare} {path or ""}'):
        return None
    cmd = bare
    try:
        # case folded as the file system may fold it
        stubs = {os.path.realpath(folder / n).casefold() for folder in prepush.guarded(ws) for n in prepush.STUBS}
        stubs |= {os.path.realpath(prepush.hooks_dir(ws) / n).casefold() for n in passing}
    except Exception:
        return None

    def is_stub(p):
        return os.path.realpath(p).casefold() in stubs
    if path and is_stub(path):
        return said
    named = [re.escape(t) for t in PATH_WORD.findall(cmd or '') if name.search(t) and is_stub(os.path.join(cwd, os.path.expanduser(t)))]
    return said if named and shellread.shell_write(cmd, [f'(?i:{n})' for n in named], raw=True) else None


def ledger_why(ws, cmd, path):
    if (path and inside(path, Path(ws) / 'telemetry' / 'events')) or (cmd and shellread.shell_write(cmd, [LEDGER_FILE], raw=True)):
        return ('the session ledger is written only by event.py and by the hooks that read a person\'s yes: a line a session '
                'wrote itself, an approve line most of all, would be a yes it gave itself. Read it, never write it')
    return None


def control_patterns(ws):
    """(label, pattern) for each control path as a shell command may name it. A directory matches only as a whole path
    component, at the start of a word, after ./ or after the workspace's own path."""
    roots = '|'.join(f'(?<={re.escape(str(r))}/)' for r in {Path(ws), Path(os.path.realpath(ws))})
    out = []
    for rel in approval.CONTROL_FILES:
        out.append((approval.control_label(rel), rf'(?i:(?<![\w.-]){re.escape(rel if rel.startswith(".") else Path(rel).name)})'))
    for d in approval.CONTROL_DIRS:
        start = r'(?<![\w.-])' if d.startswith('.') else rf'(?:(?<=[\s"\'=<>(])|(?<=\./)|{roots})'
        out.append((d + '/', rf'(?i:{start}{re.escape(d)}/[^\s;&|<>"\']*)'))
    return out


# the machine's file system does not tell Skills from skills, so no pattern here does either
SKILL_PATH = re.compile(r'(?i)(?<![\w.-])\.claude/skills/[^\s;&|<>"\']*')


def written_controls(ws, cmd):
    """(labels, why): the label of every control path the command writes, or why it is refused outright."""
    labels = {l for l, pat in control_patterns(ws) if shellread.shell_write(cmd, [pat], raw=True)}
    for path in {m.group(0) for m in SKILL_PATH.finditer(cmd)}:
        if not shellread.shell_write(cmd, [rf'(?<![\w.-]){re.escape(path)}(?![^\s;&|<>"\'])'], raw=True):
            continue
        if '..' in path.split('/'):
            return labels, f'{shown(path, 80)} reaches a skill through "..": name the skill\'s own path'
        labels.add(approval.control_label(path))
    if len(labels) > 1:
        return labels, (f'this command changes more than one control file ({", ".join(sorted(labels))}). Each changes on its '
                        'own yes: one command for each')
    return labels, None


FOLDER_HINT = ' (with its slash, or the path of the file: the folder\'s word alone does not count)'


def control_why(ws, data, cmd, path):
    label, rel = None, None
    if path and inside(path, ws):
        rel = within(path, ws).as_posix()
        label = approval.control_label(rel)
    elif cmd:
        labels, why = written_controls(ws, cmd)
        if why:
            return why
        label = next(iter(labels), None)
    if not label:
        return None
    if approval.skill_problem(label):
        return approval.skill_problem(label)
    if common.storage_of(ws) == 'files':
        return (f'{label} is a control file: on a shared folder it changes only through `event.py journal --approval '
                'proposals/<file>.md`, after an approver said yes to that proposal by name')
    why = ask(ws, data, 'control file', label, cmd or '', subject=subject_of_active(ws, data), path=rel or label)
    return why and (f'{label} is a control file (it decides what the assistant may do). It changes on an approver\'s yes naming '
                    f'{label}{FOLDER_HINT if label.endswith("/") else ""}, and its commit carries "Approved-by: <approver> <reference>", checked at push.\n{why}')


def subject_of_active(ws, data):
    here = common.active(ws, data.get('session_id'))
    return subject_of(ws, here[0]) if here else None


def journal_proposals(cmd):
    """The --approval values of every `event.py journal` the command runs, read from its words, not from its text."""
    found = []
    for toks in shellread.words(shellread.live(cmd)):
        for i, t in enumerate(toks):
            if t.rsplit('/', 1)[-1] != 'event.py' or toks[i + 1:i + 2] != ['journal']:
                continue
            rest = toks[i + 2:]
            found += [rest[j + 1] for j, a in enumerate(rest[:-1]) if a == '--approval']
            found += [a.split('=', 1)[1] for a in rest if a.startswith('--approval=')]
    return found


def journal_why(ws, data, cmd):
    for value in journal_proposals(cmd):
        m = PROPOSAL.fullmatch(value)
        f = common.real(ws, value) if m else None
        if not f:
            return f'{shown(value, 80)} is not a proposal file in this workspace (proposals/<date>-<slug>.md)'
        why = ask(ws, data, 'control file', m.group(1), cmd, proposal=value, text_sha=approval.sha(f.read_text(encoding='utf-8')),
                  subject=subject_of_active(ws, data))
        if why:
            return why
    return None


def agent_names(ws):
    """An expression for the tracker names of the workspace's agents, quoted or not; one that matches nothing when
    there are none."""
    names = set()
    for f in sorted((Path(ws) / 'agents').glob('*.yaml')) if ws else []:
        try:
            cfg = common.parse_yaml(f.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        names |= {f.stem, str(cfg.get('assignee') or f.stem)} if isinstance(cfg, dict) else {f.stem}
    if not names:
        return '(?!)'
    # a word the shell has yet to work out could be any of them
    return ('(?:(?i:["\']?(?:' + '|'.join(r'\s+'.join(map(re.escape, n.split())) for n in sorted(names) if n.strip()) + r')(?![\w-]))'
            + r'|\S*[$`*?\[{~]\S*)')


def slot_call(toks):
    """A call of the slot runner as the runner itself reads it, or None: its workspace as one word and its timeout
    option, which it takes anywhere after the verb, left out. A gate pattern is tested against this too, so where the
    words sit in the typed line does not decide whether the gate sees them."""
    at = next((i for i, t in enumerate(toks) if t.rsplit('/', 1)[-1] == 'slot.py'), None)
    rest = list(toks[at + 1:]) if at is not None else []
    if '--timeout' in rest[3:]:
        cut = rest.index('--timeout', 3)
        del rest[cut:cut + 2]
    return 'slot.py WS ' + ' '.join(rest[1:]) if len(rest) >= 3 else None


def gate_patterns(cfg, ws=None):
    """The team's gates as (name, pattern). An entry with no pattern, or one that is no expression, gates nothing: read
    as written, an empty pattern matches every command there is, and the health check fails on it. `<agents>` in a
    pattern stands for the names of the workspace's agents, so a gate can be for them without listing them."""
    gates = cfg.get('gated_commands') if isinstance(cfg.get('gated_commands'), dict) else {}
    out = []
    for gate, pattern in gates.items():
        try:
            if isinstance(pattern, str) and pattern.strip():
                out.append((gate, re.compile(pattern.replace('<agents>', agent_names(ws)) if '<agents>' in pattern else pattern)))
        except re.error:
            pass
    return out


def skip_close_why(ws, data, cmd):
    """`event.py close --outcome done` of a card whose QA was recorded as skipped: why no approver's yes to closing it
    that way is on record yet, or None. The yes is recorded here like any other, and the close command reads it."""
    import event
    for _, toks in shellread.run(cmd):
        at = next((i for i, t in enumerate(toks) if t.rsplit('/', 1)[-1] == 'event.py' and toks[i + 1:i + 2] == ['close']), None)
        rest = toks[at + 2:] if at is not None else []
        if at is None or not ('--outcome=done' in rest or any(a == '--outcome' and b == 'done' for a, b in zip(rest, rest[1:]))):
            continue
        here = common.active(ws, data.get('session_id'))
        subject = subject_of(ws, here[0]) if here and here[1] == 'card' else ''
        if not subject or event.qa_verdict(ws, subject)[1] != 'SKIPPED' or event.skip_approved(ws, subject):
            continue
        why = ask(ws, data, event.SKIP_GATE, subject, cmd, subject=subject)
        if why:
            return (f'QA for {subject} was recorded as skipped, so closing it as done waits for an approver\'s yes naming '
                    f'{subject} (for example "Yes, close {subject} as done without QA"), or for a QA pass that ends '
                    f'"Verdict: PASS".\n{why}')
    return None


def adopt_why(ws, data, cmd):
    """`prepush.py adopt <workspace> <commit>`: why an approver's yes for that commit is not on record yet, or None once
    it is. The record is written here, from the approver's own typed message naming the commit, and never from a
    bridge reply: approving a control file's change after the fact is done by the approver at the keyboard."""
    for _, toks in shellread.run(cmd):
        at = next((i for i, t in enumerate(toks) if t.rsplit('/', 1)[-1] == 'prepush.py' and toks[i + 1:i + 2] == ['adopt']), None)
        if at is None:
            continue
        said = 'recording an approval for a commit already made'
        key = (toks[at + 3] if len(toks) > at + 3 else '').lower()
        ok, full = common.git(ws, 'rev-parse', '--verify', '--quiet', f'{key}^{{commit}}') if re.fullmatch(r'[0-9a-f]{7,64}', key) else (False, '')
        if not ok:
            return f'{said}: name the commit by at least 7 characters of its id, as `prepush.py adopt <workspace> <commit>`'
        import prepush
        full = full.strip()
        if not prepush.control_changes(ws, full):
            return f'{said}: commit {key} changes no control file, so it needs no approval'
        here = common.active(ws, data.get('session_id'))
        if not here:
            return f'{said}: no session is open here, so there is nothing to tie the yes to. Open a session first'
        if any(e.get('gate') == prepush.ADOPTED and e.get('commit') == full for e in common.session_events(ws, here[0])):
            continue
        why, by, via, _, proof = approval.decide(ws, key, transcript_of(data))
        if why or via != 'typed':
            return (f'{said} is an approval, so it needs the approver\'s own typed yes naming the commit, for example '
                    f'"Yes, I approve commit {key}". Show them what the commit changes first (git show {key}).\n'
                    + (why or 'A reply through the bridge does not count for this'))
        common.append(ws, here[0], {'ev': 'approve', 'gate': prepush.ADOPTED, 'by': by, 'via': via, 'key': key, 'commit': full,
                                    'sitting': data.get('session_id'), **proof})
    return None


def waiting_in(ws, data):
    """(file, {what the sitting was refused and still waits on: how many messages had been typed by then})."""
    store = common.state_dir(ws) / ('waiting.' + re.sub(r'[^\w-]', '', str(data.get('session_id'))) + '.json')
    try:
        waiting = json.loads(store.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        waiting = {}
    return store, ({k: v for k, v in waiting.items() if isinstance(v, int)} if isinstance(waiting, dict) else {})


def gated_why(ws, cfg, data, cmd):
    parts = shellread.run(cmd)
    for gate, pattern in gate_patterns(cfg, ws):
        args = next((toks for text, toks in parts if pattern.search(text) or pattern.search(slot_call(toks) or '')), None)
        if not args:
            continue
        here = common.active(ws, data.get('session_id'))
        if not here:
            return (f'"{gate}" is a gated action and no session is open here, so there is nothing to tie a yes to: open a '
                    'session first (event.py open --kind <kind> --subject <subject>)')
        sid, kind = here
        subject = subject_of(ws, sid)
        g = approval.granted(ws, gate, kind, sid, data.get('cwd') or str(ws), args, cfg)
        if g:
            common.append(ws, sid, {'ev': 'approve', 'gate': gate, 'by': 'grant', 'via': 'grant', 'subject': subject,
                                    'ref': shown(g['title'], 100)})
            continue
        if not approval.names(' '.join(args), subject):
            return (f'"{gate}" is a gated action and this command names no {subject}: a yes is for one subject, and the '
                    'command must name the subject it runs for')
        # the one gated action a sitting waits on may be agreed to in the action's own words, typed after it was asked for
        store, waiting = waiting_in(ws, data)
        mine, words = f'{gate}: {subject}', approval.action_words(gate)
        alone = set(waiting) <= {mine}
        why = ask(ws, data, gate, subject, cmd, subject=subject, action=words, also=words if alone else (),
                  since=waiting.get(mine, len(approval.typed(transcript_of(data)))))
        if why:
            waiting.setdefault(mine, len(approval.typed(transcript_of(data))))
        else:
            waiting.pop(mine, None)
        store.parent.mkdir(parents=True, exist_ok=True)
        store.write_text(json.dumps(waiting), encoding='utf-8')
        if why:
            how = (f'It is the one gated action waiting in this sitting, so a yes typed from here on may use its own words '
                   f'({", ".join(words)}) without naming {subject}' if len(waiting) == 1 and words else
                   f'{len(waiting)} gated actions are waiting in this sitting ({"; ".join(sorted(waiting))}), so the yes must '
                   f'name {subject}')
            return f'"{gate}" is a gated action.\n{why}.\n{how}'
    return None


WRAPPERS = ('env', 'nohup', 'timeout', 'command', 'exec', 'nice', 'time', 'setsid', 'caffeinate')


def spawn_why(cmd, ws, cwd):
    """Why a command that starts a background worker lacks a rail, or None. The command typed from a template drops
    rails the template had; this reads the command as typed, behind the few wrappers a start is commonly put in."""
    for toks in shellread.words(cmd):
        at = 0
        while at < len(toks) and (re.fullmatch(r'\w+=.*|-\w+|\d+[smhd]?', toks[at]) or toks[at].rsplit('/', 1)[-1] in WRAPPERS):
            at += 2 if toks[at] == '-u' else 1  # env -u NAME
        toks = toks[at:]
        if not toks or toks[0].rsplit('/', 1)[-1] != 'claude' or '--bg' not in toks and '--background' not in toks:
            continue
        lacks = [] if '--permission-mode' in toks else ['--permission-mode']
        at = toks.index('--disallowed-tools') if '--disallowed-tools' in toks else None
        if at is None or 'AskUserQuestion' not in ' '.join(toks[at + 1:at + 4]):
            lacks.append('--disallowed-tools AskUserQuestion (nobody is there to answer a worker)')
        named = [toks[i + 1] if t == '--settings' else t.split('=', 1)[1] for i, t in enumerate(toks)
                 if (t == '--settings' and i + 1 < len(toks)) or t.startswith('--settings=')]
        lacks += [w for w in [settings_why(named[0] if named else '', ws, cwd, cmd) if len(named) < 2
                              else 'one --settings flag and no more: a later one would be read over the one dispatch wrote'] if w]
        if lacks:
            return ('this starts a background worker without ' + '; '.join(lacks) + '. Start a worker with the command '
                    '`run.py dispatch` prints, unchanged')
    return None


def settings_why(value, ws, cwd, cmd=''):
    """Why the settings a background start names are not the ones dispatch wrote for a bound item, or None."""
    wrote = '--settings naming the one dispatch wrote under sessions/<run>/workers/, with a sandbox that is on'
    if not value or value.lstrip().startswith('{'):
        return wrote
    f = Path(os.path.realpath(os.path.join(cwd, value)))
    top = Path(os.path.realpath(ws))
    try:
        run_name, folder, name = f.relative_to(top / 'sessions').parts
        have = json.loads(f.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return wrote
    item = name.removesuffix('.settings.json')
    tree = next((b.get('worktree') for b in common.bindings() if Path(os.path.realpath(str(b.get('workspace')))) == top
                 and b.get('run') == run_name and b.get('item') == item), None)
    if folder != 'workers' or item == name or not tree:
        return wrote
    import run
    if have != run.settings(top, item, tree):
        return f'settings that are the ones dispatch wrote: {value} differs from what dispatch writes for {item}'
    # ponytail: a command-reading check; the file can still change between this read and the runtime's own
    if shellread.shell_write(cmd, [name]) or re.search(rf'(?<![\w-])(?:rm|touch|chmod|unlink)\b[^;&|\n]*{re.escape(name)}', cmd):
        return f'a command that leaves the settings alone: this one also writes the settings file {name}'
    return None


areas = common.areas


def temp_dirs():
    return [tempfile.gettempdir(), '/tmp']


def outside_why(ws, cfg, data, path):
    """Why a file change outside the workspace waits, or None. The hook remembers, per sitting, the changes it refused:
    the refused write is the item the person was last shown, so while it is the only one waiting their agreement may
    name it by the words of its file name."""
    if cfg.get('outside') != 'ask-first' or not path:
        return None
    trees = [b['worktree'] for b in common.bindings() if os.path.realpath(b['workspace']) == os.path.realpath(ws)]
    if any(inside(path, top) for top in (ws, *temp_dirs(), *areas(), *trees)):
        return None
    name, said = Path(path).name, len(approval.typed(transcript_of(data)))
    gate = next((g for g, pattern in gate_patterns(cfg) if pattern.search(str(path))), 'outside the workspace')
    store, waiting = waiting_in(ws, data)
    alone = list(waiting) == [name]
    words = DESCRIBES.findall(Path(path).stem)
    why = ask(ws, data, gate, name, '', also=words if alone else (), since=waiting.get(name, 0),
              subject=subject_of_active(ws, data), path=str(path))
    if why:
        waiting.setdefault(name, said)
    else:
        waiting.pop(name, None)
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(json.dumps(waiting), encoding='utf-8')
    if not why:
        return None
    others = [k for k in waiting if k != name]
    how = (f'{len(waiting)} writes wait for a yes in this sitting ({", ".join(sorted(waiting))}), so the yes must name the file'
           if others else 'It is the one write waiting in this sitting, so a yes typed from here on may name it as ' + ' or '.join(
               json.dumps(a) for a in [name, *words]))
    where = (f'"{gate}" is a gated action, and writing {path} is one' if gate != 'outside the workspace' else
             f'{path} is outside the workspace, the temp folder and the working areas a person declared, and this workspace asks '
             'first there')
    return f'{where}.\n{why}.\n{how}'


def gate_why(data):
    """Why this tool call must not run yet, or None."""
    tool, given = str(data.get('tool_name') or ''), data.get('tool_input') or {}
    cmd, path = shell_text(tool, given), given.get(FILE_TOOLS.get(tool, ''))
    if not cmd and not path:
        return None
    why = declared_why(cmd, path)
    if why:
        return why
    cwd = data.get('cwd') or os.getcwd()
    ws = common.find_workspace(cwd) or (path and common.find_workspace(Path(path).parent)) or common.bound_workspace(cwd)
    away = None
    try:
        away = None if ws else common.sitting_workspace(data.get('session_id'))
        ws = common.sitting_workspace(data.get('session_id'), ws) if ws else away
    except OSError:
        pass
    if not ws:
        return None
    filed(ws, data.get('session_id'))
    cfg = approval.approved_config(ws)
    mode = hook_mode(ws, 'gate')
    if mode == 'off':
        return None
    if away:
        # in a folder that is not the workspace's, only the team's gated actions are its business: the folder's own
        # files, hooks and pushes are not
        why = cmd and gated_why(ws, cfg, data, cmd)
        if why and mode == 'log':
            common.hook_log(ws, {'hook': 'gate', 'would_block': True, 'tool': tool, 'why': why[:200]})
            return None
        return why or None
    why = records_why(ws, cmd, path) or ledger_why(ws, cmd, path) or transcripts_why(cmd, path, cwd) or stub_why(ws, cmd, path, cwd) \
        or (cmd and spawn_why(cmd, ws, cwd))
    if not why and cmd and shellread.push_bypass(cmd):
        why = ('this push skips git\'s own hooks, where the team\'s boundary check runs, or sets a variable that moves the runtime\'s or git\'s own configuration. '
               'Push plainly; if the check refuses, fix what it names or hand it to an approver')
    why = why or control_why(ws, data, cmd, path) or (cmd and (journal_why(ws, data, cmd) or adopt_why(ws, data, cmd) or skip_close_why(ws, data, cmd) or gated_why(ws, cfg, data, cmd))) \
        or outside_why(ws, cfg, data, path)
    if why and mode == 'log':
        common.hook_log(ws, {'hook': 'gate', 'would_block': True, 'tool': tool, 'why': why[:200]})
        return None
    return why or None


WRITERS = ('Edit', 'Write', 'MultiEdit', 'NotebookEdit')
# hooks append these between turns, so a session cannot settle them before it stops
HOOK_APPENDED = re.compile(r'^telemetry/events/[^/]+\.jsonl$')
SYNC_SCRIPT = Path(__file__).resolve().parent / 'sync.py'


def own_paths(transcript, ws):
    """Workspace paths this session wrote with a file tool, read from its own transcript. Never another session's."""
    prefix, seen = str(ws).rstrip('/') + '/', []
    for line in transcript.split('\n'):
        if '"tool_use"' not in line:
            continue
        try:
            content = (json.loads(line).get('message') or {}).get('content')
        except (ValueError, AttributeError):
            continue
        for b in content if isinstance(content, list) else []:
            if not isinstance(b, dict) or b.get('type') != 'tool_use' or b.get('name') not in WRITERS:
                continue
            given = b.get('input') or {}
            path = given.get('file_path') or given.get('notebook_path')
            if isinstance(path, str) and path.startswith(prefix):
                rel = path[len(prefix):]
                if not HOOK_APPENDED.match(rel) and rel not in seen:
                    seen.append(rel)
    return seen


def changed(ws, *paths):
    """Paths that differ from HEAD or are untracked, among `paths` or in the whole workspace."""
    out = common.git(ws, 'status', '--porcelain=v1', '-z', '--untracked-files=all', '--', *paths)[1]
    # the first record of a file changed but not staged opens with a space, and the output arrives stripped
    recs = [rec if rec[2:3] == ' ' else ' ' + rec for rec in out.split('\0') if rec]
    return [rec[3:] for rec in recs if len(rec) > 3 and not rec.startswith('R')]


def filed(ws, session):
    """The ledgers this sitting has filed under. Kept while each is open: once a session is closed, nothing else says
    which sitting its ledger belonged to."""
    store = common.state_dir(ws) / ('filed.' + re.sub(r'[^\w-]', '', str(session)))
    try:
        sids = store.read_text(encoding='utf-8').split()
    except OSError:
        sids = []
    here = common.active(ws, session)
    if here and here[0] not in sids:
        sids.append(here[0])
        store.parent.mkdir(parents=True, exist_ok=True)
        store.write_text('\n'.join(sids), encoding='utf-8')
    return sids


def ledger_news(ws, rel):
    """Whether the ledger holds a line origin's copy lacks that is more than a prompt count. The count is appended at
    every prompt, so a ledger holding nothing else new waits for the next line that is."""
    ok, theirs = common.git(ws, 'show', f'origin/{common.branch_of(ws)}:{rel}')
    have = set(theirs.splitlines()) if ok else set()
    try:
        lines = (Path(ws) / rel).read_text(encoding='utf-8', errors='replace').splitlines()
    except OSError:
        return False
    return any(l.strip() and l.strip() not in have and '"ev": "touch"' not in l for l in lines)


def scripted(ws, transcript, session):
    """Workspace paths this sitting wrote without a file tool, each with how: the ledgers it filed under, and changed
    files one of its own shell commands wrote onto. A file a command only read is another session's."""
    out = {f'telemetry/events/{sid}.jsonl': "this session's ledger" for sid in filed(ws, session)
           if ledger_news(ws, f'telemetry/events/{sid}.jsonl')}
    cmds = []
    for line in transcript.split('\n'):
        if '"tool_use"' not in line:
            continue
        try:
            content = (json.loads(line).get('message') or {}).get('content')
        except (ValueError, AttributeError):
            continue
        cmds += [shell_text(str(b.get('name')), b.get('input') or {}) for b in content if isinstance(b, dict)
                 and b.get('type') == 'tool_use'] if isinstance(content, list) else []
    cmds = [c for c in cmds if c]
    if cmds:
        ok, ahead = common.git(ws, 'diff', '--name-only', '-z', f'origin/{common.branch_of(ws)}...HEAD')
        for rel in dict.fromkeys(changed(ws) + (ahead.split('\0') if ok else [])):
            if rel and rel not in out and not HOOK_APPENDED.match(rel) and any(shellread.shell_write(c, [rel]) for c in cmds):
                out[rel] = 'written by a shell command'
    return out


def unsettled(ws, paths):
    """(dirty, unpushed): own paths that differ from HEAD or are untracked, and own paths committed here but not on
    origin's branch. A copy that already matches origin's is safe however it got there."""
    origin = f'origin/{common.branch_of(ws)}'
    dirty = []
    for i in range(0, len(paths), 200):
        dirty += changed(ws, *paths[i:i + 200])
    ok, out = common.git(ws, 'diff', '--name-only', '-z', f'{origin}...HEAD', '--', *paths)
    unpushed = [p for p in out.split('\0') if p] if ok else []

    def pending(path):
        want, have = common.git(ws, 'rev-parse', f'{origin}:{path}'), common.git(ws, 'hash-object', '--', path)
        return (Path(ws) / path).exists() and not (want[0] and have[0] and want[1] == have[1])
    return [p for p in dirty if pending(p)], [p for p in unpushed if pending(p)]


def sync_gate(data):
    """Stop: a session does not end a turn with files it wrote itself left uncommitted or, for a person's session,
    committed but not on origin. A spawned worker is logged only: whoever spawned it commits and pushes for it."""
    if data.get('stop_hook_active'):
        return None
    ws = common.find_workspace(data.get('cwd') or os.getcwd())
    if not ws or common.storage_of(ws) != 'git':
        return None
    mode = hook_mode(ws, 'sync-gate')
    transcript = transcript_of(data) if mode != 'off' else ''
    how = scripted(ws, transcript, data.get('session_id')) if mode != 'off' else {}
    paths = own_paths(transcript, os.path.realpath(ws))
    paths += [p for p in how if p not in paths]
    if not paths:
        return None
    worker = data.get('permission_mode') == 'bypassPermissions'
    dirty, unpushed = unsettled(ws, paths)

    def listed(a):
        return '\n'.join(f'  {p} ({how[p]})' if p in how else f'  {p}' for p in a[:12]) + (f'\n  ... {len(a) - 12} more' if len(a) > 12 else '')
    parts = [f'Files this session wrote are not committed:\n{listed(dirty)}'] if dirty else []
    if unpushed and not worker:
        parts.append(f"Files this session committed are not on origin's {common.branch_of(ws)}:\n{listed(unpushed)}")
    blocked = bool(parts) and not worker and mode == 'block'
    common.hook_log(ws, {'hook': 'sync-gate', 'session': data.get('session_id'), 'mode': data.get('permission_mode'), 'own': len(paths),
                         'dirty': len(dirty), 'unpushed': len(unpushed), 'blocked': blocked, 'would_block': bool(parts)})
    if not blocked:
        return None
    return {'block': '\n\n'.join(parts) + f"""

Commit only your own paths (git add <paths>; git commit -m '<message>' -- <paths>), then run
python3 {SYNC_SCRIPT} {ws}
which sends them through a clean worktree and moves the branch to origin's. Never pull, stash or rebase in the shared
checkout. If a file is left out on purpose (a draft, a large file, something sensitive), say so in your reply and stop again."""}


def hook_mode(ws, name, default='block'):
    """block, log or off for one check, from `hooks:` in the team's copy of workspace.yaml."""
    cfg = approval.approved_config(ws)
    value = (cfg.get('hooks') or {}).get(name) if isinstance(cfg.get('hooks'), dict) else None
    return value if value in ('block', 'log', 'off') else default


def detach(argv, log):
    with log.open('ab') as fh:
        subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=fh, stderr=fh, start_new_session=True)


def start(data):
    """SessionStart, storage: git: say what the last sync set aside, keep git's own hooks installed, and bring the
    checkout level with origin in the background so the session never waits on a fetch."""
    ws = common.find_workspace(data.get('cwd') or os.getcwd())
    if not ws or common.storage_of(ws) != 'git':
        return None
    ok, common_dir = common.git(ws, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    if not ok or common.git(ws, 'rev-parse', '--path-format=absolute', '--git-dir')[1] != common_dir:
        return None
    said = []
    try:
        import prepush
        # the runtime's own word for where its transcripts are, not a variable a later command could set
        given = data.get('transcript_path')
        named = isinstance(given, str) and os.path.isabs(given) and given.endswith('.jsonl')
        kept = []
        prepush.install(ws, Path(given).parent.parent if named else None, kept=kept)
        if kept:
            said.append(f'Trampo: {prepush.kept_note(prepush.hooks_dir(ws), kept)}. Tell the person.')
    except Exception as e:
        said.append(f'Trampo: the git hooks could not be installed ({e}); pushes from here are not checked. Tell the person.')
    stranded = Path(common_dir) / 'trampo-sync-stranded.txt'
    rows = stranded.read_text(encoding='utf-8', errors='replace').splitlines() if stranded.is_file() else []
    if rows:
        ref = common.git(ws, 'for-each-ref', '--sort=-refname', '--count=1', '--format=%(refname)', 'refs/sync/stranded/')[1]
        said.append(f"Trampo sync: {len(rows)} local commit(s) conflicted with origin's branch on the last sync and were set "
                    f'aside, not lost; tell the person. Inspect: git log --oneline origin/{common.branch_of(ws)}..{ref} (list: {stranded})')
    # a spawned worker does not sync: whoever spawned it does
    if data.get('permission_mode') != 'bypassPermissions' and hook_mode(ws, 'session-sync') != 'off':
        detach([sys.executable, '-B', str(SYNC_SCRIPT), str(ws), '--session'], Path(common_dir) / 'trampo-session-sync.log')
    return {'say': '\n'.join(said)} if said else None


# How a transcript line says where its prompt came from. Anything else typed at the keyboard is a person's.
ORIGINS = {'human': 'human', 'peer': 'peer', 'task-notification': 'notification'}
PROMPT_CLASSES = ('human', 'loop', 'peer', 'notification')
TOUCH_WAIT = 10.0


def prompt_class(r):
    """human, loop, peer or notification for one transcript line of a prompt, or None when the line is no prompt
    (a tool result, a compaction summary, a slash command, an interrupt)."""
    content = (r.get('message') or {}).get('content')
    if isinstance(content, list):
        if any(isinstance(i, dict) and i.get('type') == 'tool_result' for i in content):
            return None
        text = ' '.join(i.get('text') or '' for i in content if isinstance(i, dict) and i.get('type') == 'text')
    elif isinstance(content, str):
        text = content
    else:
        return None
    if r.get('isCompactSummary'):
        return None
    kind = (r.get('origin') or {}).get('kind')
    if kind in ORIGINS:
        return ORIGINS[kind]
    if r.get('scheduledTaskId') or r.get('turnOrigin') == 'scheduled' or r.get('promptSource') == 'sdk':
        return 'loop'
    head = text.lstrip()
    if head.startswith('<task-notification>') or r.get('turnOrigin') in ('task_notification', 'system'):
        return 'notification'
    if r.get('isMeta') or not head or head[0] in '</' or head.startswith('[Request interrupted'):
        return None
    return 'human'


def prompt_origin(path, prompt_id, offset=0, wait=TOUCH_WAIT, poll=0.05):
    """The class of one prompt; 'none' when its lines carry no class; 'unseen' when no line of it appears in time. The
    prompt hook runs before the prompt's line is written, so this reads the bytes past `offset` until one classifies."""
    deadline, seen = time.monotonic() + wait, False
    while True:
        try:
            with open(path, 'rb') as fh:
                fh.seek(offset)
                tail = fh.read()
        except OSError:
            tail = b''
        for raw in tail.splitlines():
            try:
                r = json.loads(raw)
            except ValueError:
                continue
            if isinstance(r, dict) and r.get('type') == 'user' and r.get('promptId') == prompt_id:
                seen = True
                found = prompt_class(r)
                if found:
                    return found
        if time.monotonic() >= deadline:
            break
        time.sleep(poll)
    if not seen and offset:
        return prompt_origin(path, prompt_id, 0, 0, poll)
    return 'none' if seen else 'unseen'


def write_touch(ws, sid, kind, origin, ts):
    common.append(ws, sid, {'kind': kind, 'ev': 'touch', 'who': common.identity(ws) or None, 'cause': 'untagged',
                            'prompt_origin': origin}, ts=ts)


def resolve_touch(ws, sid, kind, transcript, prompt_id, offset, ts, wait=TOUCH_WAIT):
    origin = prompt_origin(transcript, prompt_id, int(offset), wait)
    if origin != 'none':
        write_touch(ws, sid, kind or None, origin if origin in PROMPT_CLASSES else None, ts)


NO_RECORD = ('Trampo: no record is open for this sitting. If the person gives you something to work from, or may come '
             'back to what is said here, open one before you answer (the session skill, kind adhoc), write in it what was '
             'asked, what was given and what you answered, and close or park it when you stop. A question only about how '
             'to use the assistant needs none.')


def touch(data):
    """UserPromptSubmit: every prompt that reaches a session with an open ledger is one touch, untagged until the close
    gives it a cause. Counted here because a count typed at the close is a count forgotten. It never blocks a prompt.
    What this event prints is added to what the assistant reads, so it prints one thing only: that a sitting has no
    record yet, until it has had one."""
    ws = common.find_workspace(data.get('cwd') or os.getcwd())
    here = ws and common.active(ws, data.get('session_id'))
    if not here:
        had = ws and (common.state_dir(ws) / ('filed.' + re.sub(r'[^\w-]', '', str(data.get('session_id'))))).exists()
        return {'say': NO_RECORD} if ws and not had else None
    sid, kind = here
    ts = datetime.now(timezone.utc).strftime(common.TS)
    transcript, prompt_id = data.get('transcript_path'), data.get('prompt_id')
    if not (isinstance(transcript, str) and transcript and isinstance(prompt_id, str) and prompt_id):
        write_touch(ws, sid, kind, None, ts)
        return None
    try:
        offset = os.stat(transcript).st_size
    except OSError:
        offset = 0
    # the prompt's own line is written only after this hook returns, so a child waits for it
    common.state_dir(ws).mkdir(parents=True, exist_ok=True)
    detach([sys.executable, '-B', str(Path(__file__).resolve()), 'touch-resolve', str(ws), sid, kind or '', transcript, prompt_id,
            str(offset), ts], common.state_dir(ws) / 'touch.log')
    return None


NEEDS_YOU = re.compile(r'^.{0,8}\*\*[^*\n]{0,4}Needs\s+you:?\*\*', re.I | re.M)
LIST_ITEM = r'\s*(?:[-*+]|\d+[.)])\s'
# A question put to the person. A false pass costs nothing and a false block costs a turn, so REASONED is generous.
ASK = re.compile(r'\b(should i|shall i|do you want|would you like|want me to|which (one|way|option)|do you prefer|is it ok to|can i)\b'
                 r'|\?\s*$', re.I)
REASONED = re.compile(r"\b(otherwise|if not|either|or else|yes\b.{0,60}\bno\b|no\b.{0,60}\byes\b|your call|owns? the risk|costs?|risk|"
                      r"because|so that|blocks?|waits?|ships?|means|i recommend|recommended|i'd|i would|nothing\b)", re.I)
NEEDS_YOU_FIX = """A "Needs you" item asks the person to decide. Before it stands, say what a yes and a no would each change.

If what you already know rules one answer out, it is not a decision: do the work, say in one line what you did and why,
and flag it for review. Decide what the evidence settles; hand over only what it cannot.

Keep the item for what is the person's alone: money, a message that leaves the team, timing of a release, scope, or a
preference the evidence cannot settle. Then write it so it carries its own consequence, for example: "Send the
letter today: yes reaches them before the deadline, no waits to Monday. Your call, I have no basis to pick."""


def needs_you_block(text):
    """The Needs-you block of a reply: its header line and the list under it, or None."""
    lines = (text or '').split('\n')
    at = next((i for i, l in enumerate(lines) if NEEDS_YOU.search(l)), None)
    if at is None:
        return None
    out = [lines[at]]
    for i in range(at + 1, len(lines)):
        l = lines[i]
        if re.match(r'#{1,4}\s', l) or re.match(r'\s*\*\*[^*\n]{2,60}\*\*\s*$', l):
            break
        if not l.strip() and len(out) > 1 and not re.match(LIST_ITEM, lines[i + 1] if i + 1 < len(lines) else ''):
            break
        out.append(l)
    return '\n'.join(out)


def needs_you_items(block):
    listed = re.findall(rf'^{LIST_ITEM}+.*(?:\n(?!{LIST_ITEM}).*)*', block, re.M)
    if listed:
        return [s.strip() for s in listed]
    inline = NEEDS_YOU.sub('', block).strip()
    return [inline] if inline else []


def bare_asks(text):
    """[(number, item)] of the Needs-you items that ask a question and state no consequence."""
    block = needs_you_block(text)
    return [(n, it) for n, it in enumerate(needs_you_items(block), 1) if ASK.search(it) and not REASONED.search(it)] if block else []


def last_text(data):
    """The reply the turn ended on: the event's own copy, which the transcript can trail by a turn, else the transcript's."""
    if str(data.get('last_assistant_message') or '').strip():
        return data['last_assistant_message']
    for line in reversed(transcript_of(data).split('\n')):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        content = (e.get('message') or {}).get('content') if isinstance(e, dict) and e.get('type') == 'assistant' else None
        if not isinstance(content, list) or any(isinstance(b, dict) and b.get('type') == 'tool_use' for b in content):
            continue
        text = ''.join(b.get('text', '') for b in content if isinstance(b, dict) and b.get('type') == 'text')
        if text.strip():
            return text
    return ''


def needs_you(data):
    """Stop: a "Needs you" item phrased as a bare question is sent back once. A rule read at the start does not reach the
    turn, hundreds later, where the item is written; this does. It reads shapes, not meaning."""
    ws = common.find_workspace(data.get('cwd') or os.getcwd())
    mode = hook_mode(ws, 'needs-you') if ws else 'off'
    text = last_text(data) if mode != 'off' else ''
    block = needs_you_block(text)
    if not block:
        return None
    bad, retry = bare_asks(text), bool(data.get('stop_hook_active'))
    blocked = bool(bad) and not retry and mode == 'block'
    common.hook_log(ws, {'hook': 'needs-you', 'session': data.get('session_id'), 'retry': retry, 'items': len(needs_you_items(block)),
                         'verdict': 'bare-ask' if bad else 'pass', 'blocked': blocked})
    if not blocked:
        return None
    which = '\n'.join(f"  {n}. {re.sub(r'^(?:[-*+]|[0-9]+[.)])[ ]+', '', ' '.join(it.split()))[:120]}" for n, it in bad)
    return {'block': f'These "Needs you" items ask a question and state no consequence:\n{which}\n\n{NEEDS_YOU_FIX}'}


GATES_FILE = 'memory/shared/approval-gates.md'


def section(text, heading):
    """A heading's section, up to the next heading of the first or second level."""
    out = []
    for line in text.splitlines():
        if out and re.match(r'#{1,2} ', line):
            break
        if out or line.rstrip() == heading:
            out.append(line)
    return '\n'.join(out).rstrip()


def gate_rules(text):
    """Each entry's heading and its How to apply paragraph: the file has no digest, so these two are the rule."""
    out, keep = [], False
    for line in text.splitlines():
        if line.startswith('## '):
            out += ['', '#' + line]
            keep = False
        elif not line.strip():
            keep = False
        elif out and line.startswith('**How to apply'):
            keep = True
        if keep:
            out.append(line)
    return '\n'.join(out).strip()


def index(data):
    """SessionStart, also after a clear and a compaction: say where memory routes and what the gates are. Sessions
    skip the files that hold them, so they are said; both are cut from the live files, so no second copy can drift."""
    ws = common.find_workspace(data.get('cwd') or os.getcwd())
    if not ws:
        return None

    def read(rel):
        f = common.real(ws, rel)
        return f.read_text(encoding='utf-8', errors='replace') if f else None
    said = ['# Memory index (said by the session start hook)', '']
    routes = read('memory.md')
    found = section(routes, '## Categories') if routes is not None else ''
    said.append(found or ('memory.md not found' if routes is None else 'heading "## Categories" not found in memory.md'))
    gates = read(GATES_FILE)
    rules = gate_rules(gates) if gates is not None else ''
    said += ['', f"## Approval-gate rules (each entry's heading and How to apply paragraph from {GATES_FILE}; read the whole file "
                 'before a gated action)' if rules else (f'{GATES_FILE} not found' if gates is None else f'no "## " entries in {GATES_FILE}')]
    said += [rules] if rules else []
    here = common.active(ws, data.get('session_id'))
    if here and here[1] == 'run':
        import run
        said += ['', '## The rails of a run (said again because a compaction drops them)', run.RAILS]
    notes = sorted((Path(ws) / 'memory').rglob('*.md'))
    known = (routes or '') + ''.join(f.read_text(encoding='utf-8', errors='ignore') for f in notes if f.stem == f.parent.name)
    lost = [rel for rel in (f.relative_to(ws).as_posix() for f in notes if f.stem != f.parent.name)
            if '/archive/' not in rel and rel not in known]
    if lost:
        said += ['', '## Memory files in no index (no read trigger routes to them; add each a row in its category index): '
                 + ', '.join(lost)]
    return {'say': '\n'.join(said)}


HOOKS = {'gate': lambda data: (lambda why: {'refuse': why} if why else None)(gate_why(data)), 'start': start, 'sync-gate': sync_gate,
         'touch': touch, 'needs-you': needs_you, 'index': index}


def main(argv=None):
    """Exit status for the hook runner: 2 with the reason on stderr refuses a tool call; a Stop hook blocks by a
    decision on stdout; anything else lets the session carry on."""
    argv = sys.argv[1:] if argv is None else argv
    try:
        if argv[0] == 'touch-resolve':
            return resolve_touch(*argv[1:8])
        found = HOOKS[argv[0]](json.loads(sys.stdin.read())) or {}
    except Exception:  # a hook that cannot tell must not stop the work; the boundary check is the one that fails closed
        return None
    if found.get('say'):
        print(found['say'])
    if found.get('block'):
        print(json.dumps({'decision': 'block', 'reason': found['block']}))
    if found.get('refuse'):
        print(found['refuse'], file=sys.stderr)
        return 2
    return None


if __name__ == '__main__':
    sys.exit(main())
