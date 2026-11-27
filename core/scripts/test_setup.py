#!/usr/bin/env python3
"""Setup builds a workspace where there is none yet, on one typed approval of a summary, with no command typed by a
person: the end-to-end path, and every way back into it that must stay shut."""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import testenv  # noqa: E402
import common  # noqa: E402
import doctor  # noqa: E402
import hooks  # noqa: E402
import setup  # noqa: E402
import sync  # noqa: E402

ANSWERS = '''team: Harbour Books
storage: {storage}
{remote}approvers:
  - Robin Vale
modes:
  - adhoc
repositories:
  - https://code.example.invalid/harbour/shop.git
gated_commands:
  send to a client: deliver\\.sh
backstops:
  send to a client: only two named people can send from the mail account
slots: mock
rules:
  - Client names never go into a commit message
'''
SHOWN_AT = 1767603600.0  # 2026-01-05T09:00Z, the minute testenv stamps a sitting's first line with


class Case(unittest.TestCase):
    storage, who = 'git', 'Robin Vale'

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        top = Path(self.tmp.name)
        self.ws, self.remote = top / 'ws', top / 'team.git'
        self.ws.mkdir()
        testenv.sh(top, 'git', 'init', '-q', '--bare', '-b', 'main', str(self.remote))
        conf = top / 'gitconfig'
        conf.write_text(f'[user]\n\tname = {self.who}\n\temail = test@example.invalid\n')
        self.env = mock.patch.dict(os.environ, {'GIT_CONFIG_GLOBAL': str(conf), 'TRAMPO_USER': self.who})
        self.env.start()
        self.answers = top / 'answers.yaml'
        self.put_answers()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def put_answers(self, text=None, remote=None):
        remote = f'remote: {remote or self.remote}\n' if self.storage == 'git' else ''
        self.answers.write_text(text or ANSWERS.format(storage=self.storage, remote=remote))

    def run_setup(self, verb, status=0, session='s1'):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = setup.main([str(self.ws), verb, str(self.answers), '--session', session])
        self.assertEqual(code, status, out.getvalue() + err.getvalue())
        return out.getvalue() + err.getvalue()

    def show(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return setup.show(self.ws, setup.answers_of(self.answers), now=SHOWN_AT)

    def says(self, *lines):
        testenv.sitting(self.ws, 's1', ('agent-said', 'the summary'), *lines)

    def built(self):
        self.show()
        self.says(('human', 'Yes, go ahead with the setup.'))
        return self.run_setup('build')

    def on_team_copy(self, rel):
        return testenv.sh(self.remote, 'git', 'show', f'main:{rel}')


class FromNothing(Case):
    def test_an_empty_folder_and_an_empty_remote_become_a_healthy_shared_workspace_on_one_typed_approval(self):
        said = self.built()
        self.assertIn('Robin Vale agreed to the setup summary', said)
        self.assertIn(f'The workspace is shared at {self.remote}', said)
        cfg = common.parse_yaml(self.on_team_copy('workspace.yaml'))
        self.assertEqual(cfg['approvers'], ['Robin Vale'])
        self.assertEqual(cfg['gated_commands'], {'send to a client': 'deliver\\.sh'})
        self.assertEqual(cfg['repositories'], ['https://code.example.invalid/harbour/shop.git'])
        self.assertEqual(cfg['core_version'], testenv.VERSION)
        self.assertIn('- Client names never go into a commit message', self.on_team_copy('constitution.md'))
        self.assertIn('## send to a client waits for an approver', self.on_team_copy('memory/shared/approval-gates.md'))
        self.assertIn('Approved-by: Robin Vale ', testenv.sh(self.remote, 'git', 'log', '-1', '--format=%B', 'main'))
        founding = [e for e in common.load_events(self.ws)[0] if e.get('ev') == 'approve']
        self.assertEqual([(e['gate'], e['by'], e['via']) for e in founding], [('founding', 'Robin Vale', 'typed')])
        self.assertIn(founding[0]['event_id'], testenv.sh(self.remote, 'git', 'log', '-1', '--format=%B', 'main'))
        fails, _ = doctor.check(self.ws)
        self.assertEqual(fails, [])
        self.assertEqual(testenv.sh(self.ws, 'git', 'status', '--porcelain'), '')

    def test_the_next_share_goes_through_the_ordinary_way(self):
        self.built()
        (self.ws / 'memory' / 'note.md').write_text('# A note\n')
        testenv.sh(self.ws, 'git', 'add', 'memory/note.md')
        testenv.sh(self.ws, 'git', 'commit', '-q', '-m', 'a note')
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(sync.main([str(self.ws)]), 0)
        self.assertEqual(self.on_team_copy('memory/note.md'), '# A note')

    def test_the_summary_says_in_plain_words_what_the_control_files_will_hold_and_how_to_agree(self):
        text = self.show()
        for words in ('SETUP SUMMARY for Harbour Books', 'Nothing is written until you agree.',
                      'Who may approve an action that waits for a person: Robin Vale',
                      '  - send to a client (what stops it outside the assistant: only two named people can send from the mail account)',
                      '  - Client names never go into a commit message', 'You are Robin Vale.',
                      'To agree, type a sentence that says yes to the setup, for example: "Yes, go ahead with the setup."'):
            self.assertIn(words, text)
        self.assertFalse((self.ws / 'workspace.yaml').exists())

    def test_a_shared_folder_is_built_the_same_way_with_no_git(self):
        self.storage = 'files'
        self.put_answers()
        said = self.built()
        self.assertIn('recorded as the founding approval', said)
        self.assertFalse((self.ws / '.git').exists())
        self.assertEqual(common.listed(common.config(self.ws), 'approvers'), ['Robin Vale'])


class Lite(Case):
    """Lite setup: one person, card mode with runbooks. Three questions, and everything else at defaults that open no gate
    the full interview's recommended answers would keep shut."""

    def setUp(self):
        super().setUp()
        conf = mock.patch.dict(os.environ, {'XDG_CONFIG_HOME': str(Path(self.tmp.name) / 'config')})
        conf.start()
        self.addCleanup(conf.stop)
        self.repo = Path(self.tmp.name) / 'code' / 'shop'
        self.repo.mkdir(parents=True)
        testenv.sh(self.repo, 'git', 'init', '-q')
        self.put_answers(f'setup: lite\nteam: Harbour Books\napprovers:\n  - Robin Vale\nrepositories:\n  - {self.repo}\n')

    def full_recommended(self, where):
        """The full interview, answered the recommended way for one person with no second reviewer."""
        self.ws = where
        self.ws.mkdir()
        self.put_answers(f'team: Harbour Books\nstorage: git\napprovers:\n  - Robin Vale\nmodes:\n  - card\n'
                         f'repositories:\n  - {self.repo}\noutside: ask-first\n')
        self.built()

    def gate(self, tool, given, *said):
        data = {'tool_name': tool, 'tool_input': given, 'cwd': str(self.ws), 'session_id': 's1',
                'transcript_path': testenv.sitting(self.ws, 's1', *said)}
        return hooks.gate_why(data)

    def test_the_skill_offers_lite_first_and_lite_asks_three_questions(self):
        text = (HERE.parent / 'skills/setup/SKILL.md').read_text()
        lite = text.split('## 0. Lite or full')[1].split('\n## ')[0]
        self.assertEqual(len([l for l in lite.splitlines() if l[:3] in ('1. ', '2. ', '3. ')]), 3, lite)
        for words in ('Team or workspace name', 'code repository', 'approver'):
            self.assertIn(words, lite)

    def test_lite_answers_with_only_the_three_answers_build_a_healthy_workspace(self):
        said = self.built()
        self.assertIn('recorded as the founding approval', said)
        cfg = common.config(self.ws)
        self.assertEqual((cfg['storage'], cfg['modes'], cfg['repositories'], cfg['outside']), ('git', ['card'], [str(self.repo)], 'ask-first'))
        for rel in ('modes/card.md', 'modes/runbooks.md', 'runbooks/README.md'):
            self.assertTrue((self.ws / rel).is_file(), rel)
        self.assertEqual(doctor.check(self.ws)[0], [])

    def test_the_control_files_equal_the_full_interviews_except_the_lite_differences(self):
        self.built()
        lite = {rel: (self.ws / rel).read_text() for rel in ('workspace.yaml', 'constitution.md', 'AGENTS.md')}
        gates = (self.ws / 'memory/shared/approval-gates.md').read_text()
        self.full_recommended(Path(self.tmp.name) / 'full')
        full = {rel: (self.ws / rel).read_text() for rel in lite}
        self.assertEqual(lite['constitution.md'], full['constitution.md'])
        self.assertEqual(lite['AGENTS.md'], full['AGENTS.md'])
        self.assertEqual(lite['workspace.yaml'], full['workspace.yaml'])
        self.assertEqual(gates, (self.ws / 'memory/shared/approval-gates.md').read_text())

    def test_the_named_repositories_go_into_this_persons_areas_once(self):
        (common.config_dir()).mkdir(parents=True, exist_ok=True)
        (common.config_dir() / 'areas').write_text(f'{self.repo}\n/elsewhere/kept\n')
        self.built()
        self.assertEqual((common.config_dir() / 'areas').read_text().splitlines(), [str(self.repo), '/elsewhere/kept'])
        (common.config_dir() / 'areas').unlink()
        self.ws = Path(self.tmp.name) / 'ws2'
        self.ws.mkdir()
        self.built()
        self.assertEqual(common.areas(), [str(self.repo)])
        self.assertIn(f'Folders on this machine where the assistant edits without asking: {self.repo}', self.show_text())

    def show_text(self):
        return setup.summary(self.ws, setup.answers_of(self.answers))

    def test_an_edit_in_the_repository_goes_ahead_and_a_control_file_and_an_outside_write_still_ask(self):
        self.built()
        self.assertEqual(common.config(self.ws).get('gated_commands'), None)
        self.assertIsNone(self.gate('Write', {'file_path': str(self.repo / 'shop.py'), 'content': 'x'}))
        self.assertIn('needs a yes', self.gate('Write', {'file_path': str(self.ws / 'workspace.yaml'), 'content': 'x'}) or 'opened')
        with mock.patch.object(hooks, 'temp_dirs', return_value=[]):
            self.assertIn('needs a yes', self.gate('Write', {'file_path': str(Path(self.tmp.name) / 'other' / 'x.py'), 'content': 'x'}) or 'opened')
            self.assertIsNone(self.gate('Write', {'file_path': str(self.repo / 'shop.py'), 'content': 'x'}))

    def test_lite_takes_only_its_own_answers(self):
        self.put_answers(f'setup: lite\nteam: Harbour Books\napprovers:\n  - Robin Vale\nrepositories:\n  - {self.repo}\noutside: off\n')
        self.assertIn('lite takes only', self.run_setup('show', status=1))

    def test_a_repository_must_be_a_folder_on_this_machine(self):
        self.put_answers('setup: lite\nteam: Harbour Books\napprovers:\n  - Robin Vale\nrepositories:\n  - https://code.example.invalid/shop.git\n')
        self.assertIn('a folder on this machine', self.run_setup('show', status=1))

    def test_lite_is_refused_when_a_part_it_needs_is_not_installed(self):
        self.assertTrue({'trampo-mode-card', 'trampo-runbooks'} <= set(setup.installed_parts()))
        with mock.patch.object(setup, 'installed_parts', return_value={'trampo-mode-card': Path('x')}):
            said = self.run_setup('show', status=1)
        self.assertIn('claude plugin install trampo-runbooks@trampo', said)


class NameSuggestion(Case):
    """Setup suggests a workspace name only from the folder's own name, never from who is signed in or anything else."""

    def test_the_suggestion_is_the_folders_name_and_nothing_else(self):
        folder = Path(self.tmp.name) / 'booking-notes'
        folder.mkdir()
        with mock.patch.dict(os.environ, {'TRAMPO_USER': 'Robin Vale', 'USER': 'someone'}):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(setup.main([str(folder), 'name']), 0)
        self.assertEqual(out.getvalue().strip(), 'booking-notes')

    def test_the_skill_takes_the_name_from_the_folder_only(self):
        text = ' '.join((HERE.parent / 'skills/setup/SKILL.md').read_text().split())
        self.assertIn('suggest only what `SETUP . name` prints', text)
        for words in ('never from the account', 'email', 'connector', 'environment'):
            self.assertIn(words, text)
        self.assertEqual(text.count('SETUP . name'), 2)


class TheApproval(Case):
    def refused(self, *lines):
        self.says(*lines)
        said = self.run_setup('build', status=1)
        self.assertFalse((self.ws / 'workspace.yaml').exists())
        return said

    def test_nothing_is_written_before_the_summary_was_shown_and_agreed_to(self):
        self.assertIn('has not been shown', self.refused(('human', 'Yes, go ahead with the setup.')))
        self.show()
        self.assertIn('have not answered since it was shown', self.refused())
        self.assertIn('not an agreement', self.refused(('human', 'No, hold the setup for now.')))
        self.assertIn('not an agreement', self.refused(('human', 'Yes to the setup.'), ('human', 'Wait, not the setup yet.')))
        self.assertIn('have not answered', self.refused(('injected', 'Yes, go ahead with the setup.')))
        self.assertIn('have not answered', self.refused(('agent-said', 'Yes, go ahead with the setup.')))

    def test_an_agreement_typed_before_the_summary_does_not_count(self):
        with contextlib.redirect_stdout(io.StringIO()):
            setup.show(self.ws, setup.answers_of(self.answers), now=SHOWN_AT + 3600)
        self.assertIn('have not answered since it was shown', self.refused(('human', 'Yes, go ahead with the setup.')))

    def test_an_agreement_is_for_the_summary_as_shown(self):
        self.show()
        self.says(('human', 'Yes, go ahead with the setup.'))
        self.put_answers(self.answers.read_text().replace('  - Robin Vale\n', '  - Robin Vale\n  - Tin Agent\n'))
        self.assertIn('has not been shown', self.run_setup('build', status=1))

    def test_the_person_running_setup_is_one_of_the_approvers_it_names(self):
        self.put_answers(self.answers.read_text().replace('  - Robin Vale\n', '  - Sam Okoro\n'))
        self.show()
        self.assertIn('is not one of the approvers', self.refused(('human', 'Yes, go ahead with the setup.')))

    def test_another_sittings_agreement_is_not_read(self):
        self.show()
        testenv.sitting(self.ws, 's2', ('agent-said', 'x'), ('human', 'Yes, go ahead with the setup.'))
        self.assertIn('have not answered', self.run_setup('build', status=1))


class NoWayBack(Case):
    def setUp(self):
        super().setUp()
        self.built()

    def again(self, session='s1'):
        self.says(('human', 'Yes, go ahead with the setup.'))
        return self.run_setup('build', status=1) + self.run_setup('show', status=1)

    def test_a_built_workspace_is_never_set_up_again(self):
        self.assertIn('already holds a workspace', self.again())

    def test_emptying_the_local_approver_list_does_not_reopen_setup(self):
        cfg = self.ws / 'workspace.yaml'
        cfg.write_text(cfg.read_text().replace('approvers:\n  - Robin Vale\n', 'approvers: []\n'))
        self.assertEqual(common.listed(common.config(self.ws), 'approvers'), [])
        self.assertIn('already holds a workspace', self.again())

    def test_deleting_the_local_files_does_not_reopen_setup(self):
        (self.ws / 'workspace.yaml').unlink()
        self.assertIn('a commit in this folder already holds a workspace', self.again())
        shutil.rmtree(self.ws / '.git')
        shutil.rmtree(self.ws / 'telemetry')
        self.assertIn('already holds a workspace', self.again())

    def test_pointing_at_another_remote_does_not_reopen_setup(self):
        other = Path(self.tmp.name) / 'other.git'
        testenv.sh(self.ws, 'git', 'init', '-q', '--bare', '-b', 'main', str(other))
        (self.ws / 'workspace.yaml').unlink()
        testenv.sh(self.ws, 'git', 'remote', 'set-url', 'origin', str(other))
        self.assertIn('already holds a workspace', self.again())
        self.put_answers(remote=other)
        self.assertIn('already holds a workspace', self.again())
        testenv.sh(self.ws, 'git', 'remote', 'set-url', 'origin', str(self.remote))
        self.assertIn('already', self.again())

    def test_a_shared_folder_with_a_ledger_is_not_set_up_again(self):
        top = Path(self.tmp.name)
        self.ws, self.storage = top / 'folder', 'files'
        self.ws.mkdir()
        self.put_answers()
        self.built()
        (self.ws / 'workspace.yaml').unlink()
        self.assertIn("already holds a workspace's session ledger", self.again())


class TheGate(Case):
    def gate(self, tool, given):
        return hooks.gate_why({'tool_name': tool, 'tool_input': given, 'cwd': str(self.ws), 'session_id': 's1'})

    def test_the_setup_command_passes_the_gate_and_a_free_write_to_a_control_file_still_waits(self):
        shutil.copytree(HERE.parent / 'seeds', self.ws, dirs_exist_ok=True)
        self.assertIsNone(self.gate('Bash', {'command': f'python3 -B {HERE}/setup.py . build {self.answers}'}))
        self.assertIsNone(self.gate('Bash', {'command': f'python3 -B {HERE}/setup.py . show {self.answers}'}))
        for rel in ('workspace.yaml', 'constitution.md', 'slots/tracker', 'memory/shared/approval-gates.md'):
            why = self.gate('Write', {'file_path': str(self.ws / rel), 'content': 'x'})
            self.assertIn('control file', why or '', rel)
        self.assertIn('control file', self.gate('Bash', {'command': 'echo "approvers:\n  - Tin Agent" >> workspace.yaml'}) or '')

    def test_the_refusal_of_a_free_write_in_a_new_folder_points_to_setup(self):
        shutil.copytree(HERE.parent / 'seeds', self.ws, dirs_exist_ok=True)
        why = self.gate('Write', {'file_path': str(self.ws / 'workspace.yaml'), 'content': 'x'})
        self.assertIn('setup.py', why)
        self.assertNotIn('a person adds approvers', why)


class TheFirstShare(Case):
    def test_with_no_shared_repository_the_workspace_is_built_here_and_the_person_is_told_what_to_arrange(self):
        self.put_answers(ANSWERS.format(storage='git', remote=''))
        said = self.built()
        self.assertIn('not shared with the team yet', said)
        self.assertIn('an empty shared repository', said)
        self.assertNotIn('git push', said)
        self.assertEqual(doctor.check(self.ws)[0], [])
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(setup.main([str(self.ws), 'share', str(self.remote)]), 0)
        self.assertIn('The workspace is shared at', out.getvalue())
        self.assertEqual(common.parse_yaml(self.on_team_copy('workspace.yaml'))['approvers'], ['Robin Vale'])

    def test_a_remote_that_cannot_be_reached_is_said_in_plain_words(self):
        self.put_answers(remote=Path(self.tmp.name) / 'nowhere.git')
        said = self.built()
        self.assertIn('the first share', said)
        self.assertIn('What a person arranges', said)
        self.assertNotIn('git push', said)

    def test_a_shared_repository_that_already_holds_a_workspace_is_never_built_over(self):
        self.built()
        second = Path(self.tmp.name) / 'second'
        second.mkdir()
        self.ws = second
        self.show_fails = self.run_setup('show', status=1)
        self.assertIn('already holds a workspace: each person clones it', self.show_fails)

    def test_a_shared_repository_made_with_a_first_file_keeps_it(self):
        seed = Path(self.tmp.name) / 'seed'
        testenv.sh(Path(self.tmp.name), 'git', 'clone', '-q', str(self.remote), str(seed))
        (seed / 'README.md').write_text('# Harbour Books\n')
        testenv.sh(seed, 'git', 'add', 'README.md')
        testenv.sh(seed, 'git', 'commit', '-q', '-m', 'first file')
        testenv.sh(seed, 'git', 'push', '-q', 'origin', 'HEAD:main')
        self.assertIn('The workspace is shared at', self.built())
        self.assertEqual(self.on_team_copy('README.md'), '# Harbour Books')
        self.assertEqual(common.parse_yaml(self.on_team_copy('workspace.yaml'))['approvers'], ['Robin Vale'])

    def test_sync_points_to_setup_for_a_first_share_and_names_no_git_command(self):
        self.put_answers(ANSWERS.format(storage='git', remote=''))
        self.built()
        testenv.sh(self.ws, 'git', 'remote', 'add', 'origin', str(self.remote))
        err = io.StringIO()
        with contextlib.redirect_stdout(err), contextlib.redirect_stderr(err):
            self.assertNotEqual(sync.main([str(self.ws)]), 0)
        self.assertIn('setup.py', err.getvalue())
        self.assertNotIn('git push', err.getvalue())


class NoNameOnTheMachine(Case):
    def setUp(self):
        super().setUp()
        self.conf = Path(self.tmp.name) / 'gitconfig'
        self.conf.write_text('')
        self.named()

    def named(self, name='Robin Vale'):
        self.put_answers(self.answers.read_text().split('your_name:')[0].rstrip('\n') + (f'\nyour_name: {name}\n' if name else '\n'))

    def local_name(self):
        r = testenv.subprocess.run(['git', '-C', str(self.ws), 'config', '--local', 'user.name'], capture_output=True, text=True)
        return r.stdout.strip()

    def test_the_name_the_person_gave_is_shown_and_set_for_this_workspace_only(self):
        self.assertIn('You are Robin Vale.', self.show())
        self.assertFalse((self.ws / '.git').exists())
        self.assertIn('Robin Vale agreed to the setup summary', self.built())
        self.assertEqual(self.local_name(), 'Robin Vale')
        self.assertEqual(self.conf.read_text(), '')
        self.assertEqual(testenv.sh(self.remote, 'git', 'log', '-1', '--format=%an', 'main'), 'Robin Vale')
        self.assertEqual(doctor.check(self.ws)[0], [])

    def test_a_name_the_machine_already_has_is_never_replaced(self):
        self.conf.write_text('[user]\n\tname = Robin Vale\n')
        self.put_answers(self.answers.read_text().replace('  - Robin Vale\n', '  - Robin Vale\n  - Sam Okoro\n'))
        self.named('Sam Okoro')
        self.assertIn('You are Robin Vale.', self.show())
        self.built()
        self.assertEqual(self.local_name(), '')

    def test_the_name_given_must_be_an_approver_the_answers_name(self):
        self.named('Sam Okoro')
        self.show()
        self.says(('human', 'Yes, go ahead with the setup.'))
        self.assertIn('is not one of the approvers', self.run_setup('build', status=1))
        self.assertFalse((self.ws / '.git').exists())

    def test_with_no_name_at_all_the_assistant_is_told_to_ask_for_it_not_to_send_the_person_to_a_terminal(self):
        self.named(None)
        self.assertIn('not known to this machine by name', self.show())
        self.says(('human', 'Yes, go ahead with the setup.'))
        said = self.run_setup('build', status=1)
        self.assertIn('ask the person for their name', said)
        self.assertIn('your_name', said)

    def test_a_name_is_set_only_while_the_workspace_is_being_set_up(self):
        self.built()
        testenv.sh(self.ws, 'git', 'config', '--local', '--unset', 'user.name')
        self.named('Sam Okoro')
        self.says(('human', 'Yes, go ahead with the setup.'))
        self.run_setup('build', status=1)
        self.assertEqual(self.local_name(), '')
        why = hooks.gate_why({'tool_name': 'Bash', 'tool_input': {'command': 'git config user.name "Sam Okoro"'}, 'cwd': str(self.ws), 'session_id': 's1'})
        self.assertIn('declared by a person', why or '')

    def test_a_shared_folder_takes_no_name_from_the_answers(self):
        self.storage = 'files'
        self.put_answers()
        self.named('Robin Vale')
        with mock.patch.dict(os.environ, {'TRAMPO_USER': ''}):
            self.assertIn('not known to this machine by name', self.show())


class TheSkill(unittest.TestCase):
    def test_setup_builds_through_the_command_and_asks_for_the_teams_own_rules(self):
        text = ' '.join((HERE.parent / 'skills/setup/SKILL.md').read_text().split())
        for words in ('SETUP . show setup-answers.yaml', 'SETUP . build setup-answers.yaml', 'scripts/setup.py', "The team's own rules", 'Read the whole summary to the person',
                      'never ask a person to type a command'):
            self.assertIn(words, text)
        for words in ('git init', 'push it'):
            self.assertNotIn(words, text)


if __name__ == '__main__':
    unittest.main()
