#!/usr/bin/env python3
"""An epic run: the plan from the tracker's own links, one writer for the run's three files, a dispatch that
refuses a worker the run is not ready for, and the checks that follow a worker into its worktree."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import testenv  # noqa: E402
import common  # noqa: E402
import event  # noqa: E402
import hooks  # noqa: E402
import run  # noqa: E402
from test_slots import mocked  # noqa: E402

GATES = 'gated_commands:\n  release: release\\.sh\n'
BRIEF = '# Brief: W-1\n\n## Goal\nAdd the export.\n\n## Done when\nThe suite passes and the report is written.\n\n## Reads\nmodes/card.md\n\n' \
        '## Rails\nYou cannot ask.\n\n## Park\nSay what is missing.\n\n## Report\nsessions/W-1/report.md\n'


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        top = Path(self.tmp.name)
        self.code = top / 'code'
        self.ws = mocked(testenv.workspace(top / 'ws', extra=GATES + f'repositories:\n  - {self.code.resolve()}\n'), top / 'world')
        for title, needs in (('Add the export', ''), ('Document the export', 'W-1'), ('Fix the footer', '')):
            draft = top / 'draft.md'
            draft.write_text(f'title: {title}\nneeds: {needs}\n\nbody\n')
            self.slot('tracker', 'create', str(draft))
        self.tree = self.repo(self.code, top / 'code-w1')

    def repo(self, code, tree):
        code.mkdir()
        for args in (('init', '-q', '-b', 'main'), ('config', 'user.name', 'Tin Agent'), ('config', 'user.email', 'test@example.invalid'),
                     ('commit', '-q', '--allow-empty', '-m', 'start'), ('worktree', 'add', '-q', '-b', tree.name, str(tree))):
            testenv.sh(code, 'git', *args)
        return tree

    def tearDown(self):
        self.tmp.cleanup()

    def slot(self, name, *args):
        return run.slot_rows(self.ws, name, *args)

    def cmd(self, *args, stdin=None, status=0):
        out, err, old = io.StringIO(), io.StringIO(), sys.stdin
        sys.stdin = io.StringIO(stdin or '')
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = run.main(['--ws', str(self.ws), '--run', 'export', *args])
        finally:
            sys.stdin = old
        self.assertEqual(code, status, err.getvalue() + out.getvalue())
        return out.getvalue() + err.getvalue()

    def write(self, *records, status=0):
        return self.cmd('write', '-', stdin=json.dumps({'message': 'run export: tick', 'records': list(records)}), status=status)

    def ready(self, verdict='READY'):
        (self.ws / 'sessions/export').mkdir(parents=True, exist_ok=True)
        (self.ws / 'sessions/export/readiness.md').write_text(f'# Readiness: export   2026-01-05   Verdict: {verdict}\n')

    def brief(self, text=BRIEF):
        f = Path(self.tmp.name) / 'brief.md'
        f.write_text(text)
        return str(f)


class Plan(Case):
    def test_the_lanes_come_from_what_each_item_waits_on_not_from_the_order_given(self):
        said = self.cmd('plan', 'W-2', 'W-1', 'W-3')
        self.assertIn('step 1: W-1, W-3', said)
        self.assertIn('step 2: W-2', said)
        self.assertIn('wait for their word', said)
        state = self.cmd('state')
        self.assertIn('W-1: Open (can be dispatched now)', state)
        self.assertIn('W-2: Open (W-1 is at Open, not yet Ready)', state)

    def test_an_item_the_tracker_cannot_give_is_not_planned(self):
        self.assertIn('could not be read', self.cmd('plan', 'W-9', status=1))


class Records(Case):
    def setUp(self):
        super().setUp()
        self.cmd('plan', 'W-1', 'W-2', 'W-3')

    def test_a_blocker_is_one_row_for_the_missing_thing_and_every_item_that_waits(self):
        self.write({'op': 'block', 'missing': 'the test site login', 'items': 'W-1 W-3', 'owner': 'Robin Vale',
                    'resume': 'the login works from the worker host', 'ask': 'access'})
        state = self.cmd('state')
        self.assertIn('open blockers: 1', state)
        self.assertIn('W-3: Open (blocker 1: the test site login)', state)
        self.assertIn('ask=access', (self.ws / 'sessions/export/blockers.md').read_text())
        self.write({'op': 'edit', 'id': '1', 'status': 'cleared', 'note': 'login added'})
        self.assertIn('W-3: Open (can be dispatched now)', self.cmd('state'))
        self.assertIn('ask=access: login added', (self.ws / 'sessions/export/blockers.md').read_text())

    def test_a_batch_is_written_whole_or_not_at_all(self):
        before = (self.ws / 'sessions/export/phase-log.md').read_text()
        said = self.write({'op': 'move', 'item': 'W-1', 'to': 'Intake', 'why': 'dispatched'},
                          {'op': 'block', 'missing': 'x', 'items': 'W-1', 'owner': 'Robin Vale'}, status=1)
        self.assertIn('record 2 (block)', said)
        self.assertEqual((self.ws / 'sessions/export/phase-log.md').read_text(), before)

    def test_a_move_keeps_to_the_ladder_and_a_move_back_names_its_cause(self):
        self.assertIn('a phase of the ladder', self.write({'op': 'move', 'item': 'W-1', 'to': 'Almost done', 'why': 'x'}, status=1))
        self.write({'op': 'move', 'item': 'W-1', 'to': 'Intake', 'why': 'dispatched'},
                   {'op': 'move', 'item': 'W-1', 'to': 'Waiting review', 'why': 'review request R1 opened'})
        self.assertIn('cause token', self.write({'op': 'move', 'item': 'W-1', 'to': 'Coding', 'why': 'two findings'}, status=1))
        self.write({'op': 'move', 'item': 'W-1', 'to': 'Coding', 'why': 'review: two findings on R1'})
        self.assertIn('Waiting review -> Coding  review: two findings on R1', self.cmd('state', 'W-1'))
        self.assertIn('at most 200', self.write({'op': 'move', 'item': 'W-1', 'to': 'parked', 'why': 'x' * 300}, status=1))

    def test_the_three_files_are_one_commit_and_nothing_else_is_in_it(self):
        (self.ws / 'someone-elses.md').write_text('x\n')
        self.write({'op': 'item', 'item': 'W-1', 'set': {'worker': 'w-1', 'branch': 'w-1-export'}})
        ok, files = common.git(self.ws, 'show', '--name-only', '--format=%s', 'HEAD')
        self.assertIn('run export: tick', files)
        self.assertNotIn('someone-elses.md', files)
        self.assertIn('| W-1 | Add the export |  | w-1 | w-1-export |', (self.ws / 'sessions/export/run-ledger.md').read_text())

    def test_the_tracker_follows_the_phase_log_and_stops_where_a_person_takes_over(self):
        self.write({'op': 'move', 'item': 'W-1', 'to': 'Intake', 'why': 'dispatched'})
        self.assertIn('W-1: open -> in progress', self.cmd('follow'))
        self.write({'op': 'move', 'item': 'W-1', 'to': 'Waiting review', 'why': 'R1 opened'})
        self.cmd('follow')
        self.assertEqual(self.slot('tracker', 'read', 'W-1')[0]['state'], 'in review')
        self.write({'op': 'move', 'item': 'W-1', 'to': 'Done', 'why': 'a person merged and released it'})
        self.assertIn('already agrees', self.cmd('follow'))
        self.assertEqual(self.slot('tracker', 'read', 'W-1')[0]['state'], 'in review')


class Dispatch(Case):
    def setUp(self):
        super().setUp()
        self.cmd('plan', 'W-1', 'W-2', 'W-3')

    def go(self, item='W-1', text=BRIEF, status=0):
        return self.cmd('dispatch', item, '--brief', self.brief(text), '--worktree', str(self.tree), status=status)

    def test_no_worker_starts_before_the_readiness_record_says_ready(self):
        self.assertIn('Verdict: READY', self.go(status=1))
        self.ready('NOT READY')
        self.assertIn('Verdict: READY', self.go(status=1))
        self.ready('READY FOR W-3')
        self.assertIn('Verdict: READY', self.go(status=1))
        self.ready()
        self.assertIn('--bg', self.go())

    def test_an_item_whose_need_is_not_ready_or_whose_blocker_is_open_does_not_start(self):
        self.ready()
        self.assertIn('W-1 is at Open, not yet Ready', self.go('W-2', status=1))
        self.write({'op': 'block', 'missing': 'the export spec', 'items': 'W-1', 'owner': 'Robin Vale', 'resume': 'the spec is on the item'})
        self.assertIn('blocker 1', self.go(status=1))

    def test_a_brief_missing_a_section_or_holding_an_open_point_is_refused(self):
        self.ready()
        self.assertIn('lacks ## Park', self.go(text=BRIEF.replace('## Park\n', '## Parking\n'), status=1))
        self.assertIn('still says "TBC"', self.go(text=BRIEF.replace('Add the export.', 'Add the export, format TBC.'), status=1))

    def test_the_command_it_prints_carries_the_rails_and_a_sandbox_and_passes_the_spawn_check(self):
        self.ready()
        command = self.go()
        settings = json.loads((self.ws / 'sessions/export/workers/W-1.settings.json').read_text())['sandbox']
        self.assertTrue(settings['enabled'])
        self.assertFalse(settings['allowUnsandboxedCommands'])
        self.assertIn(str(self.tree.resolve()), settings['filesystem']['allowWrite'])
        self.assertTrue(settings['network']['strictAllowlist'])
        ws = self.ws.resolve()
        self.assertIn(str(ws / 'telemetry/events'), settings['filesystem']['allowWrite'])
        self.assertIn(str(ws / '.trampo/state/ask'), settings['filesystem']['denyWrite'])
        self.assertIn(f'--plugin-dir {HERE.parent}', command)
        self.assertIn('/goal Read', (self.ws / 'sessions/export/workers/W-1.goal').read_text())
        gate = lambda c: hooks.gate_why({'tool_name': 'Bash', 'tool_input': {'command': c}, 'cwd': str(self.ws), 'session_id': 'c1'})
        self.assertIsNone(gate(command))
        self.assertIn('without', gate('claude --bg "do the item" --permission-mode bypassPermissions'))
        self.assertIn('sandbox', gate(command.split(' --settings')[0]))
        self.assertIn('AskUserQuestion', gate(command.replace('--disallowed-tools AskUserQuestion ', '')))

    def test_a_background_start_names_the_settings_dispatch_wrote_unchanged(self):
        self.ready()
        command = self.go()
        gate = lambda c: hooks.gate_why({'tool_name': 'Bash', 'tool_input': {'command': c}, 'cwd': str(self.ws), 'session_id': 'c1'})
        written = self.ws / 'sessions/export/workers/W-1.settings.json'
        self.assertIsNone(gate(command))
        self.assertIsNone(gate('nohup ' + command))
        copy = Path(self.tmp.name) / 'mine.json'
        copy.write_text(written.read_text())
        self.assertIn('the one dispatch wrote', gate(command.replace(str(written), str(copy))))
        inline = json.dumps({'sandbox': {'enabled': True, 'allowUnsandboxedCommands': False}})
        self.assertIn('the one dispatch wrote', gate(command.replace(str(written), f"'{inline}'")))
        kept = written.read_text()
        for widen in (lambda b: b['filesystem']['allowWrite'].append('/'), lambda b: b['network']['allowedDomains'].append('example.invalid'),
                      lambda b: b['filesystem'].update(denyWrite=[]), lambda b: b['network'].update(strictAllowlist=False)):
            box = json.loads(kept)
            widen(box['sandbox'])
            written.write_text(json.dumps(box))
            self.assertIn('differs from what dispatch writes', gate(command))
        written.write_text(kept)
        self.assertIsNone(gate(command))

    def test_the_start_command_drops_the_mark_that_stops_a_worker_saving_its_transcript(self):
        self.ready()
        command = self.go()
        self.assertTrue(command.startswith('env -u CLAUDE_CODE_CHILD_SESSION claude --bg '), command[:80])
        gate = lambda c: hooks.gate_why({'tool_name': 'Bash', 'tool_input': {'command': c}, 'cwd': str(self.ws), 'session_id': 'c1'})
        self.assertIsNone(gate(command))
        self.assertIn('without', gate('env -u CLAUDE_CODE_CHILD_SESSION claude --bg "do the item" --permission-mode bypassPermissions') or '')

    def test_a_background_start_behind_a_common_wrapper_is_still_read(self):
        gate = lambda c: hooks.gate_why({'tool_name': 'Bash', 'tool_input': {'command': c}, 'cwd': str(self.ws), 'session_id': 'c1'})
        for front in ('env A=1 B=2 nohup timeout 60 ', 'nice -n 5 command ', 'A=1 exec '):
            self.assertIn('without', gate(front + 'claude --bg "do the item" --permission-mode bypassPermissions') or '', front)
        self.assertIsNone(gate('echo claude --bg is how a worker starts'))

    def test_only_a_worktree_of_a_repository_the_team_declared_is_bound(self):
        self.ready()
        top = Path(self.tmp.name)
        other = self.repo(top / 'elsewhere', top / 'elsewhere-w1')
        plain = top / 'plain'
        plain.mkdir()
        (self.tree / 'sub').mkdir()
        refused = ((other, 'is not one the team declared'), (plain, 'not a git worktree'), (self.tree / 'sub', 'not a git worktree'),
                   (top, 'holds the workspace'), (self.ws, 'the workspace itself'), (Path.home(), 'home folder'),
                   (Path.home().parent, 'home folder'), (Path('/'), 'file system root'))
        for folder, words in refused:
            said = self.cmd('dispatch', 'W-1', '--brief', self.brief(), '--worktree', str(folder), status=1)
            self.assertIn(words, said, folder)
            self.assertIsNone(common.bound_workspace(folder), folder)
        self.go()
        self.assertEqual(common.bound_workspace(self.tree), self.ws.resolve())

    def test_an_address_counts_only_inside_a_working_area_the_person_declared_on_this_machine(self):
        self.ready()
        top = Path(self.tmp.name)
        (top / 'work').mkdir()
        other = self.repo(top / 'work/elsewhere', top / 'work/elsewhere-w1')
        testenv.sh(top / 'work/elsewhere', 'git', 'remote', 'add', 'origin', 'https://code.example.invalid/team/elsewhere.git')
        cfg = self.ws / 'workspace.yaml'
        cfg.write_text(cfg.read_text() + '  - https://code.example.invalid/team/elsewhere.git\n')
        go = lambda status: self.cmd('dispatch', 'W-1', '--brief', self.brief(), '--worktree', str(other), status=status)
        self.assertIn('working area', go(1))
        self.assertIsNone(common.bound_workspace(other))
        areas = common.config_dir() / 'areas'
        areas.parent.mkdir(parents=True, exist_ok=True)
        self.addCleanup(lambda: areas.unlink(missing_ok=True))
        areas.write_text(f'{top / "somewhere-else"}\n')
        self.assertIn('working area', go(1))
        areas.write_text(f'{(top / "work").resolve()}\n')
        self.assertIn('--bg', go(0))

    def test_the_working_areas_file_is_not_written_by_a_session(self):
        areas = common.config_dir() / 'areas'
        call = lambda tool, given: hooks.gate_why({'tool_name': tool, 'tool_input': given, 'cwd': str(self.ws), 'session_id': 'c1'})
        self.assertIn('declared by a person', call('Write', {'file_path': str(areas), 'content': '/\n'}))
        self.assertIn('declared by a person', call('Edit', {'file_path': str(areas), 'old_string': 'a', 'new_string': 'b'}))
        for cmd in (f'echo / >> {areas}', f'cp mine.txt {areas}', f'tee {areas} < mine.txt', 'echo / >> ~/.config/trampo/areas'):
            self.assertIn('declared by a person', call('Bash', {'command': cmd}) or '', cmd)

    def test_the_settings_of_a_start_are_exactly_what_dispatch_wrote_and_named_once(self):
        self.ready()
        command = self.go().strip()
        gate = lambda c: hooks.gate_why({'tool_name': 'Bash', 'tool_input': {'command': c}, 'cwd': str(self.ws), 'session_id': 'c1'})
        written = self.ws / 'sessions/export/workers/W-1.settings.json'
        kept = written.read_text()
        for extra in ({'permissions': {'allow': ['Bash(*)']}}, {'hooks': {}}, {'env': {'A': '1'}}):
            written.write_text(json.dumps({**json.loads(kept), **extra}))
            self.assertIn('differs from what dispatch writes', gate(command) or '', extra)
        written.write_text(kept)
        self.assertIsNone(gate(command))
        self.assertIsNone(gate(command.replace(f'--settings {written}', f'--settings={written}')))
        other = Path(self.tmp.name) / 'mine.json'
        other.write_text('{}')
        for twice in (f'{command} --settings {other}', f'{command} --settings={other}', command.replace('--settings ', f'--settings={other} --settings ')):
            self.assertIn('one --settings', gate(twice) or '', twice)
        self.assertIn('the one dispatch wrote', gate(command.replace(f'--settings {written}', f'--settings={other}')))
        for first in (f"echo '{{}}' > {written}; ", f'cp {other} {written} && ', f'tee {written} < {other}; '):
            self.assertIn('writes the settings', gate(first + command) or '', first)
        self.assertIn('writes the settings', gate(f'{command}; cp {other} {written}') or '')

    def test_the_gates_follow_the_worker_into_its_worktree(self):
        call = {'tool_name': 'Bash', 'tool_input': {'command': './release.sh W-1'}, 'cwd': str(self.tree), 'session_id': 'w1'}
        self.assertIsNone(hooks.gate_why(call))
        self.ready()
        self.go()
        self.assertIn('gated action', hooks.gate_why(call))
        self.assertIn('no worker session has opened', self.cmd('state'))

    def test_the_state_says_a_worker_is_there_only_once_its_session_has_opened(self):
        self.ready()
        self.go()
        state = self.cmd('state')
        self.assertNotIn('worker dispatched', state)
        self.assertIn('W-1: Open (start command printed, no worker session has opened for it', state)
        with contextlib.redirect_stdout(io.StringIO()):
            event.main(['open', '--ws', str(self.ws), '--kind', 'card', '--subject', 'W-1', '--session', 'w1'])
        self.assertIn('(worker session open, gate hook', self.cmd('state'))


class Confirm(Case):
    def setUp(self):
        super().setUp()
        self.cmd('plan', 'W-1')

    def test_the_checklist_is_read_from_the_items_own_records(self):
        lacks = self.cmd('confirm', 'W-1', status=1)
        for words in ('ended done', 'qa-report.md is missing', 'report.md is missing', 'names no review request'):
            self.assertIn(words, lacks)
        draft = Path(self.tmp.name) / 'r.md'
        draft.write_text('Add the export\n\nCloses W-1.\n')
        ref = self.slot('code-host', 'open-review', 'w-1-export', str(draft))[0]['review']
        self.slot('code-host', 'sim-check', ref, 'build', 'failed')
        self.write({'op': 'item', 'item': 'W-1', 'set': {'review': ref}})
        (self.ws / 'sessions/W-1').mkdir(parents=True)
        (self.ws / 'sessions/W-1/report.md').write_text('Committed 3f9c2ab on w-1-export. Acceptance 1: PROVEN, the CSV downloads.\n')
        (self.ws / 'sessions/W-1/qa-report.md').write_text('## Pass 1\n\nVerdict: PASS\n')
        with contextlib.redirect_stdout(io.StringIO()):
            event.main(['open', '--ws', str(self.ws), '--kind', 'card', '--subject', 'W-1', '--session', 'w1'])
            event.main(['close', '--ws', str(self.ws), '--session', 'w1', '--outcome', 'done', '--goal-met', 'the CSV downloads on the test site'])
        self.assertIn(f'checks not passed on {ref}: build', self.cmd('confirm', 'W-1', status=1))
        self.slot('code-host', 'sim-check', ref, 'build', 'passed')
        self.assertIn('every row', self.cmd('confirm', 'W-1'))
        with (self.ws / 'sessions/W-1/qa-report.md').open('a') as f:
            f.write('\n## Pass 2\n\nVerdict: FAIL\n')
        self.assertIn('the last QA verdict in sessions/W-1/qa-report.md is FAIL', self.cmd('confirm', 'W-1', status=1))


class Rails(Case):
    def test_a_run_sitting_is_told_its_rails_again_at_every_start_and_compaction(self):
        self.assertNotIn('never implement', hooks.index({'cwd': str(self.ws), 'session_id': 'c1'})['say'])
        with contextlib.redirect_stdout(io.StringIO()):
            event.main(['open', '--ws', str(self.ws), '--kind', 'run', '--subject', 'export', '--session', 'c1'])
        said = hooks.index({'cwd': str(self.ws), 'session_id': 'c1'})['say']
        self.assertIn('You never implement', said)
        self.assertIn('Workers commit and report', said)
        self.assertEqual(self.cmd('rails').strip(), run.RAILS)


if __name__ == '__main__':
    unittest.main()
