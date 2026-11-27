#!/usr/bin/env python3
"""The sync for storage: git: local commits reach origin through a throwaway worktree, the checkout moves without
losing anyone's uncommitted work, and a conflict stops, waits or is stranded. Slow: every case builds two clones."""
import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import testenv  # noqa: E402
import sync  # noqa: E402


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        top = Path(self.tmp.name)
        self.ws = testenv.workspace(top / 'ws')
        self.origin = top / 'origin.git'
        testenv.sh(top, 'git', 'init', '-q', '--bare', '-b', 'main', str(self.origin))
        testenv.sh(self.ws, 'git', 'remote', 'add', 'origin', str(self.origin))
        self.commit(self.ws, 'workspace', **{'workspace.yaml': None, '.gitignore': None, 'notes.md': 'one\n',
                                             'telemetry/events/s1.jsonl': '{"n": 1}\n'})
        testenv.sh(self.ws, 'git', 'push', '-q', '-u', 'origin', 'main')
        self.other = top / 'other'
        testenv.sh(top, 'git', 'clone', '-q', str(self.origin), str(self.other))
        testenv.sh(self.other, 'git', 'config', 'user.name', 'Sam Okoro')
        testenv.sh(self.other, 'git', 'config', 'user.email', 'sam@example.invalid')

    def tearDown(self):
        self.tmp.cleanup()

    def commit(self, repo, message, **files):
        for rel, text in files.items():
            if text is not None:
                (repo / rel).parent.mkdir(parents=True, exist_ok=True)
                (repo / rel).write_text(text)
            testenv.sh(repo, 'git', 'add', rel)
        testenv.sh(repo, 'git', 'commit', '-q', '-m', message)

    def theirs(self, message, **files):
        testenv.sh(self.other, 'git', 'pull', '-q')
        self.commit(self.other, message, **files)
        testenv.sh(self.other, 'git', 'push', '-q')

    def sync(self, *mode):
        text = io.StringIO()
        with contextlib.redirect_stdout(text), contextlib.redirect_stderr(text):
            code = sync.main([str(self.ws), *mode])
        return code, text.getvalue()

    def rev(self, name, repo=None):
        return testenv.sh(repo or self.ws, 'git', 'rev-parse', name).strip()

    def level(self):
        return self.rev('HEAD') == self.rev('refs/heads/main', self.origin)


class Plain(Case):
    def test_local_commits_reach_origin_and_theirs_arrive_with_uncommitted_work_untouched(self):
        self.commit(self.ws, 'mine', **{'mine.md': 'mine\n'})
        self.theirs('theirs', **{'theirs.md': 'theirs\n'})
        (self.ws / 'draft.md').write_text('not committed\n')
        (self.ws / 'notes.md').write_text('one\nedited, not committed\n')
        code, text = self.sync()
        self.assertEqual(code, 0, text)
        self.assertTrue(self.level())
        self.assertTrue((self.ws / 'theirs.md').exists())
        self.assertEqual((self.ws / 'draft.md').read_text(), 'not committed\n')
        self.assertEqual((self.ws / 'notes.md').read_text(), 'one\nedited, not committed\n')
        self.assertEqual(self.sync()[0], 0)

    def test_a_commit_origin_already_holds_in_other_context_is_not_replayed(self):
        self.theirs('same change, landed elsewhere', **{'notes.md': 'zero\none\ntwo\n'})
        self.commit(self.ws, 'the same change again', **{'notes.md': 'one\ntwo\n'})
        code, text = self.sync()
        self.assertEqual(code, 0, text)
        self.assertEqual((self.ws / 'notes.md').read_text(), 'zero\none\ntwo\n')

    def test_it_serves_the_team_branch_only_and_one_run_at_a_time(self):
        lock = self.ws / '.git' / 'trampo-sync.lock'
        lock.mkdir()
        (lock / 'pid').write_text(str(os.getpid()))
        self.assertEqual(self.sync()[0], 3)
        (lock / 'pid').write_text('999999999')
        self.assertEqual(self.sync()[0], 0)
        testenv.sh(self.ws, 'git', 'checkout', '-q', '-b', 'side')
        self.assertEqual(self.sync()[0], 1)


class Usage(unittest.TestCase):
    def said(self, *argv):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            sync.main(list(argv))
        return out.getvalue()

    def test_asking_for_help_prints_the_usage_and_says_nothing_about_storage(self):
        for argv in (['--help'], ['-h'], []):
            self.assertIn('sync.py <workspace>', self.said(*argv))
            self.assertNotIn('not on storage', self.said(*argv))

    def test_a_folder_that_is_no_workspace_is_named_as_that(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIn('is not a workspace', self.said(tmp))
            self.assertNotIn('not on storage', self.said(tmp))


class Conflict(Case):
    def setUp(self):
        super().setUp()
        self.theirs('theirs', **{'notes.md': 'one\ntheirs\n'})
        self.commit(self.ws, 'mine', **{'notes.md': 'one\nmine\n'})
        self.commit(self.ws, 'mine too', **{'fine.md': 'fine\n'})
        self.before = self.rev('HEAD')

    def test_a_conflict_stops_with_the_branch_untouched_and_can_be_dropped(self):
        code, text = self.sync()
        self.assertEqual(code, 2, text)
        self.assertIn('conflicted: notes.md', text)
        self.assertEqual(self.rev('HEAD'), self.before)
        self.assertEqual(self.sync()[0], 2)
        self.assertEqual(self.sync('--abort')[0], 0)
        self.assertEqual(self.rev('HEAD'), self.before)

    def test_a_resolved_conflict_continues(self):
        _, text = self.sync()
        w = Path(next(l for l in text.splitlines() if 'worktree: ' in l).split('worktree: ')[1])
        (w / 'notes.md').write_text('one\ntheirs\nmine\n')
        testenv.sh(w, 'git', 'add', 'notes.md')
        code, text = self.sync('--continue')
        self.assertEqual(code, 0, text)
        self.assertTrue(self.level())
        self.assertEqual((self.ws / 'notes.md').read_text(), 'one\ntheirs\nmine\n')

    def test_stranding_keeps_the_conflicting_commit_on_a_ref_and_still_moves_the_branch(self):
        code, text = self.sync('--strand')
        self.assertEqual(code, 0, text)
        self.assertTrue(self.level())
        self.assertTrue((self.ws / 'fine.md').exists())
        self.assertEqual((self.ws / 'notes.md').read_text(), 'one\ntheirs\n')
        ref = testenv.sh(self.ws, 'git', 'for-each-ref', '--format=%(refname)', 'refs/sync/stranded/').strip()
        self.assertEqual(self.rev(ref), self.before)
        self.assertIn('mine', (self.ws / '.git' / 'trampo-sync-stranded.txt').read_text())


class Appends(Case):
    def test_two_writers_appending_to_one_ledger_both_keep_their_lines(self):
        self.theirs('theirs', **{'telemetry/events/s1.jsonl': '{"n": 1}\n{"n": "theirs"}\n'})
        self.commit(self.ws, 'mine', **{'telemetry/events/s1.jsonl': '{"n": 1}\n{"n": "mine"}\n'})
        code, text = self.sync()
        self.assertEqual(code, 0, text)
        self.assertEqual((self.ws / 'telemetry/events/s1.jsonl').read_text(), '{"n": 1}\n{"n": "theirs"}\n{"n": "mine"}\n')

    def test_a_ledger_side_that_edited_a_line_is_not_an_append(self):
        self.theirs('theirs', **{'telemetry/events/s1.jsonl': '{"n": 1}\n{"n": "theirs"}\n'})
        self.commit(self.ws, 'mine', **{'telemetry/events/s1.jsonl': '{"n": "rewritten"}\n{"n": "mine"}\n'})
        self.assertEqual(self.sync()[0], 2)

    def test_uncommitted_ledger_lines_origin_lacks_are_carried_across_the_move(self):
        self.theirs('theirs', **{'telemetry/events/s1.jsonl': '{"n": 1}\n{"n": "theirs"}\n'})
        (self.ws / 'telemetry/events/s1.jsonl').write_text('{"n": 1}\n{"n": "live"}\n')
        code, text = self.sync()
        self.assertEqual(code, 0, text)
        self.assertEqual((self.ws / 'telemetry/events/s1.jsonl').read_text(), '{"n": 1}\n{"n": "theirs"}\n{"n": "live"}\n')

    def test_an_uncommitted_edit_that_differs_from_origins_change_refuses_and_changes_nothing(self):
        self.theirs('theirs', **{'notes.md': 'theirs rewrote it\n'})
        (self.ws / 'notes.md').write_text('mine rewrote it\n')
        future = self.ws.stat().st_mtime + 3600
        os.utime(self.ws / 'notes.md', (future, future))
        before = self.rev('HEAD')
        code, text = self.sync()
        self.assertEqual(code, 1, text)
        self.assertIn('notes.md', text)
        self.assertEqual(self.rev('HEAD'), before)
        self.assertEqual((self.ws / 'notes.md').read_text(), 'mine rewrote it\n')

    def test_an_uncommitted_copy_origin_already_holds_gives_way(self):
        self.theirs('theirs', **{'notes.md': 'one\ntwo\n'})
        (self.ws / 'notes.md').write_text('one\ntwo\n')
        self.assertEqual(self.sync()[0], 0)
        self.assertEqual(testenv.sh(self.ws, 'git', 'status', '--porcelain').strip(), '')


if __name__ == '__main__':
    unittest.main()
