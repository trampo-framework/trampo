#!/usr/bin/env python3
"""Bring this checkout's team branch level with origin without touching anyone's uncommitted work (storage: git).

  sync.py <workspace>             fetch, send local commits, move the branch to origin's
  sync.py <workspace> --continue  after resolving a replay conflict in the folder it printed
  sync.py <workspace> --abort     drop the replay; the branch is left as it was
  sync.py <workspace> --strand    as the default, but a commit that conflicts is skipped and kept on
                                  refs/sync/stranded/<time>; the branch still moves

Exit: 0 level with origin, 1 refused (nothing changed), 2 a conflict is waiting, 3 another sync is running.

Local commits are replayed onto origin's branch in a throwaway worktree and pushed from there, so the checkout
itself is never pulled, stashed or rebased: several sessions share it, and each of those would move or hide another
session's uncommitted files. The checkout moves only by `reset --keep`, which refuses to overwrite a local edit.
"""
import fnmatch
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import common

PUSH_ATTEMPTS = 3
EVENT_LOGS = 'telemetry/events/*.jsonl'
LINE_LOGS = ('.jsonl', '.tsv')
NAME = 'trampo-sync'


class Stop(Exception):
    def __init__(self, code, text):
        super().__init__(text)
        self.code = code


def say(text):
    print(f'sync: {text}', flush=True)


def run(cwd, *args, binary=False):
    """(exit status, stdout) of one git call. Large files are never fetched on the way: this only moves text."""
    r = subprocess.run(['git', '-c', 'core.fsmonitor=false', '-C', str(cwd), *args], capture_output=True,
                       env={**os.environ, 'GIT_LFS_SKIP_SMUDGE': '1', 'GIT_EDITOR': 'true'})
    return r.returncode, r.stdout if binary else r.stdout.decode('utf-8', 'replace')


def out(cwd, *args):
    code, text = run(cwd, *args)
    if code:
        raise Stop(1, f'git {" ".join(args[:3])} failed')
    return text.strip()


def ok(cwd, *args):
    return run(cwd, *args)[0] == 0


def blob(cwd, name):
    code, data = run(cwd, 'cat-file', 'blob', name, binary=True)
    return data if code == 0 else None


class Sync:
    def __init__(self, ws, strand=False):
        self.ws = Path(ws).resolve()
        self.branch = common.branch_of(self.ws)
        self.origin = f'origin/{self.branch}'
        self.strand = strand
        self.common_dir = Path(out(self.ws, 'rev-parse', '--path-format=absolute', '--git-common-dir'))
        self.state = self.common_dir / NAME
        self.lock = self.common_dir / f'{NAME}.lock'
        self.list = self.common_dir / f'{NAME}-stranded.txt'
        self.w, self.start, self.local, self.stranded = None, '', [], []
        self.carry, self.keep = None, None
        self.append_only = [EVENT_LOGS, *common.listed(common.config(self.ws), 'append_only')]

    # Every session's git shares one lock on origin's ref, so a fetch can lose a race it would win seconds later
    def fetch(self):
        for _ in range(5):
            if ok(self.ws, 'fetch', '-q', 'origin'):
                return
            time.sleep(2)
        raise Stop(1, 'fetch from origin failed 5 times')

    def take_lock(self):
        for _ in range(2):
            try:
                self.lock.mkdir()
                (self.lock / 'pid').write_text(str(os.getpid()))
                return
            except FileExistsError:
                try:
                    owner = int((self.lock / 'pid').read_text().strip())
                    os.kill(owner, 0)
                except (OSError, ValueError):
                    shutil.rmtree(self.lock, ignore_errors=True)
                    continue
                raise Stop(3, f'another sync is running (pid {owner}); nothing changed')
        raise Stop(3, 'another sync took the lock; nothing changed')

    def read_state(self):
        if self.state.is_file():
            pairs = dict(l.split('=', 1) for l in self.state.read_text().splitlines() if '=' in l)
            self.w, self.start = Path(pairs['worktree']) if pairs.get('worktree') else None, pairs.get('head', '')

    def remove_worktree(self):
        if self.w:
            run(self.ws, 'worktree', 'remove', '--force', str(self.w))
            shutil.rmtree(self.w, ignore_errors=True)
        run(self.ws, 'worktree', 'prune')
        self.state.unlink(missing_ok=True)
        self.w = None

    def head(self, cwd=None):
        return out(cwd or self.ws, 'rev-parse', 'HEAD')

    def unmerged(self):
        return [p for p in out(self.w, 'diff', '--name-only', '--diff-filter=U').splitlines() if p]

    def stop_on_conflict(self):
        lines = [f'conflict replaying local commits onto {self.origin}. The branch is untouched.', f'worktree: {self.w}',
                 *[f'  conflicted: {p}' for p in self.unmerged()],
                 f"resolve there, 'git -C {self.w} add <path>', then: sync.py {self.ws} --continue  (or --abort)"]
        raise Stop(2, '\nsync: '.join(lines))

    # --cherry-pick drops a local commit only when origin has the same patch. The same change pushed once from a
    # worktree and committed again in the checkout has other context, so its replay conflicts on its own lines.
    # Origin holds a commit when it has every line the commit adds and none it removes.
    def held_on_origin(self, c):
        if not ok(self.ws, 'rev-parse', '-q', '--verify', f'{c}~1'):
            return False
        for path in out(self.ws, 'diff', '--name-only', f'{c}~1', c).splitlines():
            theirs = blob(self.ws, f'{self.origin}:{path}')
            if theirs is None:
                if ok(self.ws, 'cat-file', '-e', f'{c}:{path}'):
                    return False
                continue
            have = set(theirs.decode('utf-8', 'replace').split('\n'))
            diff = run(self.ws, 'diff', '-U0', f'{c}~1', c, '--', path)[1].split('\n')
            added = [l[1:] for l in diff if l.startswith('+') and not l.startswith('+++ ')]
            removed = [l[1:] for l in diff if l.startswith('-') and not l.startswith('--- ')]
            if any(l not in have for l in added) or any(l in have for l in removed):
                return False
        return True

    def git_dir(self):
        return Path(out(self.w, 'rev-parse', '--absolute-git-dir'))

    def replaying(self):
        gd = self.git_dir()
        return any((gd / n).exists() for n in ('rebase-merge', 'rebase-apply', 'CHERRY_PICK_HEAD', 'sequencer/todo'))

    def is_append_only(self, path):
        return any(fnmatch.fnmatchcase(path, pat) for pat in self.append_only)

    # Two writers that both appended to one log conflict at the same end. Both sides' new lines are kept, origin's
    # first, only when neither side touched a line the base had: an edit or a removal is not an append.
    @staticmethod
    def union_of_appends(base, ours, theirs):
        nb = len(base)
        if ours[:nb] != base or theirs[:nb] != base:
            return None
        seen = {}
        for l in ours[nb:]:
            seen[l] = seen.get(l, 0) + 1
        merged = list(ours)
        for l in theirs[nb:]:
            if seen.get(l, 0) > 0:
                seen[l] -= 1
            else:
                merged.append(l)
        return merged

    def resolve_appends(self):
        done = True
        for path in self.unmerged():
            stages = [l.split()[2] for l in out(self.w, 'ls-files', '-u', '--', path).splitlines()]
            if not self.is_append_only(path) or sorted(s for s in stages if s in '23') != ['2', '3']:
                done = False
                continue
            sides = [(run(self.w, 'show', f':{n}:{path}')[1] if str(n) in stages else '').splitlines() for n in (1, 2, 3)]
            merged = self.union_of_appends(*sides)
            if merged is None:
                done = False
                continue
            (self.w / path).write_text(''.join(l + '\n' for l in merged), encoding='utf-8')
            out(self.w, 'add', '--', path)
            say(f"kept both sides' appended lines, origin's first: {path}")
        return done

    def continue_replay(self):
        gd = self.git_dir()
        while self.replaying():
            if self.unmerged() and not self.resolve_appends():
                self.stop_on_conflict()
            if (gd / 'rebase-merge').exists() or (gd / 'rebase-apply').exists():
                step = ('rebase', '--continue')
            elif ok(self.w, 'diff', '--cached', '--quiet') and (gd / 'CHERRY_PICK_HEAD').exists():
                step = ('cherry-pick', '--skip')
            else:
                step = ('cherry-pick', '--continue')
            if not ok(self.w, *step) and not self.unmerged():
                self.stop_on_conflict()

    # An unattended sync that stops on a conflict nobody resolves leaves the branch frozen behind origin. Each commit
    # is picked alone, so one conflict costs only that commit and the ones built on it.
    def replay_or_strand(self):
        gd = self.git_dir()
        out(self.w, 'reset', '-q', '--hard', self.origin)
        self.stranded = []
        for c in self.local:
            if self.held_on_origin(c) or ok(self.w, 'cherry-pick', c):
                continue
            if (gd / 'CHERRY_PICK_HEAD').exists() and (not self.unmerged() or self.resolve_appends()):
                if ok(self.w, 'diff', '--cached', '--quiet'):
                    if ok(self.w, 'cherry-pick', '--skip'):
                        continue
                elif ok(self.w, 'cherry-pick', '--continue'):
                    continue
            if not ok(self.w, 'cherry-pick', '--abort'):
                run(self.w, 'reset', '-q', '--hard', 'HEAD')
            self.stranded.append(c)

    def push_worktree(self):
        for attempt in range(1, PUSH_ATTEMPTS + 1):
            r = subprocess.run(['git', '-C', str(self.w), 'push', '-q', 'origin', f'HEAD:{self.branch}'], capture_output=True, text=True)
            if r.returncode == 0:
                return
            if attempt == PUSH_ATTEMPTS:
                raise Stop(1, f'push rejected {attempt} times; worktree kept at {self.w}\n{r.stderr.strip()[:1500]}')
            say(f'origin moved or refused the push; replaying again (attempt {attempt + 1})')
            self.fetch()
            if self.strand:
                self.replay_or_strand()
            elif not ok(self.w, 'rebase', '-q', self.origin):
                self.continue_replay()

    def report_stranded(self):
        if not self.stranded:
            self.list.unlink(missing_ok=True)
            return
        ref = f"refs/sync/stranded/{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        out(self.ws, 'update-ref', ref, self.start)
        rows = [out(self.ws, 'log', '-1', '--format=%H %s', c) for c in self.stranded]
        self.list.write_text(''.join(r + '\n' for r in rows), encoding='utf-8')
        say(f'stranded {len(rows)} local commit(s) that conflict with {self.origin}; kept on {ref}:')
        for r in rows:
            say(f'  {r}')
        say(f'inspect: git log --oneline {self.origin}..{ref}')

    def aside(self, kind):
        return self.common_dir / f'{NAME}-{kind}' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')

    # A dirty path that origin also changed blocks `reset --keep`. It is set aside only when nothing in it can be
    # lost: origin holds every byte or every line of it, or what origin lacks is copied under the git folder and put
    # back after the branch moves.
    def clear_overlaps(self):
        changed = set(out(self.ws, 'diff', '--name-only', 'HEAD', self.origin).splitlines())
        entries = run(self.ws, 'status', '--porcelain', '-z', '--untracked-files=all')[1].split('\0')
        untracked, tracked, superseded, carried, kept, blockers = [], [], [], [], [], []
        skip = False
        for entry in entries:
            if skip or len(entry) < 4:
                skip = False
                continue
            status, path = entry[:2], entry[3:]
            skip = status[0] in 'RC'
            if path not in changed:
                continue
            f = self.ws / path
            data = f.read_bytes() if f.is_file() else None
            theirs = blob(self.ws, f'{self.origin}:{path}')
            have = out(self.ws, 'hash-object', '--', path) if data is not None else ''
            want = run(self.ws, 'rev-parse', '-q', '--verify', f'{self.origin}:{path}')[1].strip()
            bucket = untracked if status == '??' else tracked
            if want == have or self.origin_held(path, have) or (theirs is not None and data and (
                    theirs.startswith(data) or (path.endswith(LINE_LOGS) and set(data.split(b'\n')) <= set(theirs.split(b'\n'))))):
                bucket.append(path)
            elif fnmatch.fnmatchcase(path, EVENT_LOGS) and theirs is not None and data:
                carried.append((path, [l for l in data.split(b'\n') if l and l not in set(theirs.split(b'\n'))]))
                bucket.append(path)
            elif theirs is not None and data is not None and len(data) > len(theirs) and data.startswith(theirs):
                kept.append(path)
                bucket.append(path)
            elif self.landed_after_written(path):
                superseded.append(path)
                if status != '??':
                    tracked.append(path)
            else:
                blockers.append(path)
        # refuse before setting anything aside: a refusal skips the reset, so a restored file would stay at the older copy
        if blockers:
            raise Stop(1, ''.join(f'  {p}\n' for p in blockers) + f"uncommitted edits above differ from {self.origin}'s change to the "
                       'same path; commit or resolve them first. The branch is untouched.')
        if carried:
            self.carry = self.aside('carry')
            for path, lines in carried:
                (self.carry / path).parent.mkdir(parents=True, exist_ok=True)
                (self.carry / path).write_bytes(b''.join(l + b'\n' for l in lines))
        if kept:
            self.keep = self.aside('keep')
            for path in kept:
                (self.keep / path).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(self.ws / path, self.keep / path)
        for path in untracked:
            (self.ws / path).unlink(missing_ok=True)
        if superseded:
            aside = self.aside('aside')
            for path in superseded:
                (aside / path).parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(self.ws / path), str(aside / path))
            say(f'set aside {len(superseded)} draft(s) origin landed after they were written: {aside}')
        if tracked:
            out(self.ws, 'restore', '--source=HEAD', '--staged', '--worktree', '--', *tracked)

    def origin_held(self, path, have):
        """Whether origin's history ever held exactly this copy of the file."""
        if not have:
            return False
        log = run(self.ws, 'log', '--raw', '--no-abbrev', '--no-renames', '--format=', self.origin, '--', path)[1]
        return any(len(l.split()) > 3 and l.split()[3] == have for l in log.splitlines())

    def landed_after_written(self, path):
        landed = run(self.ws, 'log', '-1', '--format=%ct', self.origin, '--', path)[1].strip()
        f = self.ws / path
        return bool(landed) and f.is_file() and f.stat().st_mtime < int(landed)

    def restore_carried(self):
        for top, verb in ((self.keep, 'kept uncommitted appends to origin\'s copy'), (self.carry, 'kept uncommitted event lines origin lacks')):
            if not top:
                continue
            for f in (p for p in top.rglob('*') if p.is_file()):
                dest = self.ws / f.relative_to(top)
                dest.parent.mkdir(parents=True, exist_ok=True)
                if top is self.keep:
                    shutil.copy2(f, dest)
                else:
                    with dest.open('ab') as fh:
                        fh.write(f.read_bytes())
            say(f'{verb}: {top}')

    # Another session can commit to this checkout at any point of a sync, and the reset would drop that commit. The
    # branch moves only while HEAD is still the one whose commits origin was checked to hold, and a commit that lands
    # inside the reset itself is put back.
    def align(self, expected):
        gained = f'the branch gained commits during the sync; run sync.py {self.ws} again to send them'
        self.fetch()
        if self.head() == out(self.ws, 'rev-parse', self.origin):
            return
        if self.head() != expected:
            raise Stop(1, gained)
        self.clear_overlaps()
        if self.head() != expected:
            self.restore_carried()
            raise Stop(1, gained)
        out(self.ws, 'reset', '-q', '--keep', self.origin)
        before = out(self.ws, 'rev-parse', 'ORIG_HEAD')
        if before != expected:
            if self.head() != out(self.ws, 'rev-parse', self.origin) or not ok(self.ws, 'reset', '-q', '--keep', before):
                raise Stop(1, f'a commit landed during the reset; the branch is at {self.head()[:10]}, the commit is {before}')
            self.restore_carried()
            raise Stop(1, gained)
        self.restore_carried()

    def start_replay(self):
        if self.w and not self.w.is_dir():
            gone = self.w
            self.remove_worktree()
            say(f'cleared the record of a replay whose worktree is gone: {gone}')
        if self.w:
            raise Stop(2, f'a replay is already waiting in {self.w}\nsync: run --continue or --abort')
        self.fetch()
        if not ok(self.ws, 'rev-parse', '-q', '--verify', self.origin):
            raise Stop(1, f"the team's copy has no {self.branch} yet: the first share of a new workspace is made by setup "
                          '(setup.py <workspace> share), which needs no command from a person')
        self.start = self.head()
        local = out(self.ws, 'rev-list', '--reverse', '--no-merges', '--cherry-pick', '--right-only', f'{self.origin}...HEAD').split()
        self.local = [c for c in local if not self.held_on_origin(c)]
        if not self.local:
            return
        self.w = Path(tempfile.mkdtemp(prefix=f'{NAME}.'))
        self.state.write_text(f'worktree={self.w}\nhead={self.start}\n')
        # a full checkout per sync fills the disk on a large workspace: only the paths the local commits touch are needed
        out(self.ws, 'worktree', 'add', '-q', '--no-checkout', '--detach', '--force', str(self.w), self.origin)
        paths = sorted({'/' + p for c in self.local if ok(self.ws, 'rev-parse', '-q', '--verify', f'{c}~1')
                        for p in out(self.ws, 'diff', '--name-only', '--no-renames', f'{c}~1', c).splitlines()})
        subprocess.run(['git', '-C', str(self.w), 'sparse-checkout', 'set', '--no-cone', '--stdin'], input='\n'.join(paths) + '\n',
                       text=True, capture_output=True)
        out(self.w, 'checkout', '-q')
        say(f'replaying {len(self.local)} local commit(s) onto {self.origin}')
        if self.strand:
            self.replay_or_strand()
        elif not ok(self.w, 'cherry-pick', *self.local):
            self.continue_replay()

    def go(self, mode):
        if out(self.ws, 'rev-parse', '--path-format=absolute', '--git-dir') != str(self.common_dir):
            raise Stop(1, 'this is a linked worktree: the sync serves the main checkout')
        self.take_lock()
        try:
            if run(self.ws, 'symbolic-ref', '--short', '-q', 'HEAD')[1].strip() != self.branch:
                raise Stop(1, f'checkout is not on {self.branch}')
            self.read_state()
            if mode == '--abort':
                if not self.w:
                    raise Stop(1, 'no sync in progress')
                self.remove_worktree()
                say(f'replay dropped; the branch is left at {self.head()[:10]}')
                return
            if mode == '--continue':
                if not self.w or not self.w.is_dir():
                    raise Stop(1, 'no sync in progress')
                self.continue_replay()
            else:
                self.start_replay()
            if self.w:
                self.push_worktree()
                pushed = self.head(self.w)
                self.fetch()
                if not ok(self.ws, 'merge-base', '--is-ancestor', pushed, self.origin):
                    raise Stop(1, f'pushed {pushed} is not on {self.origin}; worktree kept at {self.w}')
                self.remove_worktree()
                if self.head() != self.start:
                    raise Stop(1, f'the branch gained commits during the replay; run sync.py {self.ws} again to send them')
            if self.strand:
                self.report_stranded()
            self.align(self.start)
            say(f"{self.branch} = {self.origin} = {out(self.ws, 'log', '--oneline', '-1')}")
        except Stop as e:
            # a --strand run is never continued, so a replay it leaves behind would only make the next run report a conflict
            if self.strand and e.code != 2 and self.w:
                self.remove_worktree()
            raise
        finally:
            shutil.rmtree(self.lock, ignore_errors=True)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    mode = argv[1] if len(argv) > 1 else ''
    if mode == '--session':
        # the session start step: nobody is there to continue a replay, so what a stranding run cannot settle is dropped
        print(f"== {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}", flush=True)
        code = main([argv[0], '--strand'])
        if code == 2:
            main([argv[0], '--abort'])
        print(f'exit={code}', flush=True)
        return code
    if not argv or argv[0].startswith('-') or mode not in ('', '--continue', '--abort', '--strand'):
        print(__doc__)
        return 1
    if not (Path(argv[0]) / 'workspace.yaml').is_file():
        print(f'sync: {argv[0]} is not a workspace (no workspace.yaml there): give the workspace folder')
        return 1
    if common.storage_of(argv[0]) != 'git':
        print('sync: this workspace is not on storage: git; a shared folder is synced by its own client')
        return 1
    try:
        Sync(argv[0], strand=mode == '--strand').go(mode)
    except Stop as e:
        print(f'sync: {e}', file=sys.stderr if e.code == 1 else sys.stdout, flush=True)
        return e.code
    return 0


if __name__ == '__main__':
    sys.exit(main())
