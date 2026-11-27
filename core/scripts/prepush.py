#!/usr/bin/env python3
"""git's pre-push hook for a workspace on storage: git: the one check that refuses when it cannot tell.

  prepush.py install <workspace>      put the hook in place (a hook already there is kept and run after this one)
  prepush.py run <workspace> <remote> what the installed hook calls, with git's ref lines on stdin
  prepush.py adopt <workspace> <commit>
                                      run in a session by an approver's word: says whether their yes for a control-file
                                      commit made outside any session is on record. The gate hook writes the record when
                                      it reads their typed yes naming the commit; this command writes nothing

It reads the team branch only. A commit that changes a control file carries `Approved-by: <approver> <reference>`,
and the approver is one the team's copy named before this push. A memory entry that claims live state carries its
date and re-check line. A person who must push past it uses git's own switch; the assistant's sessions are stopped
from that by the gate hook, and docs/decisions.md says what stands behind both.
"""
import os
import re
import json
import stat
import subprocess
import sys
from pathlib import Path

import approval
import common
import doctor
from untrusted import shown

ZERO = re.compile(r'0{40,64}')
SHA = re.compile(r'[0-9a-f]{40,64}')
TRAILER = re.compile(r'(?mi)^Approved-by:[ \t]*(.+)$')
MARK = 'trampo pre-push'
# The runtime's transcript folder, written into the installed hook. The process that runs the hook never chooses it:
# its environment is the pushing session's to set.
TRANSCRIPTS = None


class CannotTell(Exception):
    pass


def git(ws, *args):
    r = subprocess.run(['git', '-c', 'core.fsmonitor=false', '-C', str(ws), *args], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise CannotTell(f'git {" ".join(args[:2])} failed: {r.stderr.strip()[:200]}')
    return r.stdout


def at(ws, commit, rel):
    """The file as that commit holds it, or '' when it does not hold it."""
    r = subprocess.run(['git', '-C', str(ws), 'show', f'{commit}:{rel}'], capture_output=True, text=True, timeout=60)
    return r.stdout if r.returncode == 0 else ''


def records(ws, tip):
    """The approve lines in the pushed ledger, by id. Only the gate hook writes one, and each ties to a typed message."""
    found = {}
    for name in git(ws, 'ls-tree', '-r', '--name-only', tip, '--', 'telemetry/events').split():
        for line in at(ws, tip, name).splitlines():
            try:
                e = json.loads(line)
            except ValueError:
                continue
            if isinstance(e, dict) and e.get('ev') == 'approve' and e.get('event_id'):
                found[str(e['event_id'])] = e
    return found


def unproven(ws, ref, e, approvers, standing):
    """Why this record cannot be tied to a person's yes, or None. A typed record the team's copy already holds passed
    here once, on the machine that had its transcript. Any other typed one is read in the folder the hook was
    installed with."""
    if e.get('via') != 'typed':
        return approval.proof_problem(ws, e, approvers)
    if ref in standing:
        return approval.proof_problem(ws, e, approvers, strict=False, transcripts=os.devnull)
    if not TRANSCRIPTS:
        raise CannotTell('this hook names no transcript folder, so a typed yes cannot be read: open a session in the '
                         'workspace, or a person runs prepush.py install <workspace>')
    return approval.proof_problem(ws, e, approvers, transcripts=TRANSCRIPTS)


def cited(text):
    """Every word of the Approved-by lines in these commit messages: the references among them are spent."""
    return {word for line in TRAILER.findall(text) for word in line.split()}


def not_covered(ws, message, path, approvers, ledger, standing, spent):
    """Why this commit message does not carry a recorded yes for a change to this control path, or None. Each
    "Approved-by: <approver> <reference>" line names an approver of the team's copy and the id of the approve line the
    gate hook wrote when that approver typed their yes: a name and a reference a session typed itself are not enough.
    A record stands for one commit: one another commit already cites is spent."""
    label = approval.control_label(path)
    lines = TRAILER.findall(message)
    if not lines:
        return 'carries no "Approved-by: <approver> <reference>" line'
    why = None
    for line in lines:
        named = next((a for a in approvers if line.casefold().startswith(a.casefold())), None)
        ref = line[len(named):].split() if named else []
        if not named:
            why = f'its line "{shown(line, 60)}" names no approver of the team\'s copy ({", ".join(approvers) or "nobody yet"})'
        elif not ref:
            why = f'its "Approved-by: {named}" line carries no reference (the id of the approve line: event.py approvals)'
        elif ref[0] not in ledger:
            why = (f'there is no approve record {shown(ref[0], 40)} in the pushed ledger (commit the session ledger '
                   'telemetry/events/<sid>.jsonl that holds it)')
        elif ref[0] in spent:
            why = (f'approve record {ref[0][:10]} already stood for another commit: one yes covers one commit, so the '
                   'approver is asked again for this change')
        else:
            e = ledger[ref[0]]
            if not same_name(e.get('by'), named):
                why = f"approve record {ref[0][:10]} is {shown(e.get('by'), 40)}'s, not {named}'s"
            elif e.get('gate') != 'control file':
                why = f"approve record {ref[0][:10]} is for {shown(e.get('gate'), 40)}, not for a control file"
            elif e.get('key') != label:
                why = f"approve record {ref[0][:10]} is for {shown(e.get('key'), 40)}, not {label}"
            else:
                why = unproven(ws, ref[0], e, approvers, standing)
                if why is None:
                    return None
    return why


ADOPTED = 'control commit'


def adopted(ws, commit, approvers, ledger, standing):
    """Whether an approver's typed yes naming this exact commit is on record: the way a control-file commit made by
    hand, outside any session, is approved without rewriting it."""
    for ref, e in ledger.items():
        key = str(e.get('key') or '').lower()
        if e.get('gate') == ADOPTED and e.get('commit') == commit and len(key) >= 7 and commit.startswith(key) \
                and e.get('via') == 'typed' and any(same_name(e.get('by'), a) for a in approvers) \
                and unproven(ws, ref, e, approvers, standing) is None:
            return True
    return False


def same_name(a, b):
    return common.same(a or '', b or '')


def control_changes(ws, commit):
    """Control paths this commit changes. A merge is judged on the paths it changes from every parent: what it takes from
    one parent is that parent's own change, judged on the parent's commits."""
    parents = git(ws, 'rev-list', '--parents', '-n', '1', commit).split()[1:]
    flags = ['-c'] if len(parents) > 1 else []
    names = git(ws, 'diff-tree', '--no-commit-id', '--name-only', '-r', *flags, commit).splitlines()
    return [p for p in names if approval.is_control(p)]


def problems(ws, old, new):
    """Why the commits old..new must not reach the team branch, as a list of lines."""
    cfg = common.parse_yaml(at(ws, old, 'workspace.yaml'))
    mode = (cfg.get('hooks') or {}).get('prepush') if isinstance(cfg.get('hooks'), dict) else None
    if mode == 'off':
        return []
    approvers, out = common.listed(cfg, 'approvers'), []
    ledger, before, covered = records(ws, new), records(ws, old), set()
    # A record the team's copy already holds, unchanged, passed this check on the machine that had its transcript.
    # Every other typed one is read against its transcript here, cited or not: a record pushed first and cited later
    # would otherwise reach the team's copy unread. A bridge record needs no transcript and is read when cited.
    standing = {ref for ref, e in ledger.items() if before.get(ref) == e}
    for ref, e in ledger.items():
        if ref not in standing and e.get('gate') in ('control file', ADOPTED) and e.get('via') == 'typed':
            why = unproven(ws, ref, e, approvers, standing)
            if why:
                out.append(f'approve record {ref[:10]} is new to the team\'s copy and {why}. It is pushed from the machine where '
                           'the yes was typed')
    spent = cited(git(ws, 'log', '-i', '--grep=^Approved-by:', '--format=%B', old))
    for commit in git(ws, 'rev-list', '--reverse', f'{old}..{new}').split():
        merge = len(git(ws, 'rev-list', '--parents', '-n', '1', commit).split()) > 2
        message = git(ws, 'log', '-1', '--format=%B', commit)
        for path in control_changes(ws, commit):
            why = not_covered(ws, message, path, approvers, ledger, standing, spent)
            if why and adopted(ws, commit, approvers, ledger, standing):
                why = None
            if why:
                out.append(f'{"merge commit" if merge else "commit"} {commit[:10]} changes {shown(path, 80)}, a control file, and {why}')
            else:
                covered.add(path)
        spent |= cited(message)
    for path in git(ws, 'diff', '--name-only', old, new).splitlines():
        if approval.is_control(path) and path not in covered and not any(path in o for o in out):
            out.append(f'this push changes {shown(path, 80)}, a control file, and no commit in it carries a recorded yes for it')
    for rel in git(ws, 'diff', '--name-only', old, new, '--', 'memory').splitlines():
        if not rel.endswith('.md'):
            continue
        before = set(doctor.unstamped_claims(at(ws, old, rel)))
        for head in doctor.unstamped_claims(at(ws, new, rel)):
            if head not in before:
                out.append(f'{shown(rel, 80)}: "{shown(head, 80)}" claims live state with no "As of <date> (<source>); re-check: '
                           '<command>" line. You have just checked it: say when and how')
    if out and mode == 'log':
        common.hook_log(ws, {'hook': 'prepush', 'would_block': True, 'why': out[:5]})
        return []
    return out


def run(ws, remote, lines):
    branch = f'refs/heads/{common.branch_of(ws)}'
    out = []
    for line in lines:
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) != 4:
            raise CannotTell(f'git handed it a ref line it does not know: {line.strip()[:80]}')
        _, new, ref, old = parts
        if ref != branch:
            continue
        if ZERO.fullmatch(new):
            out.append(f'this push deletes the team branch ({branch}): a person does that, outside a session')
            continue
        if ZERO.fullmatch(old):
            continue  # the first push of the branch: there is no team copy yet for a change to get past
        if not SHA.fullmatch(new) or not SHA.fullmatch(old):
            raise CannotTell(f'git handed it a ref line it does not know: {line.strip()[:80]}')
        out += problems(ws, old, new)
    return out


def hooks_dir(ws):
    """The repository's own hooks folder, the only one this file writes in. A core.hooksPath setting is not followed:
    the folder it names may serve every repository on the machine."""
    return Path(git(ws, 'rev-parse', '--path-format=absolute', '--git-common-dir').strip()) / 'hooks'


# beside the stubs: the hooks folder a setting outside the repository names, whose hooks the stubs run after their own
OUTSIDE = 'trampo-outside'
PASS = 'trampo pass-through'
OUR_MARKS = (MARK, PASS)
# The hooks git runs in a person's clone. The ones a receiving repository runs are left out: a workspace is not
# pushed into.
HOOK_NAMES = ('applypatch-msg', 'pre-applypatch', 'post-applypatch', 'pre-commit', 'pre-merge-commit',
              'prepare-commit-msg', 'commit-msg', 'post-commit', 'pre-rebase', 'post-checkout', 'post-merge',
              'pre-push', 'pre-auto-gc', 'post-rewrite', 'sendemail-validate', 'post-index-change',
              'reference-transaction')


def hooks_paths(ws):
    """(the core.hooksPath the repository's own config sets, the one in force from outside it), each a folder or None."""
    r = subprocess.run(['git', '-C', str(ws), 'config', '--show-scope', '--type=path', '--get-all', 'core.hooksPath'],
                       capture_output=True, text=True, timeout=60)
    own = outside = None
    for line in r.stdout.splitlines():
        scope, _, value = line.partition('\t')
        if not value:
            continue
        folder = Path(os.path.abspath(Path(ws) / value))
        if scope in ('local', 'worktree'):
            own = folder
        elif scope in ('system', 'global'):
            outside = folder
    return own, outside


def same_folder(a, b):
    return os.path.realpath(a) == os.path.realpath(b)


def recorded(ws):
    """The outside hooks folder the last install wrote down, or None."""
    try:
        text = (hooks_dir(ws) / OUTSIDE).read_text(encoding='utf-8').strip()
    except OSError:
        return None
    return Path(text) if text else None


def is_stub(path):
    try:
        text = Path(path).read_text(encoding='utf-8', errors='replace')
    except OSError:
        return False
    return any(m in text for m in OUR_MARKS)


def passing(ws):
    """The names of the pass-through stubs in the repository's own hooks folder."""
    try:
        home = hooks_dir(ws)
    except CannotTell:
        return []
    return [n for n in HOOK_NAMES if n not in STUBS and passes(home / n)]


def passes(hook):
    try:
        text = hook.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return False
    return PASS in text


def pass_through(home, outside, kept):
    """One stub in the repository's folder for each of the machine's other hooks, so they still run for this
    repository now that git looks here. A hook a person put here themselves stays and is named in kept."""
    for name in (n for n in HOOK_NAMES if n not in STUBS):
        hook, theirs = home / name, (outside / name if outside else None)
        ours = passes(hook)
        if not (theirs and theirs.is_file() and os.access(theirs, os.X_OK) and not is_stub(theirs)):
            if ours:
                hook.unlink()
            continue
        if hook.exists() and not ours:
            kept.append(name)
            continue
        # read again at run time: a stub of ours put out there later would call back here
        body = (f'#!{sys.executable} -B\n# {PASS}: installed by prepush.py install; edit nothing here\n'
                'import os\nimport subprocess\nimport sys\n'
                f'hook = {str(theirs)!r}\n'
                'try:\n    text = open(hook, encoding="utf-8", errors="replace").read()\nexcept OSError:\n    sys.exit(0)\n'
                f'if any(m in text for m in {OUR_MARKS!r}) or not os.access(hook, os.X_OK):\n    sys.exit(0)\n'
                'sys.exit(subprocess.run([hook, *sys.argv[1:]]).returncode)\n')
        if not ours or hook.read_text(encoding='utf-8') != body:
            hook.write_text(body, encoding='utf-8')
        hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return kept


def kept_note(home, kept):
    return (f'{", ".join(kept)} in {home} was put there by someone and is kept: the machine\'s hook of that name does '
            'not run for this repository') if kept else ''


def guarded(ws):
    """Every folder whose hooks git or a stub runs for this repository: a session writes a stub in none of them."""
    resolved = Path(git(ws, 'rev-parse', '--git-path', 'hooks').strip())
    return {hooks_dir(ws), resolved if resolved.is_absolute() else Path(ws) / resolved} | {f for f in (recorded(ws),) if f}


def strays(ws):
    """For the health check: a line when a stub of ours sits in a hooks folder outside the repository, where an older
    version put it. It serves every repository on the machine from there, so a person puts the old hook back."""
    for folder in {f for f in (hooks_paths(ws)[1], recorded(ws)) if f and not same_folder(f, hooks_dir(ws))}:
        found = [n for n in STUBS if is_stub(folder / n)]
        if found:
            fix = '; '.join(f'mv {folder}/{n}.next {folder}/{n}' if (folder / f'{n}.next').exists() else f'rm {folder}/{n}'
                            for n in found)
            return [f'a Trampo hook sits in {folder}, a hooks folder outside this repository, and runs for every '
                    f'repository that uses that folder. A person puts the old hook back: {fix}']
    return []


# what the runtime sets for the commands a session runs
SESSION_MARKS = ('CLAUDECODE', 'CLAUDE_CODE_SESSION_ID')
STUBS = {'pre-push': ('run', 'sys.exit(f"push refused: the pre-push check could not load ({e}). Open a session in the workspace, '
                              'or a person runs prepush.py install <workspace> from their own terminal")'),
         'prepare-commit-msg': ('message', 'sys.exit(0)')}


def install(ws, transcripts=None, kept=None):
    """Put git's hooks in place. The interpreter, this file's folder and the runtime's transcript folder are written
    in, so no shell, no PATH and no variable of the pushing process sit between git and the check; after the plugin
    or the runtime's config folder moves, the session start step installs them again. The session start step names
    the transcript folder the runtime gave it; a person installing by hand has it read from their environment. A
    command a session runs gets neither: its environment is the session's to set."""
    if transcripts is None and any(os.environ.get(v) for v in SESSION_MARKS):
        raise CannotTell('inside a session the hook is installed by the session start step, which names the transcript '
                         'folder the runtime gave it. A person runs prepush.py install <workspace> from their own terminal')
    home = hooks_dir(ws)
    own, outside = hooks_paths(ws)
    if own and not same_folder(own, home):
        raise CannotTell(f"this repository's own core.hooksPath names {own}, which someone set, and it is left as it is. "
                         f'Move the hooks you keep there into {home}, then in the workspace run '
                         'git config --local --unset core.hooksPath and install again')
    if outside and same_folder(outside, home):
        outside = None
    home.mkdir(parents=True, exist_ok=True)
    if outside:
        (home / OUTSIDE).write_text(f'{outside}\n', encoding='utf-8')
        if not own:
            # git then runs the stubs for this repository alone; the folder outside stays as it is and is run from here
            git(ws, 'config', '--local', 'core.hooksPath', str(home))
    else:
        (home / OUTSIDE).unlink(missing_ok=True)
    pass_through(home, outside, kept if kept is not None else [])
    for name, (command, on_error) in STUBS.items():
        hook = home / name
        if hook.exists() and MARK not in hook.read_text(encoding='utf-8', errors='replace'):
            hook.rename(hook.with_name(f'{name}.next'))
        body = (f'#!{sys.executable} -B\n# {MARK}: installed by prepush.py install; edit nothing here\n'
                'import sys\n'
                f'sys.path.insert(0, {str(Path(__file__).resolve().parent)!r})\n'
                f'try:\n    import prepush\nexcept Exception as e:\n    {on_error}\n'
                f'prepush.TRANSCRIPTS = {str(transcripts or approval.transcripts_dir())!r}\n'
                f'sys.exit(prepush.main([{command!r}, {str(Path(ws).resolve())!r}, *sys.argv[1:]]))\n')
        if not hook.exists() or hook.read_text(encoding='utf-8') != body:
            hook.write_text(body, encoding='utf-8')
        hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return hooks_dir(ws) / 'pre-push'


def ours(ws):
    """Whether git is running this hook for the workspace's own repository. With one hooks folder set for the whole
    machine, every repository runs it, and the others are none of its business."""
    here = subprocess.run(['git', 'rev-parse', '--path-format=absolute', '--git-common-dir'], capture_output=True, text=True)
    if here.returncode != 0:
        raise CannotTell('it was not run from inside a repository')
    return here.stdout.strip() == git(ws, 'rev-parse', '--path-format=absolute', '--git-common-dir').strip()


def then(ws, name, args, text=None):
    """Run the hook that was in the repository before this one, then the machine's hook of the same name from the
    folder it lives in, and give the first refusal. A stub of ours found out there is skipped: it would call back here."""
    home, outside = hooks_dir(ws), recorded(ws)
    for after in [home / f'{name}.next'] + ([outside / name] if outside else []):
        if after.is_file() and os.access(after, os.X_OK) and not is_stub(after):
            code = subprocess.run([str(after), *args], input=text, text=True).returncode
            if code:
                return code
    return 0


def message(ws, args):
    """prepare-commit-msg: a commit made from a session ends `Session: <sid> <kind>`, so a change can be traced to the
    session that made it where several sessions commit under one git name. It never refuses a commit."""
    try:
        session = os.environ.get('CLAUDE_CODE_SESSION_ID') or ''
        here = common.active(ws, session) if (session or os.environ.get('TRAMPO_SID')) and ours(ws) else None
        # a replay re-commits someone else's work: it keeps its author's session
        replay = any(Path(git(ws, 'rev-parse', '--git-path', n).strip()).exists() for n in ('CHERRY_PICK_HEAD', 'REVERT_HEAD', 'rebase-merge'))
        body = subprocess.run(['git', 'stripspace', '--strip-comments'], input=Path(args[0]).read_text(encoding='utf-8'),
                              capture_output=True, text=True).stdout.strip()
        if here and not replay and body:
            sid, kind = here
            kind = kind or next((e.get('kind') for e in common.session_events(ws, sid) if e.get('kind')), '')
            subprocess.run(['git', 'interpret-trailers', '--in-place', '--if-exists', 'doNothing', '--trailer',
                            f'Session: {sid} {kind}'.strip(), args[0]], capture_output=True)
    except Exception:
        pass
    try:
        return then(ws, 'prepare-commit-msg', args)
    except Exception:
        return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) >= 2 and argv[0] == 'install':
        try:
            kept = []
            print(f'installed {install(argv[1], kept=kept)}')
            if kept:
                print(kept_note(hooks_dir(argv[1]), kept))
        except CannotTell as e:
            print(f'not installed: {e}', file=sys.stderr)
            return 1
        return 0
    if len(argv) >= 3 and argv[0] == 'adopt':
        try:
            full = git(argv[1], 'rev-parse', '--verify', '--quiet', f'{argv[2]}^{{commit}}').strip()
        except CannotTell:
            full = ''
        found = [e for e in common.load_events(argv[1])[0] if e.get('gate') == ADOPTED and full and e.get('commit') == full]
        if not found:
            print(f'no yes is on record for commit {argv[2]}: an approver types their yes naming it, in a session', file=sys.stderr)
            return 1
        print(f"{found[0].get('by')}'s yes for commit {full[:10]} is on record ({found[0].get('event_id')}). Commit the session "
              'ledger that holds it and share: the push carries both')
        return 0
    if len(argv) >= 2 and argv[0] == 'message':
        return message(argv[1], argv[2:])
    if len(argv) < 2 or argv[0] != 'run':
        print(__doc__)
        return 2
    ws, remote = argv[1], (argv[2] if len(argv) > 2 else 'origin')
    try:
        text = sys.stdin.read()
        found = run(ws, remote, text.splitlines()) if ours(ws) else []
    except Exception as e:  # the boundary: unsure is a refusal, with the reason
        print(f'push refused: the pre-push check could not tell whether this push is in order ({e}). Fix what it names and '
              'push again', file=sys.stderr)
        return 1
    if found:
        print('push refused, nothing was sent:\n- ' + '\n- '.join(found), file=sys.stderr)
        return 1
    return then(ws, 'pre-push', argv[2:], text)


if __name__ == '__main__':
    sys.exit(main())
