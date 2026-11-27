#!/usr/bin/env python3
"""Build a new workspace's first control files from the interview's answers, on the approval of the person running setup.

  setup.py WORKSPACE show ANSWERS      print the summary of what the control files will say; writes nothing
  setup.py WORKSPACE build ANSWERS     after the person typed their approval of that summary: write the control files,
                                       record the founding approval, make the first commit and the first share
  setup.py WORKSPACE share [ADDRESS]   the first share alone, when build could not reach the team's copy
  setup.py WORKSPACE name              the only workspace name setup may suggest: the folder's own name

This works only while there is no workspace yet: the team's copy holds none (on git, the shared repository has no
branch or no workspace.yaml on it and no commit here ever held one; on a shared folder, no workspace.yaml with
approvers and no ledger) and the folder names no approver. After that every control file changes on an approver's
approval, as protocols/gates.md says, and this command refuses.

ANSWERS is a file in the workspace.yaml subset:
  team: <name>                 storage: git | files        branch: main        remote: <address of the shared repository>
  approvers: (list)            modes: (list)                repositories: (list)
  gated_commands: (name: pattern)                           backstops: (name: what stops it outside the assistant)
  outside: ask-first           slots: mock | stub           mock_home: <shared folder of the mock>
  rules: (list, the team's own rules, in their words)
  your_name: <the name of the person running setup, read only when the machine has no git user name>
  setup: lite                  one person, card mode with runbooks: only team, approvers (the person at the keyboard)
                               and repositories (folders on this machine) are read; the rest is set as LITE says below
The sitting is read from the runtime's own variable, or --session.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import approval
import common
import event
from untrusted import shown

CORE = Path(__file__).resolve().parent.parent
KEY = 'setup'
SLOTS = ('tracker', 'ask', 'code-host', 'monitoring')
AGREE = 'Yes, go ahead with the setup.'
# Lite: one person, the card mode and the runbooks part. Each default keeps every gate the full interview's recommended
# answers keep for a person with no second reviewer: a change outside the workspace asks first, and the folders of the
# named repositories go into this person's areas so their own code edits do not.
LITE_ASKS = ('setup', 'team', 'approvers', 'repositories', 'your_name')
LITE_PARTS = ('trampo-mode-card', 'trampo-runbooks')


class Refused(Exception):
    pass


def git(ws, *args, timeout=60):
    try:
        r = subprocess.run(['git', '-c', 'core.fsmonitor=false', '-C', str(ws), *args], capture_output=True, text=True, timeout=timeout,
                           stdin=subprocess.DEVNULL, env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'})
    except (OSError, subprocess.SubprocessError):
        return False, ''
    return r.returncode == 0, (r.stdout if r.returncode == 0 else r.stderr).strip()


def installed_parts():
    """{plugin name: folder} of this product's parts at the core's version: under modules/ beside the core in a clone,
    beside the core's version folder in the plugin cache."""
    found = CORE.parent.glob('modules/*/.claude-plugin/plugin.json') if (CORE.parent / 'modules').is_dir() else \
        CORE.parent.parent.glob('*/*/.claude-plugin/plugin.json')
    parts = {}
    for f in found:
        try:
            meta = json.loads(f.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if str(meta.get('name', '')).startswith('trampo-') and meta.get('version') == common.core_version():
            parts[meta['name']] = f.parent.parent
    return parts


def lite(a):
    extra = sorted(k for k in a if k not in LITE_ASKS)
    if extra:
        raise Refused(f"lite takes only the team, the approver and the code repositories, not {', '.join(extra)}: run the full "
                      'interview to choose those')
    missing = [p for p in LITE_PARTS if p not in installed_parts()]
    if missing:
        raise Refused('lite needs the card mode and the runbooks part, and this machine lacks ' + ', '.join(missing) + '. Install '
                      + ' and '.join(f'`claude plugin install {p}@trampo`' for p in missing) + ', start a new session and run setup again')
    away = [r for r in common.listed(a, 'repositories') if not (os.path.isabs(str(r)) and Path(str(r)).is_dir())]
    if away:
        raise Refused(f'{shown(str(away[0]), 120)} is not a folder on this machine: lite names each code repository by the full path '
                      'of the folder it is kept in here')
    a.update(storage='git', branch='main', modes=['card'], outside='ask-first', rules=[])
    return a


def answers_of(path):
    f = Path(path)
    if not f.is_file():
        raise Refused(f'{path} is not a file: the setup skill writes the interview\'s answers there first')
    a = common.parse_yaml(f.read_text(encoding='utf-8'))
    if a.get('setup') == 'lite':
        a = lite(a)
    a['storage'] = a.get('storage') or 'git'
    a['branch'] = str(a.get('branch') or 'main')
    for key in ('approvers', 'modes', 'repositories', 'rules'):
        a[key] = common.listed(a, key)
    for key in ('gated_commands', 'backstops'):
        a[key] = a[key] if isinstance(a.get(key), dict) else {}
    if a['storage'] not in ('git', 'files'):
        raise Refused(f"storage is git or files, not {shown(a['storage'], 30)!r}")
    if not a.get('team') or not a['approvers']:
        raise Refused('the answers name no team or no approver: a workspace needs at least one person who can approve')
    empty = [g for g, pattern in a['gated_commands'].items() if not str(pattern or '').strip()]
    if empty:
        raise Refused(f"the gated action {shown(empty[0], 60)!r} has no pattern over a command, so it would gate nothing")
    return a


def git_name(ws):
    # a folder not made yet has no repository of its own, and the one this process stands in is not it
    return git(ws, 'config', 'user.name')[1] if Path(ws).is_dir() else git(Path.cwd(), 'config', '--global', 'user.name')[1]


def who(ws, a):
    """Who is running setup. On git it is the machine's git user name; a machine with none takes the name the person
    gave in the interview, for this first setup only. The summary they agree to shows it."""
    if a['storage'] == 'git':
        return git_name(ws) or str(a.get('your_name') or '').strip()
    name = os.environ.get('TRAMPO_USER', '').strip()
    try:
        return name or next((l.strip() for l in (common.config_dir() / 'user').read_text(encoding='utf-8').splitlines() if l.strip()), '')
    except OSError:
        return name


def not_new(ws, a):
    """Why this is no longer a workspace being set up, or None. Read from the team's copy and from what git remembers,
    never only from a file in the folder that a session could empty."""
    ws = Path(ws)
    local = ws / 'workspace.yaml'
    if local.is_file() and common.listed(common.config(ws), 'approvers'):
        return 'this folder already holds a workspace that names its approvers'
    if a['storage'] == 'files':
        if any((ws / 'telemetry' / 'events').glob('*.jsonl')):
            return 'this folder already holds a workspace\'s session ledger'
        return None
    if (ws / '.git').exists():
        if git(ws, 'log', '--all', '--format=%h', '-1', '--', 'workspace.yaml')[1]:
            return 'a commit in this folder already holds a workspace'
        ok, origin = git(ws, 'remote', 'get-url', 'origin')
        if ok and a.get('remote') and origin.rstrip('/') != str(a['remote']).rstrip('/'):
            return f'this folder is already tied to another shared repository ({shown(origin, 120)})'
        a['remote'] = origin if ok else a.get('remote')
    if a.get('remote'):
        state = remote_state(ws, a)
        if state == 'workspace':
            return (f"the shared repository at {shown(a['remote'], 120)} already holds a workspace: each person clones it, and its "
                    'control files change on an approver\'s approval')
    return None


def remote_state(ws, a):
    """'workspace', 'branch', 'empty' or 'unreachable' for the team's copy at the answers' address."""
    probe = ws if Path(ws).is_dir() else Path.cwd()
    ok, refs = git(probe, 'ls-remote', str(a['remote']), f"refs/heads/{a['branch']}")
    if not ok:
        return 'unreachable'
    if not refs.strip():
        return 'empty'
    tmp = Path(common.state_dir(ws)) / 'setup-probe.git'
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.parent.mkdir(parents=True, exist_ok=True)
    try:
        if not git(tmp.parent, 'init', '-q', '--bare', str(tmp))[0] or not git(tmp, 'fetch', '-q', '--depth', '1', str(a['remote']), a['branch'])[0]:
            return 'unreachable'
        return 'workspace' if git(tmp, 'cat-file', '-e', 'FETCH_HEAD:workspace.yaml')[0] else 'branch'
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def summary(ws, a):
    me = who(ws, a)
    kept = (f"in git, shared at {a['remote']} (branch {a['branch']})" if a.get('remote') else
            'in git on this machine only, until the team has a shared repository') if a['storage'] == 'git' else 'in this shared folder'
    lines = [f"SETUP SUMMARY for {a['team']}", '',
             'This is what the workspace\'s control files will say. Nothing is written until you agree.', '',
             f'Where the work is kept: {kept}',
             f"Who may approve an action that waits for a person: {', '.join(a['approvers'])}",
             'Actions that wait for an approver:']
    lines += [f"  - {g}" + (f" (what stops it outside the assistant: {a['backstops'][g]})" if a['backstops'].get(g) else
                            ' (nothing stops it outside the assistant yet)') for g in a['gated_commands']] or ['  - none yet']
    lines += [f"A file change outside the workspace waits for an approver: {'yes' if a.get('outside') == 'ask-first' else 'no'}",
              f"Ways of working to start with: {', '.join(a['modes']) or 'none chosen'}",
              f"The team's code repositories: {', '.join(a['repositories']) or 'none listed'}",
              'Connections to the tracker, the chat, the code host and monitoring: '
              + ('the practice versions that ship with the product' if a.get('slots') == 'mock' else 'not connected yet'),
              *([f"Folders on this machine where the assistant edits without asking: {', '.join(a['repositories'])}"]
                if a.get('setup') == 'lite' else []),
              "The team's own rules:"]
    lines += [f'  - {r}' for r in a['rules']] or ['  - none yet']
    lines += ['', f"You are {me or 'not known to this machine by name'}. Only an approver named above can agree to this.", '',
              f'To agree, type a sentence that says yes to the setup, for example: "{AGREE}"',
              'To change something, say what to change, and you will be shown this summary again.']
    return '\n'.join(lines)


def shown_file(ws):
    return common.state_dir(ws) / 'setup-shown'


def show(ws, a, now=None):
    why = not_new(ws, a)
    if why:
        raise Refused(f'{why}. Setup builds a workspace only where there is none yet')
    text = summary(ws, a)
    f = shown_file(ws)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps({'sha': approval.sha(text), 'at': now or time.time()}), encoding='utf-8')
    return text


def agreed(ws, a, sitting):
    """(name, typed message) of the founding approval, or Refused with what the person still has to do."""
    text, me = summary(ws, a), who(ws, a)
    try:
        seen = json.loads(shown_file(ws).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        seen = {}
    if seen.get('sha') != approval.sha(text):
        raise Refused('the summary as it reads now has not been shown: run `show`, read the whole summary out to the person, and wait '
                      'for their answer. An answer given before the summary was shown, or to an earlier one, does not count')
    if not me:
        raise Refused('this machine does not say who is at the keyboard, so nobody can agree yet. On git, ask the person for their name, '
                      'write it in the answers as `your_name:`, and show the summary again; it is set for this workspace when it is '
                      'built. On a shared folder the person writes their name in their own `user` file')
    if not any(common.same(me, x) for x in a['approvers']):
        raise Refused(f"{shown(me, 60)} is running setup and is not one of the approvers in the answers ({', '.join(a['approvers'])}). "
                      'The first approval comes from an approver: add this person, or have an approver run setup')
    said = [t for texts in approval.sitting_transcripts(ws, sitting or '') for t in approval.typed(texts)
            if t['sitting'] == sitting and t['at'] > float(seen.get('at', 0))]
    read = [(t, approval.verdict(t['text'], KEY)) for t in sorted(said, key=lambda t: t['at'])]
    read = [(t, v) for t, v in read if v]
    if not read or read[-1][1] != 'yes':
        why = 'their latest answer about the setup is not an agreement' if read else 'they have not answered since it was shown'
        raise Refused(f'{shown(me, 60)} has not agreed to the summary: {why}. Show the summary and wait for a typed sentence that says '
                      f'yes to the setup, such as "{AGREE}"')
    return me, read[-1][0]


def write_control_files(ws, a):
    for src in sorted(p for p in (CORE / 'seeds').rglob('*') if p.is_file()):
        dst = ws / src.relative_to(CORE / 'seeds')
        if not dst.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    seed = (CORE / 'seeds' / 'workspace.yaml').read_text(encoding='utf-8')

    def block(key, value):
        if isinstance(value, dict):
            return f'{key}:\n' + ''.join(f'  {k}: {v}\n' for k, v in value.items())
        return f'{key}:\n' + ''.join(f'  - {v}\n' for v in value) if value else f'{key}: []\n'

    text = re.sub(r'(?m)^team:.*$', f"team: {a['team']}", seed)
    text = re.sub(r'(?m)^storage:.*$', f"storage: {a['storage']}", text)
    text = re.sub(r'(?m)^branch:.*$', f"branch: {a['branch']}", text)
    text = re.sub(r'(?m)^core_version:.*$', f'core_version: {common.core_version()}', text)
    for key in ('approvers', 'repositories', 'modes'):
        text = re.sub(rf'(?m)^{key}: \[\]\n', lambda m: block(key, a[key]), text)
    extra = ''.join(block(k, a[k]) for k in ('gated_commands', 'backstops') if a[k])
    extra += 'outside: ask-first\n' if a.get('outside') == 'ask-first' else ''
    (ws / 'workspace.yaml').write_text(text.rstrip('\n') + ('\n\n' + extra if extra else '\n'), encoding='utf-8')

    rules = ''.join(f'- {r}\n' for r in a['rules']) or 'No team rules yet.\n'
    const = (CORE / 'seeds' / 'constitution.md').read_text(encoding='utf-8').replace('<team name>', str(a['team']))
    (ws / 'constitution.md').write_text(const.replace('No team rules yet.\n', rules), encoding='utf-8')
    agents = ws / 'AGENTS.md'
    agents.write_text(agents.read_text(encoding='utf-8').replace('<team name>', str(a['team'])), encoding='utf-8')
    gates = (CORE / 'seeds' / 'memory' / 'shared' / 'approval-gates.md').read_text(encoding='utf-8').rstrip('\n') + '\n'
    for g in a['gated_commands']:
        stop = a['backstops'].get(g) or 'nothing yet; the health check warns until one is named'
        gates += (f'\n## {g} waits for an approver (setup)\n\nThe team chose this at setup. What stops it outside the assistant: {stop}.\n\n'
                  f'**How to apply:** draft it, show the exact command, and wait for an approver to agree to "{g}".\n')
    (ws / 'memory' / 'shared' / 'approval-gates.md').write_text(gates, encoding='utf-8')
    if a.get('setup') == 'lite':
        for part in LITE_PARTS:
            top = installed_parts()[part]
            for rel in common.listed(common.parse_yaml((top / 'module.md').read_text(encoding='utf-8').split('---')[1]), 'seeds'):
                dst = ws / Path(rel).relative_to('seeds')
                if not dst.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(top / rel, dst)
    if a.get('slots') == 'mock':
        for name in SLOTS:
            shutil.copy2(CORE / 'mocks' / 'slot', ws / 'slots' / name)
        (ws / 'slots' / 'mock-home').write_text(f"{a.get('mock_home') or '.trampo/mock'}\n", encoding='utf-8')


def add_areas(folders):
    """Lite only, after the person agreed to a summary that names these folders: they work alone, and their own code
    repositories are where they edit every day."""
    f = common.config_dir() / 'areas'
    have = f.read_text(encoding='utf-8').splitlines() if f.is_file() else []
    new = [str(x) for x in folders if str(x) not in (h.strip() for h in have)]
    if new:
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(''.join(f'{line}\n' for line in have + new), encoding='utf-8')


def share(ws, a):
    """The first share of a workspace on git. Returns what to tell the person."""
    branch = a['branch']
    ok, origin = git(ws, 'remote', 'get-url', 'origin')
    if not ok and a.get('remote'):
        ok = git(ws, 'remote', 'add', 'origin', str(a['remote']))[0]
        origin = str(a['remote'])
    if not ok:
        return False, ('The workspace is built and saved on this machine, and it is not shared with the team yet. What a person '
                       'arranges: an empty shared repository on the team\'s code host, and its address. Give the assistant the '
                       'address and it shares the workspace; nobody needs to type a command.')
    state = remote_state(ws, {'remote': origin, 'branch': branch})
    if state == 'workspace':
        ours = git(ws, 'rev-parse', 'HEAD')[1]
        if git(ws, 'ls-remote', origin, f'refs/heads/{branch}')[1].split('\t')[0] == ours:
            return True, f'The workspace is already shared at {origin}.'
        return False, (f'The shared repository at {origin} already holds another workspace, so this one was not shared over it. '
                       'A person decides which one the team uses.')
    done, said = git(ws, 'push', '-q', '-u', 'origin', branch, timeout=120)
    if done:
        return True, f'The workspace is shared at {origin}. Each other person gets their own copy from that address.'
    return False, (f'The workspace is built and saved on this machine, and the first share to {origin} did not go through. What a '
                   'person arranges: that the address is right, that the repository exists and is empty, and that this machine is '
                   f'allowed to write to it. Then ask the assistant to share again. What the code host said: {shown(said, 300)}')


def build(ws, a, sitting):
    ws = Path(ws)
    why = not_new(ws, a)
    if why:
        raise Refused(f'{why}. Setup builds a workspace only where there is none yet; from here a control file changes on an '
                      'approver\'s approval, as for any other change')
    me, said = agreed(ws, a, sitting)
    text_sha = approval.sha(summary(ws, a))
    ws.mkdir(parents=True, exist_ok=True)
    if a['storage'] == 'git' and not (ws / '.git').exists():
        git(ws, 'init', '-q', '-b', a['branch'])
        if a.get('remote') and remote_state(ws, a) == 'branch':
            # the shared repository was made with a first file in it: build on that commit, keeping its files
            git(ws, 'fetch', '-q', str(a['remote']), a['branch'])
            git(ws, 'reset', '-q', 'FETCH_HEAD')
            git(ws, 'checkout-index', '-a')
    if a['storage'] == 'git' and not git_name(ws):
        git(ws, 'config', '--local', 'user.name', me)
    write_control_files(ws, a)
    if a.get('setup') == 'lite':
        add_areas(a['repositories'])
    if not common.active(ws, sitting):
        event.main(['open', '--ws', str(ws), '--kind', 'adhoc', '--subject', KEY, *(['--session', sitting] if sitting else [])])
    sid = common.active(ws, sitting)[0]
    common.append(ws, sid, {'ev': 'approve', 'gate': 'founding', 'by': me, 'via': 'typed', 'key': KEY, 'sitting': sitting,
                            'msg_sha': approval.sha(said['text']), 'msg_at': said.get('stamp'), 'text_sha': text_sha})
    ref = [e for e in common.session_events(ws, sid) if e.get('ev') == 'approve'][-1]['event_id']
    out = [f'The workspace for {a["team"]} is built. {me} agreed to the setup summary, and that is recorded as the founding approval.']
    if a['storage'] == 'git':
        git(ws, 'add', '-A')
        mail = [] if git(ws, 'config', 'user.email')[1] else ['-c', 'user.email=not-set@invalid']
        ok, err = git(ws, *mail, 'commit', '-q', '-m', f'Set up the workspace for {a["team"]}\n\nApproved-by: {me} {ref}')
        if not ok:
            raise Refused(f'the files are written and the first commit failed: {shown(err, 300)}')
        out.append(share(ws, a)[1])
    shown_file(ws).unlink(missing_ok=True)
    return '\n'.join(out)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    sitting = os.environ.get(event.SESSION_VAR) or ''
    if '--session' in argv[:-1]:
        at = argv.index('--session')
        sitting = argv[at + 1]
        del argv[at:at + 2]
    if len(argv) == 2 and argv[1] == 'name':
        print(Path(argv[0]).resolve().name)
        return 0
    if len(argv) < 2 or argv[1] not in ('show', 'build', 'share') or (argv[1] != 'share' and len(argv) != 3):
        print(__doc__)
        return 2
    ws = Path(argv[0]).resolve()
    try:
        if argv[1] == 'share':
            if not (ws / 'workspace.yaml').is_file() or not (ws / '.git').exists():
                raise Refused('there is no workspace on git in this folder to share')
            ok, said = share(ws, {'branch': common.branch_of(ws), 'remote': argv[2] if len(argv) > 2 else None})
            print(said)
            return 0 if ok else 1
        a = answers_of(argv[2])
        print(show(ws, a) if argv[1] == 'show' else build(ws, a, sitting))
    except Refused as e:
        print(f'setup: {e}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
