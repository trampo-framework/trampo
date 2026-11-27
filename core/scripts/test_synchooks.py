#!/usr/bin/env python3
"""The session start step and the stop gate for storage: git: what a session wrote must be committed and on origin
before it stops, and what the last sync set aside is said at the start."""
import contextlib
import io
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import testenv  # noqa: E402
import common  # noqa: E402
import event  # noqa: E402
import hooks  # noqa: E402
import test_wiring as wiring  # noqa: E402


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        top = Path(self.tmp.name)
        self.ws = testenv.workspace(top / 'ws')
        testenv.sh(top, 'git', 'init', '-q', '--bare', '-b', 'main', str(top / 'origin.git'))
        testenv.sh(self.ws, 'git', 'remote', 'add', 'origin', str(top / 'origin.git'))
        testenv.sh(self.ws, 'git', 'add', 'workspace.yaml', '.gitignore')
        testenv.sh(self.ws, 'git', 'commit', '-q', '-m', 'workspace')
        testenv.sh(self.ws, 'git', 'push', '-q', '-u', 'origin', 'main')
        self.real = Path(os.path.realpath(self.ws))

    def tearDown(self):
        self.tmp.cleanup()

    def stop(self, *wrote, **extra):
        lines = [w if isinstance(w, dict) else ('wrote', self.real / w) for w in wrote]
        data = {'cwd': str(self.ws), 'session_id': 'c1', 'transcript_path': testenv.transcript(Path(self.tmp.name) / 't.jsonl', *lines), **extra}
        return hooks.sync_gate(data)


class StopGate(Case):
    def test_nothing_written_by_the_session_means_nothing_to_settle(self):
        (self.ws / 'someone-elses.md').write_text('x\n')
        self.assertIsNone(self.stop())

    def test_a_file_the_session_wrote_and_left_uncommitted_blocks_once(self):
        (self.ws / 'a.md').write_text('x\n')
        found = self.stop('a.md')
        self.assertIn('a.md', found['block'])
        self.assertIn('not committed', found['block'])
        self.assertIsNone(self.stop('a.md', stop_hook_active=True))

    def test_committed_but_not_on_origin_blocks_and_pushed_does_not(self):
        (self.ws / 'a.md').write_text('x\n')
        testenv.sh(self.ws, 'git', 'add', 'a.md')
        testenv.sh(self.ws, 'git', 'commit', '-q', '-m', 'a')
        self.assertIn('not on origin', self.stop('a.md')['block'])
        testenv.sh(self.ws, 'git', 'push', '-q', 'origin', 'main')
        testenv.sh(self.ws, 'git', 'fetch', '-q')
        self.assertIsNone(self.stop('a.md'))

    def test_a_tracked_file_the_session_changed_is_seen_like_a_new_one(self):
        (self.ws / 'workspace.yaml').write_text((self.ws / 'workspace.yaml').read_text() + '# a note\n')
        self.assertIn('workspace.yaml', self.stop('workspace.yaml')['block'])

    def test_another_sessions_dirty_file_is_not_this_sessions_to_commit(self):
        (self.ws / 'a.md').write_text('x\n')
        (self.ws / 'theirs.md').write_text('y\n')
        self.assertNotIn('theirs.md', self.stop('a.md')['block'])

    def test_a_spawned_worker_is_logged_and_never_blocked(self):
        (self.ws / 'a.md').write_text('x\n')
        self.assertIsNone(self.stop('a.md', permission_mode='bypassPermissions'))
        self.assertIn('"would_block": true', (self.ws / '.trampo/state/hook-log.jsonl').read_text())

    def test_the_ledger_the_hooks_append_is_not_the_sessions_to_settle(self):
        (self.ws / 'telemetry/events').mkdir(parents=True)
        (self.ws / 'telemetry/events/s1.jsonl').write_text('{}\n')
        self.assertIsNone(self.stop('telemetry/events/s1.jsonl'))

    def ran(self, cmd):
        return {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': 'Bash', 'input': {'command': cmd}}]}}

    def opened(self):
        with contextlib.redirect_stdout(io.StringIO()):
            event.main(['open', '--ws', str(self.ws), '--kind', 'adhoc', '--subject', 'site-plan', '--session', 'c1'])
        return common.active(self.ws, 'c1')[0]

    def shared(self):
        testenv.sh(self.ws, 'git', 'add', 'telemetry')
        testenv.sh(self.ws, 'git', 'commit', '-q', '-m', 'ledger')
        testenv.sh(self.ws, 'git', 'push', '-q', 'origin', 'main')
        testenv.sh(self.ws, 'git', 'fetch', '-q')

    def test_the_sessions_own_ledger_is_settled_with_its_files_and_named_as_the_ledger(self):
        sid = self.opened()
        self.assertIn(f"telemetry/events/{sid}.jsonl (this session's ledger)", self.stop()['block'])
        with contextlib.redirect_stdout(io.StringIO()):
            event.main(['close', '--ws', str(self.ws), '--outcome', 'no-action', '--session', 'c1'])
        self.assertIsNone(common.active(self.ws, 'c1'))
        self.assertIn(f'telemetry/events/{sid}.jsonl', self.stop()['block'])
        testenv.sh(self.ws, 'git', 'add', 'telemetry')
        testenv.sh(self.ws, 'git', 'commit', '-q', '-m', 'ledger')
        self.assertIn('not on origin', self.stop()['block'])
        testenv.sh(self.ws, 'git', 'push', '-q', 'origin', 'main')
        testenv.sh(self.ws, 'git', 'fetch', '-q')
        self.assertIsNone(self.stop())

    def test_a_ledger_whose_only_unshared_lines_are_prompt_counts_waits_for_the_next_write(self):
        sid = self.opened()
        self.stop()
        self.shared()
        common.append(self.ws, sid, {'ev': 'touch'})
        self.assertIsNone(self.stop())
        common.append(self.ws, sid, {'ev': 'note', 'text': 'the plan changed'})
        self.assertIn('ledger', self.stop()['block'])

    def test_another_sessions_ledger_is_not_this_sessions(self):
        (self.ws / 'telemetry/events').mkdir(parents=True)
        (self.ws / 'telemetry/events/someone-20260105T0900.jsonl').write_text('{"ev": "start"}\n')
        self.assertIsNone(self.stop())

    def test_a_file_a_shell_command_wrote_is_the_sessions_and_one_it_only_read_is_not(self):
        (self.ws / 'notes').mkdir()
        (self.ws / 'notes/plan.md').write_text('x\n')
        (self.ws / 'other.md').write_text('x\n')
        found = self.stop(self.ran("printf 'x' > notes/plan.md"), self.ran('cat other.md'))
        self.assertIn('notes/plan.md (written by a shell command)', found['block'])
        self.assertNotIn('other.md', found['block'])

    def test_a_shared_folder_has_no_commit_to_wait_for(self):
        files = testenv.workspace(Path(self.tmp.name) / 'files', 'files')
        (files / 'a.md').write_text('x\n')
        data = {'cwd': str(files), 'transcript_path': testenv.transcript(Path(self.tmp.name) / 'f.jsonl', ('wrote', Path(os.path.realpath(files)) / 'a.md'))}
        self.assertIsNone(hooks.sync_gate(data))

    def test_a_check_set_to_log_records_and_lets_through(self):
        (self.ws / 'workspace.yaml').write_text((self.ws / 'workspace.yaml').read_text() + 'hooks:\n  sync-gate: log\n')
        testenv.sh(self.ws, 'git', 'commit', '-q', '-am', 'log first')
        testenv.sh(self.ws, 'git', 'push', '-q', 'origin', 'main')
        testenv.sh(self.ws, 'git', 'fetch', '-q')
        (self.ws / 'a.md').write_text('x\n')
        self.assertIsNone(self.stop('a.md'))

    def test_the_registered_stop_hook_prints_a_block_decision(self):
        (self.ws / 'a.md').write_text('x\n')
        data = {'hook_event_name': 'Stop', 'cwd': str(self.ws), 'session_id': 'c1',
                'transcript_path': testenv.transcript(Path(self.tmp.name) / 't.jsonl', ('wrote', self.real / 'a.md'))}
        ran = wiring.fire('Stop', data)
        self.assertEqual({status for status, _, _ in ran}, {0})
        (out,) = [out for _, out, _ in ran if out.strip()]
        self.assertEqual(json.loads(out)['decision'], 'block')


class Start(Case):
    def start(self, **extra):
        spawned = []
        with mock.patch.object(hooks, 'detach', side_effect=lambda argv, log: spawned.append(argv)):
            return hooks.start({'cwd': str(self.ws), **extra}), spawned

    def test_it_installs_git_hooks_and_starts_a_detached_sync(self):
        said, spawned = self.start()
        self.assertIsNone(said)
        self.assertTrue((self.ws / '.git/hooks/pre-push').exists())
        self.assertTrue((self.ws / '.git/hooks/prepare-commit-msg').exists())
        self.assertEqual(spawned[0][-1], '--session')
        self.assertTrue(spawned[0][-3].endswith('sync.py'))

    def test_the_hook_it_installs_names_the_transcript_folder_the_runtime_gave_not_the_environments(self):
        given = Path(self.tmp.name) / 'runtime' / 'projects'
        with mock.patch.dict(os.environ, {'CLAUDE_CONFIG_DIR': str(Path(self.tmp.name) / 'forged')}):
            self.start(transcript_path=str(given / '-ws' / 'c1.jsonl'))
        stub = (self.ws / '.git/hooks/pre-push').read_text()
        self.assertIn(f'TRANSCRIPTS = {str(given)!r}', stub)
        self.assertNotIn('forged', stub)

    def test_a_spawned_worker_does_not_sync(self):
        self.assertEqual(self.start(permission_mode='bypassPermissions')[1], [])

    def test_stranded_commits_are_said_at_the_start(self):
        (self.ws / '.git/trampo-sync-stranded.txt').write_text('abc123 my change\n')
        said, _ = self.start()
        self.assertIn('1 local commit', said['say'])
        self.assertIn('tell the person', said['say'])

    def test_a_linked_worktree_is_left_alone(self):
        wt = Path(self.tmp.name) / 'wt'
        testenv.sh(self.ws, 'git', 'worktree', 'add', '-q', str(wt), '-b', 'side')
        self.assertEqual(hooks.start({'cwd': str(wt)}), None)
        self.assertFalse((wt / '.git').is_dir())

    def test_the_registered_start_hook_runs_and_never_blocks(self):
        ran = wiring.fire('SessionStart', {'hook_event_name': 'SessionStart', 'cwd': str(self.ws), 'source': 'startup',
                                           'permission_mode': 'bypassPermissions'}, 'startup')
        self.assertEqual([status for status, _, _ in ran], [0, 0])


if __name__ == '__main__':
    unittest.main()
