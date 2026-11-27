#!/usr/bin/env python3
"""The ledger: what emit writes and refuses, the done rule, open and close, the report, and the journal that
storage: files keeps."""
import contextlib
import io
import json
import os
import sys
import time
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import testenv  # noqa: E402
import common  # noqa: E402
import event  # noqa: E402


class Case(unittest.TestCase):
    storage = 'git'

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = str(testenv.workspace(Path(self.tmp.name) / 'ws', self.storage))

    def tearDown(self):
        self.tmp.cleanup()

    def run_cmd(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            event.main([args[0], '--ws', self.ws, *args[1:]])
        return out.getvalue()

    def emit(self, *args, sid='s1', kind='adhoc'):
        return self.run_cmd('emit', '--sid', sid, '--kind', kind, *args)

    def events(self, sid='s1'):
        return common.session_events(self.ws, sid)

    def refused(self, *args, **kw):
        before = len(common.load_events(self.ws)[0])
        with self.assertRaises(SystemExit) as cm:
            self.emit(*args, **kw)
        self.assertNotIn(cm.exception.code, (0, None))
        self.assertEqual(len(common.load_events(self.ws)[0]), before)
        return str(cm.exception.code)


class Emit(Case):
    def test_a_start_carries_who_from_git_the_subject_and_the_running_version(self):
        self.emit('--ev', 'start', '--subject', 'billing-export', '--source', 'person')
        e = self.events()[0]
        self.assertEqual((e['ev'], e['kind'], e['subject'], e['who'], e['source']), ('start', 'adhoc', 'billing-export', 'Robin Vale', 'person'))
        self.assertEqual(e['core_version'], testenv.VERSION)
        self.assertTrue(e['event_id'] and e['ts'].endswith('Z'))

    def test_an_end_needs_a_start_and_an_outcome_from_the_list(self):
        self.assertIn('no start', self.refused('--ev', 'end', '--outcome', 'abandoned'))
        self.emit('--ev', 'start')
        self.refused('--ev', 'end')
        self.refused('--ev', 'end', '--outcome', 'finished')
        self.emit('--ev', 'end', '--outcome', 'abandoned')
        self.assertIn('already ended', self.refused('--ev', 'end', '--outcome', 'abandoned'))

    def test_done_needs_how_the_goal_was_checked_and_nothing_else_takes_it(self):
        self.emit('--ev', 'start')
        self.assertIn('--goal-met', self.refused('--ev', 'end', '--outcome', 'done'))
        self.refused('--ev', 'end', '--outcome', 'done', '--goal-met', '  ')
        self.refused('--ev', 'end', '--outcome', 'parked', '--goal-met', 'ran it')
        self.emit('--ev', 'end', '--outcome', 'done', '--goal-met', 'the requester opened the export and the totals match')
        self.assertEqual(self.events()[-1]['goal_met'], 'the requester opened the export and the totals match')

    def test_a_block_needs_a_real_cause(self):
        self.emit('--ev', 'start')
        self.refused('--ev', 'block')
        self.refused('--ev', 'block', '--cause', 'untagged')
        self.emit('--ev', 'block', '--cause', 'approval-gate', '--ask', 'grant', '--note', 'waits for an approver')
        self.assertEqual(self.events()[-1]['ask'], 'grant')

    def test_field_shapes_are_checked(self):
        self.emit('--ev', 'start')
        self.refused('--ev', 'touch', '--cause', 'direction', '--subtag', 'x' * 41)
        self.refused('--ev', 'clear', '--subtag', 'late')
        self.refused('--ev', 'touch', '--note', 'n' * 141)
        self.refused('--ev', 'touch', '--fp', 'no-colon')
        self.refused('--ev', 'touch', '--ask', 'grant')
        self.refused('--ev', 'wrong', '--what', 'direction')
        self.refused('--ev', 'touch', '--what', 'direction', '--severity', 'quality')
        self.refused('--ev', 'usage')
        self.refused('--ev', 'spawn', '--effort', 'heroic')
        self.emit('--ev', 'touch', '--cause', 'direction', '--by', 'agent', '--fp', 'exports:wrong-total', '--prior', 'found')
        self.emit('--ev', 'wrong', '--what', 'action', '--severity', 'quality')
        self.emit('--ev', 'usage', '--usage', '{"turns": 4, "cost_usd": null}')
        self.assertEqual(self.events()[-1]['usage']['turns'], 4)

    def test_lines_only_a_hook_or_the_journal_writes_are_never_emitted_by_hand(self):
        self.emit('--ev', 'start')
        for ev in ('approve', 'write', 'remove'):
            with self.assertRaises(SystemExit):
                self.emit('--ev', ev)

    def test_who_on_a_shared_folder_is_the_declared_name(self):
        ws = str(testenv.workspace(Path(self.tmp.name) / 'files', 'files'))
        with mock.patch.dict(os.environ, {'TRAMPO_USER': 'Sam Okoro'}):
            event.main(['emit', '--ws', ws, '--sid', 's1', '--kind', 'adhoc', '--ev', 'start'])
        self.assertEqual(common.session_events(ws, 's1')[0]['who'], 'Sam Okoro')


class OpenClose(Case):
    def open(self, subject='billing-export', kind='adhoc', session='c1', *more):
        return self.run_cmd('open', '--kind', kind, '--subject', subject, '--session', session, *more).strip()

    def test_open_starts_a_ledger_and_names_it_for_the_prompt_hook(self):
        sid = self.open().split()[1]
        self.assertRegex(sid, r'^billing-export-\d{8}T\d{4}')
        self.assertEqual(common.active(self.ws, 'c1'), (sid, 'adhoc'))
        self.assertEqual([e['ev'] for e in self.events(sid)], ['start'])

    def test_a_session_left_open_is_resumed_under_its_own_sid_with_nothing_written(self):
        sid = self.open().split()[1]
        self.run_cmd('close', '--session', 'c1', '--park', '--cause', 'approval-gate', '--note', 'waits for Robin')
        self.assertEqual(common.active(self.ws, 'c1'), (sid, 'adhoc'))
        again = self.open('billing-export', 'adhoc', 'c2')
        self.assertEqual(again.split()[:2], ['resumed', sid])
        self.assertEqual([e['ev'] for e in self.events(sid)], ['start', 'block'])

    def test_after_an_end_the_subject_gets_a_new_sid_that_names_the_last_one(self):
        sid = self.open().split()[1]
        self.run_cmd('close', '--session', 'c1', '--outcome', 'no-action')
        self.assertIsNone(common.active(self.ws, 'c1'))
        with mock.patch.object(event, 'stamp', return_value='20990101T0000'):
            new = self.open('billing-export', 'adhoc', 'c2').split()[1]
        self.assertNotEqual(new, sid)
        self.assertEqual(self.events(new)[0]['note'], f'resumes {sid}')

    def test_open_refuses_to_file_one_assistant_session_under_two_subjects(self):
        self.open()
        with self.assertRaises(SystemExit) as cm:
            self.open('other-subject')
        self.assertIn('already files under', str(cm.exception.code))

    def test_close_is_safe_to_run_twice_and_keeps_the_done_rule(self):
        self.open()
        with self.assertRaises(SystemExit):
            self.run_cmd('close', '--session', 'c1', '--outcome', 'done')
        self.run_cmd('close', '--session', 'c1', '--outcome', 'done', '--goal-met', 'the totals match the bank file')
        self.assertIn('nothing to close', self.run_cmd('close', '--session', 'c1', '--outcome', 'done', '--goal-met', 'x'))

    def test_close_says_how_many_prompts_are_still_untagged(self):
        sid = self.open().split()[1]
        for _ in range(3):
            common.append(self.ws, sid, {'kind': 'adhoc', 'ev': 'touch', 'cause': 'untagged', 'prompt_origin': 'human'})
        self.emit('--ev', 'touch', '--cause', 'direction', '--by', 'agent', sid=sid)
        self.assertIn('2 untagged', self.run_cmd('close', '--session', 'c1', '--outcome', 'abandoned'))


class CardClose(Case):
    open = OpenClose.open
    """A card that closes as done says what it learned about the systems and where that now lives."""
    DONE = ('close', '--session', 'c1', '--outcome', 'done', '--goal-met', 'the export matches the bank file')

    def card(self, line, runbooks=True, qa='# QA\n\nVerdict: PASS\n'):
        self.open('item-12', 'card')
        ws = Path(self.ws)
        (ws / 'sessions/item-12').mkdir(parents=True)
        if qa is not None:
            (ws / 'sessions/item-12/qa-report.md').write_text(qa)
        (ws / 'sessions/item-12/session.md').write_text(f'# item-12\n\n## Close-out\n\n{line}\n')
        if runbooks:
            (ws / 'runbooks/systems').mkdir(parents=True)
            (ws / 'runbooks/systems/billing.md').write_text('# billing\n')

    def refused(self):
        with self.assertRaises(SystemExit):
            self.run_cmd(*self.DONE)

    def test_a_done_card_with_no_runbook_line_closes_with_a_warning_naming_the_line(self):
        self.card('nothing here')
        out = self.run_cmd(*self.DONE)
        self.assertIn('closed', out)
        self.assertIn('warning: sessions/item-12/session.md has no "runbook:" line', out)

    def test_the_template_placeholder_left_in_place_is_a_warning_too(self):
        self.card('runbook: <paths of the runbooks changed | none learned>')
        out = self.run_cmd(*self.DONE)
        self.assertIn('closed', out)
        self.assertIn('warning:', out)

    def test_a_clean_line_closes_without_a_warning(self):
        self.card('runbook: none learned')
        self.assertNotIn('warning', self.run_cmd(*self.DONE))

    def test_none_learned_or_the_runbooks_that_changed_close_it(self):
        self.card('runbook: none learned')
        self.assertIn('closed', self.run_cmd(*self.DONE))

    def test_a_named_runbook_must_be_a_file_under_runbooks(self):
        self.card('runbook: runbooks/systems/ledger.md')
        self.refused()

    def test_named_runbooks_that_exist_close_it(self):
        self.card('runbook: runbooks/systems/billing.md, `runbooks/systems/billing.md`')
        self.assertIn('closed', self.run_cmd(*self.DONE))

    def test_with_no_runbooks_folder_the_line_says_where_the_facts_were_left(self):
        self.card('runbook: left in sessions/item-12/session.md, the team has no runbooks', runbooks=False)
        self.assertIn('closed', self.run_cmd(*self.DONE))

    def test_the_card_mode_and_its_record_template_carry_the_step(self):
        card = Path(__file__).resolve().parent.parent.parent / 'modules/mode-card'
        mode = ' '.join((card / 'seeds/modes/card.md').read_text().split())
        for words in ('System facts go to the runbooks', 'runbook: none learned', '_(verify)_', 'not-yet-replayed', 'runbook: left in'):
            self.assertIn(words, mode)
        self.assertNotIn('qa/runbooks', mode)
        self.assertIn('\nrunbook: <', (card / 'templates/session.md').read_text())

    def test_a_park_and_another_kind_of_session_are_not_asked(self):
        self.card('nothing here')
        self.assertIn('parked', self.run_cmd('close', '--session', 'c1', '--park', '--cause', 'approval-gate', '--note', 'waits'))
        self.open('a-question', 'adhoc', 'c2')
        self.assertIn('closed', self.run_cmd('close', '--session', 'c2', '--outcome', 'no-action'))


class QaBeforeDone(Case):
    open, card, DONE = OpenClose.open, CardClose.card, CardClose.DONE
    """A card closes as done only with a last QA verdict of PASS in its QA report."""

    def close(self, qa):
        self.card('runbook: none learned', qa=qa)
        return self.run_cmd(*self.DONE)

    def refused_for(self, qa, words):
        self.card('runbook: none learned', qa=qa)
        with self.assertRaises(SystemExit) as cm:
            self.run_cmd(*self.DONE)
        self.assertIn(words, str(cm.exception.code))

    def test_a_pass_closes_it(self):
        self.assertIn('closed', self.close('# QA\n\n## Pass 1\n\nVerdict: PASS\n'))

    def test_no_report_is_refused_with_what_to_do(self):
        self.refused_for(None, 'sessions/item-12/qa-report.md is missing')

    def test_a_report_with_no_verdict_line_is_refused(self):
        self.refused_for('# QA\n\nall good, verdict PASS in my view\n', 'no line "Verdict: PASS"')

    def test_fail_and_cannot_verify_are_refused(self):
        self.refused_for('Verdict: FAIL\n', 'FAIL')

    def test_cannot_verify_is_refused(self):
        self.refused_for('Verdict: CANNOT-VERIFY\n', 'CANNOT-VERIFY')

    def test_the_last_verdict_wins(self):
        self.refused_for('Verdict: PASS\n\n## Pass 2\n\nVerdict: FAIL\n', 'FAIL')

    def test_a_later_pass_after_a_fail_closes_it(self):
        self.assertIn('closed', self.close('Verdict: FAIL\n\n## Pass 2\n\nVerdict: PASS\n'))

    def test_a_last_verdict_line_that_is_not_one_of_the_three_words_is_refused(self):
        self.refused_for('Verdict: PASS\nVerdict: PASS with two open points\n', 'is not one of')

    def test_the_templates_placeholder_is_no_verdict(self):
        self.refused_for('Verdict: <PASS | FAIL | CANNOT-VERIFY>\n', 'is not one of')

    def test_the_word_is_read_exactly(self):
        self.refused_for('Verdict: pass\n', 'is not one of')

    def test_a_park_and_an_adhoc_session_are_not_asked_for_qa(self):
        self.card('runbook: none learned', qa=None)
        self.assertIn('parked', self.run_cmd('close', '--session', 'c1', '--park', '--cause', 'approval-gate', '--note', 'waits'))
        self.open('a-question', 'adhoc', 'c2')
        self.assertIn('closed', self.run_cmd('close', '--session', 'c2', '--outcome', 'done', '--goal-met', 'answered'))


class QaSkipped(Case):
    """QA recorded as skipped (no local path to test) lets a card close as done once an approver said yes to closing it."""
    open, card, DONE = OpenClose.open, CardClose.card, CardClose.DONE
    SKIPPED = '## Pass 1\n\nVerdict: SKIPPED: no local path, the export runs only on the test site\n'
    CLOSE = 'python3 core/scripts/event.py close --session c1 --outcome done --goal-met "the export matches"'

    def setUp(self):
        super().setUp()
        self.card('runbook: none learned', qa=self.SKIPPED)
        self.sid = common.active(self.ws, 'c1')[0]

    def gate(self, *said, cmd=None, who='Robin Vale'):
        import hooks
        data = {'tool_name': 'Bash', 'tool_input': {'command': cmd or self.CLOSE}, 'cwd': self.ws, 'session_id': 'c1',
                'transcript_path': testenv.sitting(Path(self.ws), 'c1', *said)}
        testenv.sh(Path(self.ws), 'git', 'config', 'user.name', who)
        try:
            return hooks.gate_why(data)
        finally:
            testenv.sh(Path(self.ws), 'git', 'config', 'user.name', 'Robin Vale')

    def refused(self, *words):
        with self.assertRaises(SystemExit) as cm:
            self.run_cmd(*self.DONE)
        for w in words:
            self.assertIn(w, str(cm.exception.code))

    def approve(self, by='Robin Vale', key='item-12'):
        common.append(self.ws, self.sid, {'ev': 'approve', 'gate': 'close a card with QA skipped', 'by': by, 'via': 'typed', 'key': key})

    def test_an_approvers_typed_yes_naming_the_card_lets_it_close(self):
        self.assertIsNone(self.gate(('human', 'Yes, close item-12 as done without QA.')))
        self.assertEqual([(e['gate'], e['key'], e['by']) for e in common.session_events(self.ws, self.sid) if e.get('ev') == 'approve'],
                         [('close a card with QA skipped', 'item-12', 'Robin Vale')])
        self.assertIn('closed', self.run_cmd(*self.DONE))

    def test_with_no_yes_the_gate_asks_and_the_close_names_both_ways_out(self):
        self.assertIn('needs a yes', self.gate(('human', 'how is item-12 going?')) or 'opened')
        self.refused('SKIPPED', 'Verdict: PASS', 'approver')

    def test_a_yes_typed_by_someone_who_is_not_an_approver_does_not_count(self):
        self.assertIn('needs a yes', self.gate(('human', 'Yes, close item-12 as done without QA.'), who='Tin Agent') or 'opened')
        self.approve(by='Tin Agent')
        self.refused('approver')

    def test_a_yes_for_another_card_does_not_count(self):
        self.approve(key='item-13')
        self.refused('approver')

    def test_fail_and_cannot_verify_are_not_closed_by_a_yes(self):
        self.approve()
        for verdict in ('FAIL', 'CANNOT-VERIFY'):
            (Path(self.ws) / 'sessions/item-12/qa-report.md').write_text(self.SKIPPED + f'\n## Pass 2\n\nVerdict: {verdict}\n')
            self.assertIsNone(self.gate(('human', 'Yes, close item-12 as done without QA.')), verdict)
            self.refused(verdict)

    def test_a_skip_with_no_reason_is_not_a_skip(self):
        (Path(self.ws) / 'sessions/item-12/qa-report.md').write_text('Verdict: SKIPPED\n')
        self.approve()
        self.refused('is not one of')

    def test_a_park_is_not_gated(self):
        self.assertIsNone(self.gate(cmd='python3 core/scripts/event.py close --session c1 --park --cause approval-gate --note waits'))

    def test_confirm_in_a_run_reads_the_same_rule(self):
        self.assertIn('approver', event.qa_problem(self.ws, 'item-12') or 'nothing')
        self.approve()
        self.assertIsNone(event.qa_problem(self.ws, 'item-12'))


class CardModeLessons(unittest.TestCase):
    """A scope correction counts and keeps its lesson; what the session settled alone is written down as assumed."""
    CARD = Path(__file__).resolve().parent.parent.parent / 'modules/mode-card'

    def text(self, rel):
        return ' '.join((self.CARD / rel).read_text().split())

    def test_a_person_changing_the_scope_is_a_counted_interaction_and_a_product_decision_is_no_reason(self):
        mode = self.text('seeds/modes/card.md')
        self.assertIn('narrowing, widening or correcting the card\'s scope or direction is a counted interaction', mode)
        self.assertIn('"a product decision" is not by itself a reason for `no durable lesson`', mode)
        self.assertIn('keep a card to what was asked and offer extras as separate cards', mode)
        self.assertIn('"a product decision" is not by itself a reason', self.text('templates/session.md'))

    def test_a_question_the_session_settled_alone_is_written_as_assumed_not_asked(self):
        mode = self.text('seeds/modes/card.md')
        self.assertIn('`assumed, not asked` in the By column', mode)
        for how in ('from a README', 'by inference from another answer', 'by choosing a design'):
            self.assertIn(how, mode)
        self.assertIn('`assumed, not asked`', self.text('templates/session.md'))


class Report(Case):
    def test_touches_are_counted_per_session_and_a_tagged_one_replaces_an_untagged_one(self):
        for sid, n in (('a', 3), ('b', 1)):
            self.emit('--ev', 'start', sid=sid, kind='card')
            for _ in range(n):
                common.append(self.ws, sid, {'kind': 'card', 'ev': 'touch', 'cause': 'untagged'})
        self.emit('--ev', 'touch', '--cause', 'verification', sid='a', kind='card')
        self.emit('--ev', 'end', '--outcome', 'done', '--goal-met', 'checked', sid='a', kind='card')
        out = self.run_cmd('report')
        self.assertIn('card: sessions 2, touches/session mean 2.00 median 2', out)
        self.assertIn('untagged 3, verification 1', out)
        self.assertIn('outcomes: done 1', out)

    def test_a_failure_class_seen_in_two_sessions_is_named_as_a_repeat(self):
        for sid in ('a', 'b', 'c'):
            self.emit('--ev', 'start', sid=sid, kind='triage')
        self.emit('--ev', 'touch', '--cause', 'verification', '--fp', 'exports:wrong-total', sid='a', kind='triage')
        self.emit('--ev', 'block', '--cause', 'tooling', '--fp', 'exports:wrong-total', sid='b', kind='triage')
        self.emit('--ev', 'touch', '--cause', 'other', '--fp', 'mail:bounce', sid='c', kind='triage')
        out = self.run_cmd('report')
        self.assertIn('exports:wrong-total: 2 sessions (a, b)', out)
        self.assertNotIn('mail:bounce', out)

    def test_two_incidents_named_for_the_same_failure_are_a_repeat_with_no_class_typed(self):
        self.emit('--ev', 'start', '--subject', '2027-05-06-double-charge-deposit', sid='a', kind='triage')
        self.emit('--ev', 'start', '--subject', '2027-05-14-double-charge-deposit', sid='b', kind='triage')
        self.emit('--ev', 'start', '--subject', '2027-05-14-slow-login', sid='c', kind='triage')
        self.emit('--ev', 'start', '--subject', 'double-charge-deposit', sid='d', kind='card')
        out = self.run_cmd('report')
        self.assertIn('double-charge-deposit: 2 sessions (a, b)', out)
        self.assertNotIn('slow-login', out)

    def test_one_failure_class_typed_two_ways_is_still_one_class(self):
        for sid in ('a', 'b'):
            self.emit('--ev', 'start', sid=sid, kind='triage')
        self.emit('--ev', 'touch', '--cause', 'verification', '--fp', 'Exports:Wrong_Total', sid='a', kind='triage')
        self.emit('--ev', 'block', '--cause', 'tooling', '--fp', 'exports:wrong-total', sid='b', kind='triage')
        self.assertIn('exports:wrong-total: 2 sessions (a, b)', self.run_cmd('report'))

    def test_open_blocks_wait_until_cleared(self):
        self.emit('--ev', 'start', '--subject', 'refund-letter')
        self.emit('--ev', 'block', '--cause', 'approval-gate', '--note', 'the letter waits for an approver')
        self.assertEqual([w['subject'] for w in event.waiting(self.ws)], ['refund-letter'])
        self.emit('--ev', 'clear')
        self.assertEqual(event.waiting(self.ws), [])


class Stats(Case):
    def played(self):
        for sid, outcome in (('a', 'done'), ('b', 'abandoned'), ('c', None)):
            self.emit('--ev', 'start', '--subject', f'job-{sid}', sid=sid, kind='card')
            self.emit('--ev', 'block', '--cause', 'approval-gate', sid=sid, kind='card') if sid != 'b' else None
            if outcome:
                met = ('--goal-met', 'the export ran and its row count matched') if outcome == 'done' else ()
                self.emit('--ev', 'end', '--outcome', outcome, *met, sid=sid, kind='card')

    def test_the_totals_line_counts_each_session_once_ended_stopped_or_still_open(self):
        self.played()
        line = self.run_cmd('stats').splitlines()[0]
        self.assertRegex(line, r'^stats all dates, as of \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z: 2 sessions ended '
                               r'\(abandoned 1, done 1\), 1 of 2 stopped at least once, 1 still open, by 1 named people, '
                               r'counted by session$')

    def test_the_line_names_its_own_window_so_a_later_count_gives_the_same_line(self):
        self.played()
        line = self.run_cmd('stats', '--since', '2020-01-01').splitlines()[0]
        self.assertIn('stats since 2020-01-01, as of ', line)
        time.sleep(1.1)
        self.emit('--ev', 'start', '--subject', 'later', sid='d', kind='adhoc')
        self.emit('--ev', 'end', '--outcome', 'no-action', sid='d', kind='adhoc')
        asof = line.split('as of ')[1].split(':')[0:3]
        again = event.stats_lines(common.load_events(self.ws)[0], '2020-01-01', ':'.join(asof))[0]
        self.assertEqual(again, line)


class Journal(Case):
    storage = 'files'

    def journal(self, *args):
        with mock.patch.dict(os.environ, {'TRAMPO_USER': 'Sam Okoro'}):
            return self.run_cmd('journal', '--sid', 's1', *args)

    def write(self, rel, text):
        src = Path(self.tmp.name) / 'draft.md'
        src.write_text(text)
        self.journal('--path', rel, '--from', str(src))

    def test_a_write_lands_on_disk_and_in_the_ledger_with_its_whole_text(self):
        self.write('memory/shared/tools.md', 'one\n')
        self.write('memory/shared/tools.md', 'two\n')
        self.assertEqual((Path(self.ws) / 'memory/shared/tools.md').read_text(), 'two\n')
        a, b = self.events()
        self.assertEqual((a['ev'], a['text'], a['prev_sha'], b['prev_sha']), ('write', 'one\n', '', event.sha('one\n')))
        self.assertEqual(event.replay(self.events())[0], {'memory/shared/tools.md': 'two\n'})

    def test_a_path_outside_the_workspace_or_a_wrong_version_is_refused(self):
        with self.assertRaises(SystemExit):
            self.write('../elsewhere.md', 'x')
        (Path(self.ws) / 'workspace.yaml').write_text('storage: files\ncore_version: 0.0.1\n')
        with self.assertRaises(SystemExit) as cm:
            self.write('memory/shared/tools.md', 'x')
        self.assertIn('core_version', str(cm.exception.code))

    def test_a_hand_edit_is_shown_then_adopted_or_restored(self):
        self.write('memory/shared/tools.md', 'one\n')
        (Path(self.ws) / 'memory/shared/tools.md').write_text('one\nby hand\n')
        self.assertIn('+by hand', self.journal('--path', 'memory/shared/tools.md', '--diff'))
        with self.assertRaises(SystemExit):
            self.journal('--path', 'memory/shared/tools.md', '--adopt')
        self.journal('--path', 'memory/shared/tools.md', '--adopt', '--accepted-by', 'Sam Okoro')
        self.assertEqual(self.events()[-1]['accepted_by'], 'Sam Okoro')
        (Path(self.ws) / 'memory/shared/tools.md').write_text('lost\n')
        self.journal('--path', 'memory/shared/tools.md', '--restore')
        self.assertEqual((Path(self.ws) / 'memory/shared/tools.md').read_text(), 'one\nby hand\n')

    def test_on_git_there_is_no_journal(self):
        ws = str(testenv.workspace(Path(self.tmp.name) / 'g', 'git'))
        with self.assertRaises(SystemExit) as cm:
            event.main(['journal', '--ws', ws, '--sid', 's1', '--path', 'memory/a.md', '--remove'])
        self.assertIn('storage: files', str(cm.exception.code))


if __name__ == '__main__':
    unittest.main()
