#!/usr/bin/env python3
"""The unattended loop, ticked against the mock slots: pickup, the cap, a wait on a chat answer, a stop at ready for release,
and the monitor that keeps the loop alive."""
import json
import os
import sys
import tempfile
import time
import unittest
from unittest import mock
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import testenv  # noqa: E402
import agent  # noqa: E402
import common  # noqa: E402
import hooks  # noqa: E402
import doctor  # noqa: E402
import run  # noqa: E402
from test_slots import mocked  # noqa: E402


class World(unittest.TestCase):
    bot_extra = ''

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        top = Path(self.tmp.name)
        home = top / 'world'
        self.lead = mocked(testenv.workspace(top / 'lead', who='Robin Vale', extra='approvers:\n  - Robin Vale\n'), home)
        self.bot = mocked(testenv.workspace(top / 'bot', who='Tin Agent', extra=self.bot_extra), home)
        self.watch = mocked(testenv.workspace(top / 'watch', who='Mon Agent'), home)
        (self.bot / 'agents').mkdir()
        (self.bot / 'agents/launch.sh').write_text(f'#!/bin/sh\necho "$1" >> {top}/launched\n')
        (self.bot / 'agents/launch.sh').chmod(0o755)
        (self.bot / 'agents/card-agent.yaml').write_text('kind: card\nassignee: Tin Agent\ncap: 2\ninterval: 15\nlaunch: agents/launch.sh\n')
        (self.watch / 'agents').mkdir()
        for name in ('card-agent',):
            (self.watch / 'agents' / f'{name}.yaml').write_text('kind: card\ninterval: 15\n')
        (self.watch / 'agents/agents-monitor.yaml').write_text('kind: monitor\nwatches:\n  - card-agent\nstuck_hours: 8\n')
        self.launched = top / 'launched'
        self.items = []
        for title in ('One', 'Two', 'Three'):
            d = top / 'd.md'
            d.write_text(f'title: {title}\nassignee: Tin Agent\n\nbody\n')
            self.items.append(run.slot_rows(self.lead, 'tracker', 'create', str(d))[0]['id'])

    def tearDown(self):
        self.tmp.cleanup()

    def states(self):
        return {r['id']: r['state'] for r in run.slot_rows(self.lead, 'tracker', 'list')}

    def sent(self):
        return self.launched.read_text().split() if self.launched.exists() else []

    def tick(self, now=None):
        return agent.tick(self.bot, 'card-agent', now)[0]


class CardAgent(World):
    def test_it_claims_what_is_assigned_to_it_and_starts_one_worker_per_item_up_to_its_cap(self):
        self.assertEqual(self.tick(), 'launched')
        self.assertEqual(self.sent(), self.items[:2])
        self.assertEqual(self.states()[self.items[0]], 'in progress')
        self.assertEqual(self.states()[self.items[2]], 'open')
        self.assertEqual(self.tick(), 'capped')
        self.assertEqual(self.sent(), self.items[:2])

    def test_an_item_not_assigned_to_it_is_never_picked_up(self):
        run.slot_rows(self.lead, 'tracker', 'assign', self.items[0], 'Robin Vale')
        self.tick()
        self.assertNotIn(self.items[0], self.sent())

    def test_a_quiet_tick_leaves_one_word_and_prints_nothing_else(self):
        for i in self.items:
            run.slot_rows(self.lead, 'tracker', 'assign', i, 'Robin Vale')
        self.assertEqual(agent.main(['--ws', str(self.bot), 'tick', 'card-agent']), 0)
        self.assertEqual((self.bot / '.trampo/state/agent-card-agent.last').read_text(), 'idle')

    def test_a_paused_agent_touches_nothing_until_a_person_resumes_it(self):
        agent.main(['--ws', str(self.bot), 'pause', 'card-agent'])
        self.assertEqual(self.tick(), 'paused')
        self.assertEqual(self.sent(), [])
        agent.main(['--ws', str(self.bot), 'resume', 'card-agent'])
        self.assertEqual(self.tick(), 'launched')

    def test_an_item_ready_for_release_is_left_for_a_person_and_ticks_go_quiet(self):
        for i in self.items:
            run.slot_rows(self.lead, 'tracker', 'move', i, 'ready for release')
        self.assertEqual(self.tick(), 'ready-for-release')
        self.assertEqual(self.sent(), [])

    def test_it_waits_on_its_own_question_until_a_person_answers_it(self):
        self.tick()
        first = self.items[0]
        q = self.bot / 'q.md'
        q.write_text('Which format?\n a) csv\n b) json\n')
        key = run.slot_rows(self.bot, 'ask', 'ask', first, str(q))[0]['key']
        agent.mark(self.bot, 'card-agent', 'waits', json.dumps({self.items[2]: key}))
        self.assertEqual(self.tick(), 'waiting')
        run.slot_rows(self.lead, 'ask', 'sim-answer', key, 'a')
        run.slot_rows(self.lead, 'tracker', 'move', self.items[1], 'in review')
        self.assertEqual(self.tick(), 'launched')
        self.assertIn(self.items[2], self.sent())

    def asked(self, item):
        q = self.bot / 'q.md'
        q.write_text('Which format?\n a) csv\n b) json\n')
        return run.slot_rows(self.bot, 'ask', 'ask', item, str(q))[0]['key']

    def test_a_worker_records_its_wait_and_the_waiting_item_still_holds_its_place_under_the_cap(self):
        self.tick()
        first, second, third = self.items
        key = self.asked(first)
        self.assertEqual(agent.main(['--ws', str(self.bot), 'wait', 'card-agent', first, key]), 0)
        self.assertEqual(self.tick(), 'waiting')
        self.assertEqual(self.sent(), [first, second])
        run.slot_rows(self.lead, 'tracker', 'move', second, 'in review')
        self.assertEqual(self.tick(), 'launched')
        self.assertEqual(self.sent(), [first, second, third])

    def test_only_an_approvers_reply_ends_a_wait_and_another_persons_reply_is_said_and_kept(self):
        self.tick()
        first = self.items[0]
        key = self.asked(first)
        agent.main(['--ws', str(self.bot), 'wait', 'card-agent', first, key])
        run.slot_rows(self.watch, 'ask', 'sim-answer', key, 'a')
        word, notes = agent.tick(self.bot, 'card-agent')
        self.assertEqual(word, 'waiting')
        self.assertIn('Mon Agent', ' '.join(notes))
        self.assertIn('not an approver', ' '.join(notes))
        self.assertEqual(self.sent().count(first), 1)
        run.slot_rows(self.lead, 'ask', 'sim-answer', key, 'a')
        self.assertEqual(self.tick(), 'launched')
        self.assertEqual(self.sent().count(first), 2)

    def test_a_wait_is_taken_only_for_an_item_the_agent_is_working_and_a_question_that_was_asked(self):
        self.tick()
        key = self.asked(self.items[0])
        with self.assertRaises(SystemExit):
            agent.wait(self.bot, 'card-agent', self.items[2], key)
        with self.assertRaises(SystemExit):
            agent.wait(self.bot, 'card-agent', self.items[0], 'q999')
        self.assertEqual(agent.load(self.bot, 'card-agent', 'waits'), {})

    def test_a_session_does_not_write_the_agents_state_files_by_hand(self):
        self.tick()
        gate = lambda tool, given: hooks.gate_why({'tool_name': tool, 'tool_input': given, 'cwd': str(self.bot), 'session_id': 'w1'})
        for name in ('.trampo/state/agent-card-agent.waits', '.trampo/state/agent-card-agent.pool', 'sessions/agents/card-agent.json'):
            self.assertIn('agent', gate('Write', {'file_path': str(self.bot / name), 'content': '{}'}) or '', name)
            self.assertIn('agent', gate('Bash', {'command': f"echo '{{}}' > {name}"}) or '', name)
        self.assertIsNone(gate('Bash', {'command': 'python3 core/scripts/agent.py --ws . wait card-agent W-1 q1'}))
        self.assertIsNone(gate('Bash', {'command': 'cat .trampo/state/agent-card-agent.waits'}))

    def test_it_has_no_way_to_merge_approve_or_finish_an_item(self):
        for _ in range(4):
            self.tick()
        self.assertTrue(set(self.states().values()) <= {'open', 'in progress'})
        self.assertEqual([r for r in run.slot_rows(self.lead, 'code-host', 'list')], [])
        text = (HERE / 'agent.py').read_text()
        for verb in ('sim-merge', 'sim-approve', "'create'", "'move'", "'resolve'"):
            self.assertNotIn(verb, text)

    def test_a_tracker_that_does_not_answer_is_said_not_guessed_at(self):
        (self.bot / 'slots/tracker').unlink()
        self.assertEqual(self.tick(), 'no-tracker')


class Loop(World):
    SCRIPT = HERE.parent.parent / 'modules/mode-agents/loop/agent-loop.sh'

    def go(self):
        import subprocess
        return subprocess.run([str(self.SCRIPT), str(self.bot), 'tick', 'card-agent'], capture_output=True, text=True,
                              env={**os.environ, 'GIT_CONFIG_GLOBAL': '/dev/null'})

    def test_the_timer_script_runs_a_tick_and_prints_the_one_word_or_what_it_did(self):
        r = self.go()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn('worker started', r.stdout)
        self.assertEqual(self.sent(), self.items[:2])

    def test_the_lock_is_gone_after_every_tick_a_failed_one_included(self):
        import subprocess
        lock = self.bot / '.trampo/state/agent-card-agent.lock'
        self.assertEqual(self.go().returncode, 0)
        self.assertFalse(lock.exists(), 'the lock outlived a tick that passed')
        self.assertEqual(self.go().returncode, 0)
        r = subprocess.run([str(self.SCRIPT), str(self.bot), 'no-such-verb', 'card-agent'], capture_output=True, text=True,
                           env={**os.environ, 'GIT_CONFIG_GLOBAL': '/dev/null'})
        self.assertNotEqual(r.returncode, 0)
        self.assertFalse(lock.exists(), 'the lock outlived a tick that failed')

    def test_a_tick_still_running_makes_the_next_one_exit_without_acting(self):
        (self.bot / '.trampo/state/agent-card-agent.lock').mkdir(parents=True)
        self.assertEqual(self.go().returncode, 0)
        self.assertEqual(self.sent(), [])


class Monitor(World):
    def mon(self, now=None):
        return agent.monitor(self.watch, 'agents-monitor', now)

    def notes(self):
        return [n['text'] for n in run.slot_rows(self.lead, 'ask', 'sim-notes')]

    def test_a_loop_that_stopped_ticking_is_told_to_a_person_once_a_day(self):
        word, _ = self.mon()
        self.assertEqual(word, 'told')
        self.assertIn('card-agent: no tick within twice its interval', self.notes()[0])
        self.assertEqual(self.mon()[0], 'known')
        self.assertEqual(len(self.notes()), 1)
        self.assertEqual(self.mon(time.time() + 25 * 3600)[0], 'told')
        self.assertEqual(len(self.notes()), 2)

    def test_a_trial_tick_says_what_it_would_tell_and_posts_and_remembers_nothing(self):
        import contextlib, io
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(agent.main(['--ws', str(self.watch), 'monitor', 'agents-monitor', '--dry-run']), 0)
        self.assertIn('would tell: card-agent: no tick within twice its interval', out.getvalue())
        self.assertEqual(self.notes(), [])
        self.assertFalse(agent.mark(self.watch, 'agents-monitor', 'told').exists())
        self.assertFalse(agent.mark(self.watch, 'agents-monitor', 'beat').exists())
        self.assertEqual(self.mon()[0], 'told')
        self.assertEqual(len(self.notes()), 1)

    def test_a_beat_inside_twice_the_interval_is_alive_and_a_quiet_monitor_says_so(self):
        agent.mark(self.watch, 'card-agent', 'beat', 'now')
        self.assertEqual(self.mon()[0], 'quiet')
        self.assertEqual(self.notes(), [])

    def test_a_worker_with_no_report_past_its_limit_is_told(self):
        agent.mark(self.watch, 'card-agent', 'beat', 'now')
        old = agent.stamp(time.time() - 9 * 3600)
        agent.mark(self.watch, 'card-agent', 'pool', json.dumps({'W-1': old}))
        self.assertEqual(self.mon()[0], 'told')
        self.assertIn('W-1 has been in progress over 8 hours', self.notes()[0])

    def test_files_left_uncommitted_for_hours_are_told(self):
        agent.mark(self.watch, 'card-agent', 'beat', 'now')
        f = self.watch / 'left.md'
        f.write_text('x\n')
        past = time.time() - 3 * 3600
        os.utime(f, (past, past))
        self.assertEqual(self.mon()[0], 'told')
        self.assertIn('uncommitted for over 1 hours', self.notes()[0])


class SharedState(World):
    """The agent's state travels in the team's repository, so a monitor in another clone reads it."""

    def setUp(self):
        super().setUp()
        top = Path(self.tmp.name)
        (self.bot / 'agents/agents-monitor.yaml').write_text('kind: monitor\nwatches:\n  - card-agent\nstuck_hours: 8\n')
        testenv.sh(top, 'git', 'init', '-q', '--bare', '-b', 'main', str(top / 'origin.git'))
        testenv.sh(self.bot, 'git', 'add', '-A')
        testenv.sh(self.bot, 'git', 'commit', '-q', '-m', 'the workspace')
        testenv.sh(self.bot, 'git', 'remote', 'add', 'origin', str(top / 'origin.git'))
        testenv.sh(self.bot, 'git', 'push', '-q', '-u', 'origin', 'main')
        self.far = top / 'far'
        testenv.sh(top, 'git', 'clone', '-q', str(top / 'origin.git'), str(self.far))
        testenv.sh(self.far, 'git', 'config', 'user.name', 'Mon Agent')
        testenv.sh(self.far, 'git', 'config', 'user.email', 'test@example.invalid')

    def commits(self, where=None):
        return testenv.sh(where or self.bot, 'git', 'log', '--format=%s').splitlines()

    def test_a_tick_that_changed_something_is_one_commit_on_the_teams_copy_and_a_tick_that_did_not_is_none(self):
        before = len(self.commits())
        self.assertEqual(self.tick(), 'launched')
        self.assertEqual(len(self.commits()), before + 1)
        self.assertEqual(self.commits()[0], 'agent card-agent: state')
        self.assertEqual(testenv.sh(self.bot, 'git', 'rev-parse', 'HEAD'), testenv.sh(self.bot, 'git', 'rev-parse', 'origin/main'))
        state = json.loads((self.bot / 'sessions/agents/card-agent.json').read_text())
        self.assertEqual(sorted(state['pool']), sorted(self.items[:2]))
        self.tick()
        self.tick()
        self.assertEqual(len(self.commits()), before + 1)

    def test_a_monitor_in_another_clone_sees_the_agent_it_watches(self):
        said = lambda now: ' '.join(text for _, text, _ in agent.findings(self.far, 'agents-monitor', now))
        self.assertIn('card-agent: no tick within', said(time.time()))
        self.tick()
        self.assertNotIn('no tick within', said(time.time()))
        later = said(time.time() + 9 * 3600)
        self.assertIn('card-agent: no tick within', later)
        self.assertIn(f'{self.items[0]} has been in progress over 8 hours', later)


class ReleaseMonitor(World):
    def setUp(self):
        super().setUp()
        (self.watch / 'agents/release-monitor.yaml').write_text('kind: release\nsystems:\n  - billing\nwindow_hours: 24\n')
        run.slot_rows(self.lead, 'tracker', 'move', self.items[0], 'done')

    def go(self, now=None):
        return agent.release(self.watch, 'release-monitor', now)[0]

    def notes(self):
        return [n['text'] for n in run.slot_rows(self.lead, 'ask', 'sim-notes')]

    def record(self):
        return (self.watch / 'sessions/release-monitor' / f'{self.items[0]}.md').read_text()

    def test_only_a_failing_verdict_is_posted_and_each_failure_once(self):
        run.slot_rows(self.lead, 'monitoring', 'sim-check', 'billing', 'errors', 'passing')
        self.assertEqual(self.go(), 'quiet')
        self.assertEqual(self.notes(), [])
        self.assertIn('Verdict: WATCHING', self.record())
        run.slot_rows(self.lead, 'monitoring', 'sim-check', 'billing', 'errors', 'failing', 'error rate 4 times its baseline')
        self.assertEqual(self.go(), 'told')
        self.assertIn('billing/errors: error rate 4 times its baseline', self.notes()[0])
        self.assertEqual(self.go(), 'quiet')
        self.assertEqual(len(self.notes()), 1)
        self.assertIn('Verdict: FAIL', self.record())

    def test_a_trial_tick_of_the_release_watch_posts_nothing_and_writes_no_record(self):
        run.slot_rows(self.lead, 'monitoring', 'sim-check', 'billing', 'errors', 'failing')
        word, notes = agent.release(self.watch, 'release-monitor', dry=True)
        self.assertEqual(word, 'dry-run')
        self.assertIn('would tell', ' '.join(notes))
        self.assertIn('billing/errors', ' '.join(notes))
        self.assertEqual(self.notes(), [])
        self.assertFalse((self.watch / 'sessions/release-monitor').exists())

    def test_a_system_that_reports_no_checks_is_not_called_passing(self):
        self.assertEqual(self.go(), 'told')
        self.assertIn('reports no checks', self.notes()[0])

    def test_an_item_that_stays_green_for_its_window_ends_as_a_pass_with_no_post(self):
        run.slot_rows(self.lead, 'monitoring', 'sim-check', 'billing', 'errors', 'passing')
        self.go()
        self.assertEqual(self.go(time.time() + 25 * 3600), 'quiet')
        self.assertIn('Verdict: PASS', self.record())
        self.assertEqual(self.notes(), [])


class CreationGate(World):
    SHIPPED = common.parse_yaml((HERE.parent.parent / 'modules/mode-agents/module.md').read_text().split('---')[1])['gates']
    bot_extra = 'gated_commands:\n' + ''.join(f'  {k}: {v}\n' for k, v in SHIPPED.items())

    def why(self, cmd):
        return hooks.gate_why({'tool_name': 'Bash', 'tool_input': {'command': cmd}, 'cwd': str(self.bot), 'session_id': 'b1'})

    def test_the_agents_mode_ships_its_two_gates(self):
        self.assertEqual(list(self.SHIPPED), ['create a tracker item', 'assign an item to an agent'])

    def test_handing_an_item_to_an_agent_waits_for_an_approver_and_handing_it_to_a_person_does_not(self):
        for cmd in ('./slots/tracker assign W-1 Tin Agent', 'python3 core/scripts/slot.py . tracker assign W-1 "Tin Agent"',
                    "./slots/tracker assign W-1 'tin agent'"):
            self.assertIn('assign an item to an agent', self.why(cmd) or '', cmd)
        for cmd in ('./slots/tracker assign W-1 Robin Vale', './slots/tracker claim W-1', './slots/tracker list --assignee "Tin Agent"'):
            self.assertIsNone(self.why(cmd), cmd)
        (self.bot / 'agents/card-agent.yaml').unlink()
        self.assertIsNone(self.why('./slots/tracker assign W-1 Tin Agent'))

    def test_the_gate_the_agents_mode_ships_holds_every_way_of_creating_an_item_and_no_read(self):
        for cmd in ('python3 core/scripts/slot.py . tracker create drafts/one.md', './slots/tracker create drafts/one.md'):
            self.assertIn('create a tracker item', self.why(cmd) or '', cmd)
        for cmd in ('python3 core/scripts/slot.py . tracker list', './slots/tracker read W-1', 'cat drafts/one.md'):
            self.assertIsNone(self.why(cmd), cmd)

    def test_the_gates_read_a_slot_call_the_way_the_slot_runner_parses_it(self):
        for cmd in ('python3 core/scripts/slot.py . tracker assign W-1 --timeout 5 Tin Agent',
                    'python3 core/scripts/slot.py . tracker assign --timeout 5 W-1 "Tin Agent"',
                    'python3 core/scripts/slot.py "my ws" tracker assign W-1 Tin Agent'):
            self.assertIn('assign an item to an agent', self.why(cmd) or '', cmd)
        for cmd in ('python3 core/scripts/slot.py "my ws" tracker create drafts/one.md',
                    'python3 core/scripts/slot.py "my ws" tracker create --timeout 5 drafts/one.md'):
            self.assertIn('create a tracker item', self.why(cmd) or '', cmd)
        self.assertIsNone(self.why('python3 core/scripts/slot.py . tracker assign W-1 --timeout 5 Robin Vale'))

    def test_an_assignee_the_shell_has_yet_to_work_out_needs_the_approval_too(self):
        for who in ('"$WHO"', '`cat who.txt`', '$(cat who.txt)', 'Tin*', '~/who'):
            self.assertIn('assign an item to an agent', self.why(f'./slots/tracker assign W-1 {who}') or '', who)

    def slot(self, *call, session='b1'):
        import contextlib, io, slot
        marks = {'CLAUDE_CODE_SESSION_ID': session} if session else {}
        with mock.patch.dict(os.environ, marks), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
            return slot.main([str(self.bot), 'tracker', *call]), err.getvalue()

    def test_the_slot_runner_itself_refuses_a_gated_call_the_session_holds_no_yes_for(self):
        import contextlib, io, event
        item = self.items[0]
        run.slot_rows(self.lead, 'tracker', 'assign', item, 'Robin Vale')
        owner = lambda: {r['id']: r['assignee'] for r in run.slot_rows(self.lead, 'tracker', 'list')}[item]
        code, said = self.slot('assign', item, 'Tin Agent')
        self.assertEqual(code, 2)
        self.assertIn('assign an item to an agent', said)
        self.assertEqual(owner(), 'Robin Vale')
        with contextlib.redirect_stdout(io.StringIO()):
            event.main(['open', '--ws', str(self.bot), '--kind', 'adhoc', '--subject', item, '--session', 'b1'])
        self.assertEqual(self.slot('assign', item, 'Tin Agent')[0], 2)
        common.append(self.bot, common.active(self.bot, 'b1')[0], {'ev': 'approve', 'gate': 'assign an item to an agent', 'key': item,
                                                                   'by': 'Robin Vale', 'via': 'typed'})
        self.assertEqual(self.slot('assign', item, 'Tin Agent')[0], 0)
        self.assertEqual(owner(), 'Tin Agent')
        self.assertEqual(self.slot('assign', self.items[1], 'Tin Agent')[0], 2)
        self.assertEqual(self.slot('assign', self.items[1], 'Robin Vale')[0], 0)
        self.assertEqual(self.slot('assign', self.items[2], 'Tin Agent', session=None)[0], 0)

    def test_setup_writes_a_modes_own_gates_once_the_slot_is_filled(self):
        setup = ' '.join((HERE.parent / 'skills/setup/SKILL.md').read_text().split())
        self.assertIn('under `gates:` in its `module.md`', setup)
        self.assertIn('as soon as the slot it names is filled', setup)


class Health(World):
    def test_an_agent_that_is_also_an_approver_fails_the_health_check(self):
        cfg = self.lead / 'workspace.yaml'
        cfg.write_text(cfg.read_text().replace('- Robin Vale', '- Robin Vale\n  - Tin Agent'))
        (self.lead / 'agents').mkdir()
        (self.lead / 'agents/card-agent.yaml').write_text('kind: card\nassignee: Tin Agent\nlaunch: agents/launch.sh\n')
        fails, _ = doctor.check(self.lead)
        self.assertTrue(any('Tin Agent is an approver and also an agent' in f for f in fails), fails)


if __name__ == '__main__':
    unittest.main()
