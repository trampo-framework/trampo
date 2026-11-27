#!/usr/bin/env python3
"""The boundary: git's own pre-push hook. It refuses a push to the team branch that changes a control file with no
approver's name on the commit, or adds a claim about live state with no date and re-check, and it refuses when it
cannot tell."""
import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import testenv  # noqa: E402
import approval  # noqa: E402
import common  # noqa: E402
import prepush  # noqa: E402

STAMPED = '## The export job is enabled\n\nAs of 2026-01-05 (session c1); re-check: crontab -l\n**How to apply:** check before relying on it.\n'


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = testenv.workspace(Path(self.tmp.name) / 'ws')
        self.origin = Path(self.tmp.name) / 'origin.git'
        testenv.sh(self.tmp.name, 'git', 'init', '-q', '--bare', '-b', 'main', str(self.origin))
        testenv.sh(self.ws, 'git', 'remote', 'add', 'origin', str(self.origin))
        self.commit('workspace', 'workspace.yaml', None)
        prepush.install(self.ws)
        self.assertEqual(self.push().returncode, 0)

    def tearDown(self):
        self.tmp.cleanup()

    def commit(self, message, rel, text):
        if text is not None:
            (self.ws / rel).parent.mkdir(parents=True, exist_ok=True)
            (self.ws / rel).write_text(text)
        testenv.sh(self.ws, 'git', 'add', rel)
        testenv.sh(self.ws, 'git', 'commit', '-q', '-m', message)

    def push(self, **env):
        return subprocess.run(['git', '-C', str(self.ws), 'push', '-q', 'origin', 'main'], capture_output=True, text=True,
                              env={**os.environ, **env})

    def approve(self, label, by='Robin Vale', text=None, **change):
        """An approve line as the gate hook writes it, committed with the ledger. Returns the trailer to put on a commit."""
        text = text or f'yes, change {label}'
        self.sittings = getattr(self, 'sittings', 0) + 1
        sitting = f'{Path(self.tmp.name).name}-{self.sittings}'
        self.said = Path(testenv.sitting(self.ws, sitting, ('human', text)))
        line = {'ev': 'approve', 'gate': 'control file', 'by': by, 'via': 'typed', 'key': label, 'msg_sha': approval.sha(text),
                'sitting': sitting, **change}
        e = common.append(self.ws, 's1', {k: v for k, v in line.items() if v is not None})
        self.commit('ledger', 'telemetry/events/s1.jsonl', None)
        return f"Approved-by: {by} {e['event_id']}"

    def more_approvers(self):
        return (self.ws / 'workspace.yaml').read_text().replace('  - Robin Vale', '  - Robin Vale\n  - Sam Okoro')


class ControlFiles(Case):
    def test_ordinary_work_and_working_instructions_push_without_ceremony(self):
        self.commit('session: notes', 'sessions/refund-letter/session.md', 'notes\n')
        self.commit('evolve: card mode asks for the amount first', 'modes/card.md', 'ask for the amount first\n')
        self.assertEqual(self.push().returncode, 0)

    def test_a_control_file_change_needs_an_approvers_name_and_the_record_of_their_yes(self):
        self.commit('add an approver', 'workspace.yaml', self.more_approvers())
        r = self.push()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('Approved-by', r.stderr)
        self.assertIn('workspace.yaml', r.stderr)
        testenv.sh(self.ws, 'git', 'reset', '-q', '--hard', 'origin/main')
        trailer = self.approve('workspace.yaml')
        self.commit(f'add an approver\n\n{trailer}', 'workspace.yaml', self.more_approvers())
        self.assertEqual(self.push().returncode, 0)

    def test_the_name_must_be_an_approver_in_the_teams_copy_not_one_this_push_adds(self):
        trailer = self.approve('workspace.yaml', by='Sam Okoro')
        self.commit(f'add an approver\n\n{trailer}', 'workspace.yaml', self.more_approvers())
        r = self.push()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('Robin Vale', r.stderr)

    def test_a_name_with_no_reference_or_a_reference_to_nothing_is_not_a_recorded_yes(self):
        self.commit('grants\n\nApproved-by: Robin Vale', 'memory/shared/grants.md', '# Standing grants\n')
        self.assertNotEqual(self.push().returncode, 0)
        testenv.sh(self.ws, 'git', 'commit', '-q', '--amend', '-m', 'grants\n\nApproved-by: Robin Vale session c1')
        r = self.push()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('no approve record', r.stderr)

    def test_a_record_that_is_not_the_gate_hooks_is_not_a_yes(self):
        for change, word in (({'msg_sha': None}, 'typed message'), ({'msg_sha': approval.sha('hello')}, 'typed message'),
                             ({'key': 'constitution.md'}, 'constitution.md'), ({'gate': 'send to client'}, 'control file'),
                             ({'via': 'grant'}, 'typed')):
            trailer = self.approve('workspace.yaml', **change)
            self.commit(f'add an approver\n\n{trailer}', 'workspace.yaml', self.more_approvers())
            r = self.push()
            self.assertNotEqual(r.returncode, 0, change)
            self.assertIn(word, r.stderr, change)
            testenv.sh(self.ws, 'git', 'reset', '-q', '--hard', 'origin/main')

    def test_one_trailered_commit_does_not_cover_another_commit_with_a_control_change(self):
        self.commit('add an approver', 'workspace.yaml', self.more_approvers())
        trailer = self.approve('constitution.md')
        self.commit(f'the constitution\n\n{trailer}', 'constitution.md', 'rules\n')
        r = self.push()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('workspace.yaml', r.stderr)

    def test_a_record_new_to_the_teams_copy_needs_its_transcript_on_this_machine(self):
        trailer = self.approve('workspace.yaml')
        self.said.unlink()
        self.commit(f'add an approver\n\n{trailer}', 'workspace.yaml', self.more_approvers())
        r = self.push()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('transcript', r.stderr)

    def test_a_record_with_no_transcript_cannot_be_parked_on_the_teams_copy_first(self):
        self.approve('workspace.yaml')
        self.said.unlink()
        r = self.push()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('transcript', r.stderr)

    def test_a_record_the_teams_copy_already_holds_stands_on_a_machine_without_the_transcript(self):
        trailer = self.approve('workspace.yaml')
        self.assertEqual(self.push().returncode, 0)
        self.said.unlink()
        self.commit(f'add an approver\n\n{trailer}', 'workspace.yaml', self.more_approvers())
        self.assertEqual(self.push().returncode, 0)

    def test_the_environment_of_a_push_does_not_choose_where_transcripts_are_read(self):
        forged = Path(self.tmp.name) / 'forged'
        with mock.patch.dict(os.environ, {'CLAUDE_CONFIG_DIR': str(forged)}):
            trailer = self.approve('workspace.yaml')
        self.commit(f'add an approver\n\n{trailer}', 'workspace.yaml', self.more_approvers())
        r = self.push(CLAUDE_CONFIG_DIR=str(forged))
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('transcript', r.stderr)

    def test_the_folder_is_the_one_named_when_the_hook_was_installed(self):
        moved = Path(self.tmp.name) / 'moved'
        with mock.patch.dict(os.environ, {'CLAUDE_CONFIG_DIR': str(moved)}):
            prepush.install(self.ws)
            trailer = self.approve('workspace.yaml')
        self.commit(f'add an approver\n\n{trailer}', 'workspace.yaml', self.more_approvers())
        self.assertEqual(self.push().returncode, 0)

    def test_inside_a_session_the_installer_takes_the_folder_only_from_the_start_step(self):
        stub = self.ws / '.git/hooks/pre-push'
        for marker in ('CLAUDECODE', 'CLAUDE_CODE_SESSION_ID'):
            before = stub.read_text()
            with mock.patch.dict(os.environ, {marker: '1', 'CLAUDE_CONFIG_DIR': str(Path(self.tmp.name) / 'forged')}):
                with self.assertRaises(prepush.CannotTell, msg=marker):
                    prepush.install(self.ws)
                self.assertEqual(stub.read_text(), before)
                prepush.install(self.ws, Path(self.tmp.name) / 'given')
                self.assertIn('given', stub.read_text())
                self.assertNotIn('forged', stub.read_text())

    def test_a_hook_that_names_no_folder_refuses_a_record_it_must_read(self):
        hook = self.ws / '.git/hooks/pre-push'
        hook.write_text(''.join(l for l in hook.read_text().splitlines(True) if 'TRANSCRIPTS' not in l))
        self.commit('notes', 'notes.md', 'x\n')
        self.assertEqual(self.push().returncode, 0)
        trailer = self.approve('workspace.yaml')
        self.commit(f'add an approver\n\n{trailer}', 'workspace.yaml', self.more_approvers())
        r = self.push()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('install', r.stderr)

    def test_a_record_the_teams_copy_holds_cannot_be_rewritten_in_a_push(self):
        self.approve('workspace.yaml')
        self.assertEqual(self.push().returncode, 0)
        self.said.unlink()
        ledger = self.ws / 'telemetry/events/s1.jsonl'
        self.commit('ledger', 'telemetry/events/s1.jsonl', ledger.read_text().replace('"key": "workspace.yaml"', '"key": "slots"'))
        self.assertNotEqual(self.push().returncode, 0)

    def test_one_record_covers_one_commit(self):
        trailer = self.approve('workspace.yaml')
        self.commit(f'add an approver\n\n{trailer}', 'workspace.yaml', self.more_approvers())
        self.assertEqual(self.push().returncode, 0)
        self.commit(f'another\n\n{trailer}', 'workspace.yaml', self.more_approvers().replace('Sam Okoro', 'Ira Moss'))
        r = self.push()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('already stood', r.stderr)

    def test_one_record_cited_by_two_commits_of_one_push_covers_the_first_only(self):
        trailer = self.approve('workspace.yaml')
        self.commit(f'add an approver\n\n{trailer}', 'workspace.yaml', self.more_approvers())
        self.commit(f'another\n\n{trailer}', 'workspace.yaml', self.more_approvers().replace('Sam Okoro', 'Ira Moss'))
        r = self.push()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('already stood', r.stderr)

    def merge_changing_the_approvers(self, message):
        testenv.sh(self.ws, 'git', 'checkout', '-q', '-B', 'side', 'origin/main')
        self.commit('side work', 'notes.md', 'x\n')
        testenv.sh(self.ws, 'git', 'checkout', '-q', 'main')
        self.commit('main work', 'other.md', 'y\n')
        testenv.sh(self.ws, 'git', 'merge', '-q', '--no-commit', '--no-ff', 'side')
        (self.ws / 'workspace.yaml').write_text(self.more_approvers())
        testenv.sh(self.ws, 'git', 'add', 'workspace.yaml')
        testenv.sh(self.ws, 'git', 'commit', '-q', '-m', message)

    def test_a_merge_that_changes_a_control_file_itself_needs_its_own_trailer(self):
        self.merge_changing_the_approvers('merge side')
        r = self.push()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('merge commit', r.stderr)
        testenv.sh(self.ws, 'git', 'reset', '-q', '--hard', 'origin/main')
        trailer = self.approve('workspace.yaml')
        self.merge_changing_the_approvers(f'merge side\n\n{trailer}')
        self.assertEqual(self.push().returncode, 0)

    def test_a_clean_merge_of_commits_that_carry_their_own_trailers_passes(self):
        testenv.sh(self.ws, 'git', 'checkout', '-q', '-b', 'side')
        trailer = self.approve('workspace.yaml')
        self.commit(f'add an approver\n\n{trailer}', 'workspace.yaml', self.more_approvers())
        testenv.sh(self.ws, 'git', 'checkout', '-q', 'main')
        self.commit('main work', 'other.md', 'y\n')
        testenv.sh(self.ws, 'git', 'merge', '-q', '--no-ff', '-m', 'merge side', 'side')
        self.assertEqual(self.push().returncode, 0)


class Memory(Case):
    def test_a_new_claim_about_live_state_needs_its_date_and_recheck(self):
        self.commit('memory', 'memory/shared/tooling.md', STAMPED.replace('As of 2026-01-05 (session c1); re-check: crontab -l\n', ''))
        r = self.push()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('re-check', r.stderr)
        self.commit('memory', 'memory/shared/tooling.md', STAMPED)
        self.assertEqual(self.push().returncode, 0)


class Trailer(Case):
    def last_message(self):
        return testenv.sh(self.ws, 'git', 'log', '-1', '--format=%B')

    def test_a_commit_made_from_a_session_names_it_and_one_typed_by_hand_does_not(self):
        import event
        with contextlib.redirect_stdout(io.StringIO()):
            event.main(['open', '--ws', str(self.ws), '--kind', 'card', '--subject', 'refund-letter', '--session', 'c1'])
        self.commit('by hand', 'a.md', 'a\n')
        self.assertNotIn('Session:', self.last_message())
        with mock.patch.dict(os.environ, {'CLAUDE_CODE_SESSION_ID': 'c1'}):
            self.commit('from a session', 'b.md', 'b\n')
        self.assertRegex(self.last_message(), r'Session: refund-letter-\S+ card')


class Boundary(Case):
    def test_it_refuses_when_it_cannot_tell(self):
        with mock.patch('sys.stdin', io.StringIO('refs/heads/main nonsense refs/heads/main nonsense\n')), \
                mock.patch('sys.stderr', io.StringIO()) as err, contextlib.chdir(self.ws):
            self.assertEqual(prepush.main(['run', str(self.ws), 'origin']), 1)
        self.assertIn('could not', err.getvalue())

    def test_other_branches_are_not_its_business(self):
        testenv.sh(self.ws, 'git', 'checkout', '-q', '-b', 'draft')
        self.commit('draft', 'workspace.yaml', self.more_approvers())
        r = subprocess.run(['git', '-C', str(self.ws), 'push', '-q', 'origin', 'draft'], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)

    def test_a_check_set_to_log_in_the_teams_copy_lets_through_and_a_local_edit_does_not_switch_it_off(self):
        self.commit('off locally', 'workspace.yaml', (self.ws / 'workspace.yaml').read_text() + 'hooks:\n  prepush: off\n')
        self.assertNotEqual(self.push().returncode, 0)

    def test_installing_keeps_a_hook_that_was_there_and_runs_it_after(self):
        hook = self.ws / '.git' / 'hooks' / 'pre-push'
        hook.write_text('#!/bin/sh\necho theirs >&2\nexit 1\n')
        hook.chmod(0o755)
        prepush.install(self.ws)
        prepush.install(self.ws)
        self.assertIn('theirs', (hook.parent / 'pre-push.next').read_text())
        self.commit('notes', 'notes.md', 'x\n')
        r = self.push()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('theirs', r.stderr)


class AdoptedCommit(Case):
    """A control-file commit made by hand, outside any session, is approved afterwards by an approver naming it."""

    def setUp(self):
        super().setUp()
        import contextlib, io, event
        self.commit('add an approver by hand', 'workspace.yaml', (self.ws / 'workspace.yaml').read_text() + 'caps:\n  file_words: 900\n')
        self.full = testenv.sh(self.ws, 'git', 'rev-parse', 'HEAD')
        self.short = self.full[:8]
        self.sitting = f'{Path(self.tmp.name).name}-adopt'
        with contextlib.redirect_stdout(io.StringIO()):
            event.main(['open', '--ws', str(self.ws), '--kind', 'adhoc', '--subject', 'tidy-up', '--session', self.sitting])
        self.sid = common.active(self.ws, self.sitting)[0]

    def adopt(self, *said, who='Robin Vale', commit=None):
        import hooks
        data = {'tool_name': 'Bash', 'tool_input': {'command': f'python3 core/scripts/prepush.py adopt . {commit or self.short}'},
                'cwd': str(self.ws), 'session_id': self.sitting, 'transcript_path': testenv.sitting(self.ws, self.sitting, *said)}
        testenv.sh(self.ws, 'git', 'config', 'user.name', who)
        try:
            return hooks.gate_why(data)
        finally:
            testenv.sh(self.ws, 'git', 'config', 'user.name', 'Robin Vale')

    def records(self):
        return [e for e in common.session_events(self.ws, self.sid) if e.get('gate') == 'control commit']

    def share(self):
        self.commit('ledger', f'telemetry/events/{self.sid}.jsonl', None)
        return self.push()

    def test_the_hand_made_commit_blocks_the_push_until_an_approver_names_it_in_a_session(self):
        self.assertIn('carries no "Approved-by', self.push().stderr)
        self.assertIsNone(self.adopt(('human', f'Yes, I approve commit {self.short}.')))
        self.assertEqual([e['commit'] for e in self.records()], [self.full])
        self.assertEqual(prepush.main(['adopt', str(self.ws), self.short]), 0)
        r = self.share()
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_nothing_is_recorded_without_the_approvers_own_yes_naming_that_commit(self):
        self.assertIn('needs a yes', self.adopt(('human', 'please sort out that push')))
        self.assertIn('needs a yes', self.adopt(('human', 'Yes, I approve commit 0123abcd.')))
        self.assertIn('not an approver', self.adopt(('human', f'Yes, I approve commit {self.short}.'), who='Sam Okoro'))
        self.assertEqual(self.records(), [])
        self.assertEqual(prepush.main(['adopt', str(self.ws), self.short]), 1)
        self.assertNotEqual(self.share().returncode, 0)

    def test_the_yes_covers_that_one_commit_and_only_a_commit_that_changes_a_control_file(self):
        self.assertIsNone(self.adopt(('human', f'Yes, I approve commit {self.short}.')))
        self.commit('another by hand', 'workspace.yaml', (self.ws / 'workspace.yaml').read_text() + '  memory_lines: 300\n')
        r = self.share()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn(testenv.sh(self.ws, 'git', 'rev-parse', 'HEAD~1')[:10], r.stderr)
        self.commit('notes', 'notes.md', 'x\n')
        plain = testenv.sh(self.ws, 'git', 'rev-parse', 'HEAD')[:8]
        self.assertIn('changes no control file', self.adopt(('human', f'Yes, I approve commit {plain}.'), commit=plain))

    def test_a_record_a_session_wrote_for_itself_is_not_a_yes(self):
        common.append(self.ws, self.sid, {'ev': 'approve', 'gate': 'control commit', 'by': 'Robin Vale', 'via': 'typed',
                                          'key': self.short, 'commit': self.full, 'sitting': self.sitting,
                                          'msg_sha': approval.sha('yes, I approve it')})
        self.assertNotEqual(self.share().returncode, 0)


class MachineWideHooks(unittest.TestCase):
    """A machine whose git config points every repository at one hooks folder: nothing of ours goes in there."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        top = Path(self.tmp.name)
        self.shared, self.log = top / 'machine-hooks', top / 'ran.log'
        self.shared.mkdir()
        self.hook('pre-push', f'#!/bin/sh\necho "machine pre-push $@" >> {self.log}\ncat >> {self.log}\nexit 0\n')
        self.hook('prepare-commit-msg', f'#!/bin/sh\necho "machine prepare $(basename $1)" >> {self.log}\nexit 0\n')
        self.conf = top / 'gitconfig'
        self.point_at(self.shared)
        self.env = mock.patch.dict(os.environ, {'GIT_CONFIG_GLOBAL': str(self.conf)})
        self.env.start()
        self.ws = testenv.workspace(top / 'ws')
        self.origin = top / 'origin.git'
        testenv.sh(top, 'git', 'init', '-q', '--bare', '-b', 'main', str(self.origin))
        testenv.sh(self.ws, 'git', 'remote', 'add', 'origin', str(self.origin))
        self.own = self.ws / '.git' / 'hooks'

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def hook(self, name, text, folder=None):
        f = (folder or self.shared) / name
        f.write_text(text)
        f.chmod(0o755)

    def point_at(self, folder):
        self.conf.write_text('[user]\n\tname = Robin Vale\n\temail = test@example.invalid\n'
                             + (f'[core]\n\thooksPath = {folder}\n' if folder else ''))

    def snapshot(self, folder=None):
        return {f.name: (f.read_bytes(), f.stat().st_mode) for f in sorted((folder or self.shared).iterdir())}

    def commit_and_push(self):
        notes = self.ws / 'notes.md'
        notes.write_text((notes.read_text() if notes.exists() else '') + 'x\n')
        testenv.sh(self.ws, 'git', 'add', 'notes.md', 'workspace.yaml')
        testenv.sh(self.ws, 'git', 'commit', '-q', '-m', 'notes')
        return subprocess.run(['git', '-C', str(self.ws), 'push', '-q', 'origin', 'main'], capture_output=True, text=True)

    def local_path(self):
        r = subprocess.run(['git', '-C', str(self.ws), 'config', '--local', '--get', 'core.hooksPath'], capture_output=True, text=True)
        return r.stdout.strip()

    def test_a_machine_wide_hooks_folder_is_left_byte_for_byte_as_it_was(self):
        self.hook('pre-commit', f'#!/bin/sh\necho "machine pre-commit" >> {self.log}\n')
        self.hook('post-merge', f'#!/bin/sh\necho "machine post-merge $1" >> {self.log}\n')
        before = self.snapshot()
        prepush.install(self.ws)
        prepush.install(self.ws)
        self.commit_and_push()
        self.assertEqual(self.snapshot(), before)

    def test_the_machines_pre_commit_runs_for_a_commit_in_the_workspace_and_its_refusal_stops_the_commit(self):
        self.hook('pre-commit', f'#!/bin/sh\necho "machine pre-commit" >> {self.log}\n')
        prepush.install(self.ws)
        self.assertEqual(self.commit_and_push().returncode, 0)
        self.assertIn('machine pre-commit', self.log.read_text())
        self.hook('pre-commit', '#!/bin/sh\necho "the machine says no to this commit" >&2\nexit 3\n')
        (self.ws / 'notes.md').write_text('more\n')
        r = subprocess.run(['git', '-C', str(self.ws), 'commit', '-q', '-m', 'more', '--', 'notes.md'], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('the machine says no to this commit', r.stderr)
        self.assertNotIn('more', testenv.sh(self.ws, 'git', 'log', '-1', '--format=%s'))

    def test_the_machines_post_merge_runs_for_a_merge_in_the_workspace(self):
        self.hook('post-merge', f'#!/bin/sh\necho "machine post-merge $1" >> {self.log}\n')
        prepush.install(self.ws)
        self.commit_and_push()
        testenv.sh(self.ws, 'git', 'checkout', '-q', '-b', 'side')
        self.commit_and_push()
        testenv.sh(self.ws, 'git', 'checkout', '-q', 'main')
        testenv.sh(self.ws, 'git', 'merge', '-q', '--no-ff', '-m', 'merge side', 'side')
        self.assertIn('machine post-merge 0', self.log.read_text())

    def test_installing_again_follows_the_machines_folder_and_only_real_hooks_get_a_stub(self):
        prepush.install(self.ws)
        self.assertFalse((self.own / 'pre-commit').exists())
        self.hook('pre-commit', '#!/bin/sh\nexit 0\n')
        for other in ('pre-commit.local', 'pre-commit.next', 'post-merge.trampo', 'helper.sh', 'commit-msg~'):
            self.hook(other, '#!/bin/sh\nexit 0\n')
        (self.shared / 'commit-msg').write_text('#!/bin/sh\nexit 0\n')
        self.hook('post-commit', f'#!/bin/sh\n# {prepush.MARK}\nexit 0\n')
        before = self.snapshot()
        prepush.install(self.ws)
        ours = sorted(f.name for f in self.own.iterdir() if prepush.PASS in f.read_text(errors='replace'))
        self.assertEqual(ours, ['pre-commit'])
        first = (self.own / 'pre-commit').read_bytes()
        prepush.install(self.ws)
        self.assertEqual((self.own / 'pre-commit').read_bytes(), first)
        self.assertEqual(self.snapshot(), before)
        (self.shared / 'pre-commit').unlink()
        prepush.install(self.ws)
        self.assertFalse((self.own / 'pre-commit').exists())

    def test_a_hook_a_person_put_in_the_repository_is_kept_and_the_install_says_so(self):
        self.own.mkdir(parents=True, exist_ok=True)
        mine = self.own / 'pre-commit'
        mine.write_text(f'#!/bin/sh\necho "my own pre-commit" >> {self.log}\n')
        mine.chmod(0o755)
        self.hook('pre-commit', f'#!/bin/sh\necho "machine pre-commit" >> {self.log}\n')
        kept = []
        prepush.install(self.ws, kept=kept)
        self.assertEqual(kept, ['pre-commit'])
        self.assertIn('my own pre-commit', mine.read_text())
        self.commit_and_push()
        self.assertIn('my own pre-commit', self.log.read_text())
        self.assertNotIn('machine pre-commit', self.log.read_text())

    def test_a_session_does_not_write_a_stub_that_passes_on_to_the_machines_hook(self):
        import hooks
        self.hook('pre-commit', '#!/bin/sh\nexit 0\n')
        prepush.install(self.ws)
        self.assertTrue(hooks.stub_why(self.ws, None, str(self.own / 'pre-commit'), str(self.ws)))
        self.assertTrue(hooks.stub_why(self.ws, 'echo x > .git/hooks/pre-commit', None, str(self.ws)))
        self.assertIsNone(hooks.stub_why(self.ws, 'cat .git/hooks/pre-commit', None, str(self.ws)))
        self.assertIsNone(hooks.stub_why(self.ws, None, str(self.own / 'post-commit'), str(self.ws)))

    def test_the_hooks_go_into_the_repository_and_git_runs_them_for_this_repository_only(self):
        where = prepush.install(self.ws)
        self.assertEqual(os.path.realpath(where), os.path.realpath(self.own / 'pre-push'))
        for name in prepush.STUBS:
            self.assertIn(prepush.MARK, (self.own / name).read_text())
        self.assertEqual(os.path.realpath(self.local_path()), os.path.realpath(self.own))
        other = testenv.workspace(Path(self.tmp.name) / 'unrelated')
        self.assertEqual(os.path.realpath(testenv.sh(other, 'git', 'rev-parse', '--git-path', 'hooks')), os.path.realpath(self.shared))

    def test_the_machines_own_hooks_still_run_for_this_repository_with_the_same_arguments_and_input(self):
        prepush.install(self.ws)
        self.assertEqual(self.commit_and_push().returncode, 0)
        ran = self.log.read_text()
        self.assertIn('machine prepare COMMIT_EDITMSG', ran)
        self.assertIn(f'machine pre-push origin {self.origin}', ran)
        self.assertRegex(ran, r'refs/heads/main [0-9a-f]{40} refs/heads/main [0-9a-f]{40}')
        self.hook('pre-push', '#!/bin/sh\necho "the machine says no" >&2\nexit 7\n')
        r = self.commit_and_push()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('the machine says no', r.stderr)

    def test_a_hooks_path_a_person_set_in_the_repository_is_not_replaced(self):
        theirs = self.ws / '.githooks'
        theirs.mkdir()
        testenv.sh(self.ws, 'git', 'config', '--local', 'core.hooksPath', '.githooks')
        with self.assertRaises(prepush.CannotTell) as refused:
            prepush.install(self.ws)
        self.assertIn('core.hooksPath', str(refused.exception))
        self.assertIn('git config --local --unset core.hooksPath', str(refused.exception))
        self.assertEqual(self.local_path(), '.githooks')
        self.assertEqual(list(theirs.iterdir()), [])
        self.assertFalse((self.own / 'pre-push').exists() and prepush.MARK in (self.own / 'pre-push').read_text())

    def test_installing_again_reads_where_the_machines_hooks_are_now(self):
        prepush.install(self.ws)
        moved = Path(self.tmp.name) / 'moved-hooks'
        moved.mkdir()
        self.hook('pre-push', f'#!/bin/sh\necho "moved pre-push" >> {self.log}\n', moved)
        self.point_at(moved)
        prepush.install(self.ws)
        self.commit_and_push()
        self.assertIn('moved pre-push', self.log.read_text())
        self.assertNotIn('machine pre-push', self.log.read_text())
        self.point_at(None)
        self.log.write_text('')
        prepush.install(self.ws)
        self.assertEqual(self.commit_and_push().returncode, 0)
        self.assertEqual(self.log.read_text(), '')

    def test_a_stub_of_ours_left_in_the_machines_folder_is_never_run_from_the_repository(self):
        prepush.install(self.ws)
        self.hook('pre-push', (self.own / 'pre-push').read_text())
        self.assertEqual(self.commit_and_push().returncode, 0)

    def test_a_linked_worktree_runs_the_same_stubs_and_the_guard_covers_every_folder_they_run_from(self):
        prepush.install(self.ws)
        tree = Path(self.tmp.name) / 'tree'
        testenv.sh(self.ws, 'git', 'worktree', 'add', '-q', '-b', 'side', str(tree))
        self.assertEqual(os.path.realpath(testenv.sh(tree, 'git', 'rev-parse', '--git-path', 'hooks')), os.path.realpath(self.own))
        (tree / 'side.md').write_text('x\n')
        testenv.sh(tree, 'git', 'add', 'side.md')
        testenv.sh(tree, 'git', 'commit', '-q', '-m', 'side')
        self.assertIn('machine prepare COMMIT_EDITMSG', self.log.read_text())
        self.assertEqual(os.path.realpath(prepush.hooks_dir(tree)), os.path.realpath(self.own))
        self.assertEqual({os.path.realpath(f) for f in prepush.guarded(self.ws)},
                         {os.path.realpath(self.own), os.path.realpath(self.shared)})

    def test_the_health_check_warns_about_a_stub_outside_the_repository_and_says_how_to_put_the_old_hook_back(self):
        import doctor
        stub = f'#!/usr/bin/env python3\n# {prepush.MARK}: installed by prepush.py install; edit nothing here\n'
        for name in prepush.STUBS:
            (self.shared / name).rename(self.shared / f'{name}.next')
            self.hook(name, stub)
        before = self.snapshot()
        warns = [w for w in doctor.check(self.ws)[1] if 'hooks folder outside' in w]
        self.assertEqual(len(warns), 1, doctor.check(self.ws))
        for name in prepush.STUBS:
            self.assertIn(f'mv {self.shared}/{name}.next {self.shared}/{name}', warns[0])
        self.assertEqual(self.snapshot(), before)
        for name in prepush.STUBS:
            (self.shared / name).unlink()
            (self.shared / f'{name}.next').rename(self.shared / name)
        self.assertEqual([w for w in doctor.check(self.ws)[1] if 'hooks folder outside' in w], [])

if __name__ == '__main__':
    unittest.main()
