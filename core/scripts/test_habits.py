#!/usr/bin/env python3
"""The habits a hook keeps: one touch per prompt with where the prompt came from, a "Needs you" item that carries its
own consequence, the memory routes and gate rules said at every start, and the seeds a new workspace begins with."""
import contextlib
import io
import json
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
import event  # noqa: E402
import hooks  # noqa: E402

SEEDS = HERE.parent / 'seeds'


def prompt(pid, text='carry on', **extra):
    return {'type': 'user', 'promptId': pid, 'message': {'content': text}, **extra}


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.top = Path(self.tmp.name)
        self.ws = testenv.workspace(self.top / 'ws')

    def tearDown(self):
        self.tmp.cleanup()

    def open(self, subject='refund-letter', session='c1'):
        with contextlib.redirect_stdout(io.StringIO()):
            event.main(['open', '--ws', str(self.ws), '--kind', 'card', '--subject', subject, '--session', session])
        return common.active(self.ws, session)[0]

    def touches(self, sid):
        return [e for e in common.session_events(self.ws, sid) if e.get('ev') == 'touch']

    def lines(self, *rows):
        f = self.top / 't.jsonl'
        f.write_text(''.join(json.dumps(r) + '\n' for r in rows))
        return str(f)


class PromptClass(unittest.TestCase):
    def test_a_prompt_is_classed_by_what_its_transcript_line_says(self):
        for row, want in ((prompt('p', origin={'kind': 'human'}), 'human'),
                          (prompt('p', origin={'kind': 'peer'}), 'peer'),
                          (prompt('p', origin={'kind': 'task-notification'}), 'notification'),
                          (prompt('p', scheduledTaskId='t1'), 'loop'),
                          (prompt('p', '<task-notification>done</task-notification>'), 'notification'),
                          (prompt('p'), 'human'),
                          (prompt('p', '/compact'), None),
                          (prompt('p', isMeta=True), None),
                          (prompt('p', isCompactSummary=True), None),
                          ({'type': 'user', 'promptId': 'p', 'message': {'content': [{'type': 'tool_result', 'content': 'x'}]}}, None)):
            self.assertEqual(hooks.prompt_class(row), want, row)


class Touch(Case):
    def test_no_open_session_means_no_touch_and_no_file(self):
        hooks.touch({'cwd': str(self.ws), 'session_id': 'c1'})
        self.assertEqual(common.ledger_files(self.ws), [])

    def test_a_sitting_with_no_record_is_told_to_open_one_until_it_has(self):
        said = (hooks.touch({'cwd': str(self.ws), 'session_id': 'q1'}) or {}).get('say', '')
        self.assertIn('no record is open for this sitting', said)
        self.assertIn('kind adhoc', said)
        with contextlib.redirect_stdout(io.StringIO()):
            event.main(['open', '--ws', str(self.ws), '--kind', 'adhoc', '--subject', 'opening-hours', '--session', 'q1'])
        self.assertIsNone(hooks.touch({'cwd': str(self.ws), 'session_id': 'q1'}))
        hooks.gate_why({'tool_name': 'Bash', 'tool_input': {'command': 'ls'}, 'cwd': str(self.ws), 'session_id': 'q1'})
        with contextlib.redirect_stdout(io.StringIO()):
            event.main(['close', '--ws', str(self.ws), '--outcome', 'no-action', '--session', 'q1'])
        self.assertIsNone(hooks.touch({'cwd': str(self.ws), 'session_id': 'q1'}))
        self.assertIn('leaves a record', (HERE.parent / 'seeds/AGENTS.md').read_text())
        self.assertNotIn('is just a question', (HERE.parent / 'seeds/AGENTS.md').read_text())

    def test_a_prompt_with_no_transcript_is_one_untagged_touch_of_unknown_origin(self):
        sid = self.open()
        self.assertIsNone(hooks.touch({'cwd': str(self.ws), 'session_id': 'c1'}))
        (t,) = self.touches(sid)
        self.assertEqual((t['cause'], t['kind'], t['who'], t.get('prompt_origin')), ('untagged', 'card', 'Robin Vale', None))

    def test_the_origin_is_read_from_the_prompts_own_line_past_the_offset(self):
        sid = self.open()
        path = self.lines(prompt('p0', origin={'kind': 'human'}), prompt('p1', origin={'kind': 'peer'}))
        hooks.resolve_touch(str(self.ws), sid, 'card', path, 'p1', '0', '2026-01-05T09:00:00Z', wait=0)
        (t,) = self.touches(sid)
        self.assertEqual((t['prompt_origin'], t['ts'], t['cause']), ('peer', '2026-01-05T09:00:00Z', 'untagged'))

    def test_a_prompt_with_no_class_is_not_a_touch_and_an_unseen_one_is_a_touch_of_unknown_origin(self):
        sid = self.open()
        path = self.lines(prompt('p1', '/compact'))
        hooks.resolve_touch(str(self.ws), sid, 'card', path, 'p1', '0', '2026-01-05T09:00:00Z', wait=0)
        self.assertEqual(self.touches(sid), [])
        hooks.resolve_touch(str(self.ws), sid, 'card', path, 'p2', '0', '2026-01-05T09:01:00Z', wait=0)
        self.assertNotIn('prompt_origin', self.touches(sid)[0])

    def test_a_prompt_with_a_transcript_is_resolved_by_a_detached_child_so_the_prompt_never_waits(self):
        sid, seen = self.open(), []
        path = self.lines(prompt('p0'))
        with mock.patch.object(hooks, 'detach', lambda argv, log: seen.append(argv)):
            hooks.touch({'cwd': str(self.ws), 'session_id': 'c1', 'transcript_path': path, 'prompt_id': 'p1'})
        self.assertEqual(self.touches(sid), [])
        self.assertEqual(seen[0][3:9], ['touch-resolve', str(self.ws), sid, 'card', path, 'p1'])
        self.assertEqual(int(seen[0][9]), Path(path).stat().st_size)

    def test_only_a_persons_prompts_wait_for_a_cause_at_close(self):
        sid = self.open()
        for origin in ('human', 'human', 'loop', 'notification', None):
            hooks.write_touch(self.ws, sid, 'card', origin, None)
        self.assertEqual(event.untagged(common.session_events(self.ws, sid)), 3)
        said = '\n'.join(event.report(self.ws))
        self.assertIn('prompts by origin: human 2, loop 1, notification 1, unknown 1', said)


SHAPED = """**Closed the refund letter.**

**Needs you:**
{items}

**What changed**
The letter went out.
"""


class NeedsYou(Case):
    def stop(self, text, **extra):
        return hooks.needs_you({'cwd': str(self.ws), 'session_id': 'c1', 'last_assistant_message': text, **extra})

    def test_a_bare_question_in_needs_you_blocks_the_stop_and_names_the_item(self):
        found = self.stop(SHAPED.format(items='1. The draft is in sessions/refund-letter.\n2. Should I send it today?'))
        self.assertIn('2. Should I send it today?', found['block'])
        self.assertNotIn('1. The draft', found['block'])

    def test_an_item_that_carries_its_consequence_passes(self):
        for item in ('1. Send it today: yes posts it before the deadline, no waits to Monday. Your call.',
                     '1. Which way do I go on the wording? I recommend the short one because the long one repeats the offer.',
                     'nothing'):
            self.assertIsNone(self.stop(SHAPED.format(items=item)), item)

    def test_the_shapes_the_rule_was_first_written_for(self):
        for text in ('**Needs you:**\n1. Should I redeploy the test site after the rebase?\n\nDetail below.',
                     '**\u2b50\ufe0f Needs you:** Do you want the eight-digit table used as-is?',
                     '**Needs you:**\n1. Send the first review now.\n2. Shall I retarget the second off the merged branch?'):
            self.assertTrue(hooks.bare_asks(text), text)
        for text in ('**Needs you:** nothing for this QA pass.',
                     '**Needs you:** Review the privacy failures below before sharing.',
                     '**Needs you:**\n1. Should I redeploy? Yes costs one pipeline run, no leaves the gate detached from the head.',
                     '**Needs you:** nothing.\n\n**Detail**\nShould I have run the suite here?'):
            self.assertEqual(hooks.bare_asks(text), [], text)

    def test_a_question_on_the_header_line_with_no_list_is_an_item_too(self):
        self.assertTrue(self.stop('**Done.**\n\n**Needs you:** want me to send it?\n'))

    def test_no_needs_you_block_and_a_second_stop_are_let_through(self):
        self.assertIsNone(self.stop('Sent. Should I also file it?'))
        self.assertIsNone(self.stop(SHAPED.format(items='1. Should I send it?'), stop_hook_active=True))

    def test_the_last_reply_is_read_from_the_transcript_when_the_event_carries_none(self):
        path = testenv.transcript(self.top / 't.jsonl', ('agent-said', SHAPED.format(items='1. Can I delete the old drafts?')),
                                  ('wrote', self.ws / 'a.md'))
        self.assertTrue(hooks.needs_you({'cwd': str(self.ws), 'transcript_path': path}))

    def test_each_turn_with_a_block_leaves_one_log_row_and_log_mode_never_blocks(self):
        self.stop(SHAPED.format(items='1. Should I send it?'))
        rows = [json.loads(l) for l in (common.state_dir(self.ws) / 'hook-log.jsonl').read_text().splitlines()]
        self.assertEqual([(r['hook'], r['verdict'], r['blocked'], r['items']) for r in rows], [('needs-you', 'bare-ask', True, 1)])
        (self.ws / 'workspace.yaml').write_text((self.ws / 'workspace.yaml').read_text() + 'hooks:\n  needs-you: log\n')
        self.assertIsNone(self.stop(SHAPED.format(items='1. Should I send it?')))


class Index(Case):
    def test_the_start_says_the_category_routes_and_each_gate_rule(self):
        (self.ws / 'memory.md').write_text('# Memory\n\nintro\n\n## Categories\n\n| Category | Index | Read trigger |\n| --- | --- | --- |\n'
                                           '| shared | memory/shared/shared.md | always |\n\n## Other\n\nnot said\n')
        (self.ws / 'memory/shared').mkdir(parents=True)
        (self.ws / 'memory/shared/approval-gates.md').write_text(
            '# Gates\n\n## Sending to a client waits (2026-01-05)\n\nLong story.\n\n**How to apply:** draft, show, wait.\nSecond line.\n\nMore story.\n')
        said = hooks.index({'cwd': str(self.ws)})['say']
        self.assertIn('| shared | memory/shared/shared.md | always |', said)
        self.assertIn('### Sending to a client waits (2026-01-05)\n**How to apply:** draft, show, wait.\nSecond line.', said)
        self.assertNotIn('not said', said)
        self.assertNotIn('story', said)

    def test_a_missing_file_is_said_and_never_stops_the_session(self):
        said = hooks.index({'cwd': str(self.ws)})['say']
        self.assertIn('memory.md not found', said)
        self.assertIn('approval-gates.md not found', said)
        self.assertIsNone(hooks.index({'cwd': str(self.top)}))


class Seeds(Case):
    def seeded(self):
        shutil.copytree(SEEDS, self.ws, dirs_exist_ok=True)
        text = (self.ws / 'workspace.yaml').read_text().replace('approvers: []', 'approvers:\n  - Robin Vale')
        (self.ws / 'workspace.yaml').write_text(text)
        return self.ws

    def test_a_workspace_made_from_the_seeds_is_healthy_and_pins_the_running_core(self):
        self.assertEqual(doctor.check(self.seeded()), ([], []))
        self.assertEqual(str(common.config(self.ws)['core_version']), common.core_version())

    def test_the_seeds_carry_the_four_categories_the_registers_and_the_refusals(self):
        for rel in ('memory.md', 'memory/shared/shared.md', 'memory/dev/dev.md', 'memory/support/support.md', 'memory/review/review.md',
                    'memory/shared/approval-gates.md', 'memory/shared/verification-method.md', 'memory/shared/known-issues.md',
                    'memory/shared/grants.md', 'people/README.md', 'constitution.md', 'AGENTS.md', '.gitignore'):
            self.assertTrue((SEEDS / rel).is_file(), rel)
        ignored = (SEEDS / '.gitignore').read_text()
        for word in ('.trampo/state/', '*.pdf', '*.zip', '*.png'):
            self.assertIn(word, ignored)

    def test_an_urgent_out_of_scope_finding_goes_to_a_person_now_and_is_still_not_fixed_in_the_work(self):
        core = HERE.parent
        for rel in ('constitution.md', 'protocols/write.md', 'seeds/AGENTS.md', 'seeds/memory/shared/known-issues.md',
                    'skills/session/SKILL.md'):
            text = ' '.join((core / rel).read_text().split())
            self.assertIn('live exposure', text, rel)
            self.assertIn('escalated', text, rel)
        self.assertIn('`escalated (<to whom, when>)`', (core / 'seeds/memory/shared/known-issues.md').read_text())

    def test_the_start_names_a_memory_file_that_is_in_no_index(self):
        ws = self.seeded()
        self.assertNotIn('in no index', hooks.index({'cwd': str(ws)})['say'])
        (ws / 'memory/shared/supplier-addresses.md').write_text('# Supplier addresses\n')
        (ws / 'memory/archive').mkdir(exist_ok=True)
        (ws / 'memory/archive/old.md').write_text('# Old\n')
        said = hooks.index({'cwd': str(ws)})['say']
        self.assertIn('in no index', said)
        self.assertIn('memory/shared/supplier-addresses.md', said)
        self.assertNotIn('archive/old.md', said)

    def test_the_seeded_index_and_gate_rules_are_what_the_start_says(self):
        said = hooks.index({'cwd': str(self.seeded())})['say']
        self.assertIn('memory/shared/shared.md', said)
        self.assertIn('**How to apply:**', said)
        self.assertNotIn('not found', said)

    def test_size_and_routing_only_warn(self):
        ws = self.seeded()
        (ws / 'memory/dev/loose.md').write_text('# Loose\n\n' + 'word ' * 2000)
        fails, warns = doctor.check(ws)
        self.assertEqual(fails, [])
        self.assertEqual(len([w for w in warns if 'loose.md' in w]), 2)


class Schema(unittest.TestCase):
    def test_the_published_lists_are_the_lists_the_code_checks(self):
        props = json.loads((HERE.parent / 'schemas' / 'event.schema.json').read_text())['properties']
        for field, want in (('kind', event.KINDS), ('ev', (*event.EVS, *event.OWN_WRITER)), ('cause', event.CAUSES), ('ask', event.ASKS),
                            ('source', event.SOURCES), ('prior', event.PRIORS), ('outcome', event.OUTCOMES),
                            ('prompt_origin', hooks.PROMPT_CLASSES)):
            self.assertEqual(props[field]['enum'], list(want), field)


class FileTypes(Case):
    def test_a_document_archive_or_screenshot_git_would_take_is_a_warning(self):
        (self.ws / 'memory.md').write_text('# Memory\n')
        for name in ('export.pdf', 'bundle.zip', 'screen.png'):
            (self.ws / name).write_bytes(b'x')
        warns = doctor.check(self.ws)[1]
        self.assertEqual(len([w for w in warns if 'never go into git' in w]), 3)
        (self.ws / '.gitignore').write_text('.trampo/state/\n*.pdf\n*.zip\n*.png\n')
        self.assertEqual([w for w in doctor.check(self.ws)[1] if 'never go into git' in w], [])


class Backstops(Case):
    def test_a_gated_action_with_no_backstop_named_is_a_warning_until_one_is(self):
        (self.ws / 'memory.md').write_text('# Memory\n')
        cfg = self.ws / 'workspace.yaml'
        cfg.write_text(cfg.read_text() + 'gated_commands:\n  send to a client: deliver\\.sh\n  release: release\\.sh\n'
                                         'backstops:\n  release: the release account is held by two named people\n')
        warns = [w for w in doctor.check(self.ws)[1] if 'backstop' in w]
        self.assertEqual(len(warns), 1, warns)
        self.assertIn('send to a client', warns[0])

    def test_a_backstop_recorded_as_nothing_yet_is_still_a_warning(self):
        (self.ws / 'memory.md').write_text('# Memory\n')
        cfg = self.ws / 'workspace.yaml'
        cfg.write_text(cfg.read_text() + 'gated_commands:\n  send to a client: deliver\\.sh\n  release: release\\.sh\n  refund: refund\\.sh\n'
                                         'backstops:\n  send to a client: Nothing yet.\n  release: none\n'
                                         '  refund: nothing reaches the bank without the second signer\n')
        warns = [w for w in doctor.check(self.ws)[1] if 'backstop' in w]
        self.assertEqual(len(warns), 2, warns)
        self.assertIn('recorded as "Nothing yet."', ' '.join(warns))
        self.assertNotIn('refund', ' '.join(warns))


class Release(unittest.TestCase):
    ROOT = HERE.parent.parent

    def test_the_version_is_one_number_in_every_manifest_and_the_seed(self):
        self.assertEqual(testenv.VERSION, '0.5.0')
        self.assertIn(f'core_version: {testenv.VERSION}\n', (SEEDS / 'workspace.yaml').read_text())
        self.assertIn(f'Status: {testenv.VERSION}', (self.ROOT / 'README.md').read_text())

    def test_ci_runs_every_suite_by_discovery_with_git_isolated(self):
        ci = (self.ROOT / '.github/workflows/ci.yml').read_text()
        self.assertIn("python3 -B -m unittest discover -p 'test_*.py'", ci)
        self.assertIn('GIT_CONFIG_GLOBAL=/dev/null', ci)

    def test_setup_asks_what_each_decision_needs(self):
        setup = (HERE.parent / 'skills/setup/SKILL.md').read_text()
        for words in ('Approvers', 'gated_commands:', 'backstop for each gated action', 'pass a review before they take effect',
                      'outside: ask-first', 'Slots', 'Standing grants', 'Size prompts', 'seeds/'):
            self.assertIn(words, setup, words)

    def test_the_review_cadence_is_a_setting_setup_asks_for(self):
        seed = (SEEDS / 'workspace.yaml').read_text()
        self.assertRegex(seed, r'(?m)^retro:\n  every_days: 7\n  window_days: 14$')
        setup = (HERE.parent / 'skills/setup/SKILL.md').read_text()
        self.assertIn('retro.every_days', setup)
        self.assertIn('EV stats', (HERE.parent / 'skills/retro/SKILL.md').read_text())

    def test_the_release_notes_say_what_changed_how_to_upgrade_and_what_is_new(self):
        notes = (self.ROOT / 'docs/decisions.md').read_text()
        at = notes.index('## Release 0.3')
        for head in ('### What changed and why', '### Upgrading from 0.2.8', '### Why the hooks are Python',
                     '### Every hook is a check against a confused assistant', '### What is new relative to the reference',
                     '### Enforced and prose'):
            self.assertIn(head, notes[at:], head)

    def test_no_document_describes_a_removed_command(self):
        gone = ('event.py approve ', 'event.py approved', 'event.py show', 'event.py prefer', 'event.py sync', 'decline-gate',
                'propose-gate', 'records/<mode>', '120 words', 'live:')
        for top in ('core', 'modules'):
            for f in (self.ROOT / top).rglob('*.md'):
                text = f.read_text()
                for word in gone:
                    self.assertNotIn(word, text, f'{f.relative_to(self.ROOT)}: {word}')
        for name in ('README.md', 'AGENTS.md'):
            for word in gone:
                self.assertNotIn(word, (self.ROOT / name).read_text(), f'{name}: {word}')


if __name__ == '__main__':
    unittest.main()
