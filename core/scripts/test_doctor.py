#!/usr/bin/env python3
"""The health check: what fails, what only warns, and what it can rebuild from the journal."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import testenv  # noqa: E402
import doctor  # noqa: E402
import event  # noqa: E402

ENTRY = '## Exports run at night (2026-01-05, billing-export)\n\nThe export job starts at 02:00.\n**How to apply:** look after 03:00.\n'


class Case(unittest.TestCase):
    storage = 'git'
    extra = ''

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = testenv.workspace(Path(self.tmp.name) / 'ws', self.storage, extra=self.extra)
        self.put('memory.md', '# Memory\n\n## Categories\n\n| File | Subject | Read trigger |\n|---|---|---|\n'
                 '| `memory/shared/shared.md` | Shared facts | Before any work |\n')
        self.put('memory/shared/shared.md', '| `memory/shared/tools.md` | Tools | Before using a tool |\n')
        self.put('memory/shared/tools.md', ENTRY)

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, rel, text):
        f = self.ws / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)

    def check(self, **kw):
        return doctor.check(self.ws, **kw)

    def assertIn_any(self, needle, lines):
        self.assertTrue(any(needle in l for l in lines), f'{needle!r} not in {lines}')


class Basics(Case):
    def test_a_seeded_workspace_is_clean(self):
        self.assertEqual(self.check(), ([], []))

    def test_the_version_pin_and_the_storage_kind_are_failures(self):
        self.put('workspace.yaml', 'storage: tape\ncore_version: 0.0.1\n')
        fails, _ = self.check()
        self.assertIn_any('storage must be files or git', fails)
        self.assertIn_any('core version mismatch', fails)

    def test_a_gated_command_with_no_approver_is_a_failure(self):
        self.put('workspace.yaml', f'storage: git\ncore_version: {testenv.VERSION}\ngated_commands:\n  send: deliver\\.sh\n')
        self.assertIn_any('nobody can approve', self.check()[0])

    def test_a_symbolic_link_is_never_followed(self):
        (self.ws / 'memory' / 'link.md').symlink_to(self.ws / 'memory.md')
        self.assertIn_any('symbolic link', self.check()[0])

    def test_size_and_routing_only_warn(self):
        self.put('workspace.yaml', f'storage: git\ncore_version: {testenv.VERSION}\ncaps:\n  file_words: 5\n  index_words: 5\n')
        self.put('memory/shared/unlisted.md', ENTRY)
        fails, warns = self.check()
        self.assertEqual(fails, [])
        self.assertIn_any('memory/shared/tools.md has', warns)
        self.assertIn_any('memory.md has', warns)
        self.assertIn_any('memory/shared/unlisted.md is in no index', warns)

    def test_a_claim_about_live_state_needs_its_stamp(self):
        self.put('memory/shared/tools.md', '## The night export is disabled (2026-01-05, billing-export)\n\nOff.\n**How to apply:** ask.\n')
        self.assertIn_any('claims live state', self.check()[0])
        self.put('memory/shared/tools.md', '## The night export is disabled (2026-01-05, billing-export)\n\nOff.\n'
                 'As of 2026-01-05 (billing-export); re-check: crontab -l\n**How to apply:** ask.\n')
        self.assertEqual(self.check()[0], [])

    def test_text_that_looks_personal_warns_and_a_secret_warns_on_git(self):
        self.put('sessions/a/session.md', 'Call 555-010-1234 or write to sam@example.org\npassword = hunter2hunter2\n')
        fails, warns = self.check()
        self.assertEqual(fails, [])
        self.assertIn_any('an email address', warns)
        self.assertIn_any('a password assignment', warns)


class Files(Case):
    storage = 'files'

    def journal(self, rel, text):
        src = Path(self.tmp.name) / 'draft'
        src.write_text(text)
        with mock.patch.dict(os.environ, {'TRAMPO_USER': 'Sam Okoro'}), mock.patch('builtins.print'):
            event.main(['journal', '--ws', str(self.ws), '--sid', 's1', '--path', rel, '--from', str(src)])

    def test_a_hand_edit_fails_until_a_person_decides(self):
        self.journal('memory/shared/tools.md', ENTRY)
        self.assertEqual(self.check()[0], [])
        self.put('memory/shared/tools.md', ENTRY + 'by hand\n')
        self.assertIn_any('differs from its journal', self.check()[0])

    def test_rebuild_puts_back_only_what_is_missing(self):
        self.journal('memory/shared/tools.md', ENTRY)
        (self.ws / 'memory/shared/tools.md').unlink()
        self.assertIn_any('differs from its journal', self.check()[0])
        self.assertEqual(self.check(rebuild=True)[0], [])
        self.assertEqual((self.ws / 'memory/shared/tools.md').read_text(), ENTRY)

    def test_a_secret_in_a_shared_folder_is_a_failure(self):
        self.put('sessions/a/session.md', 'password = hunter2hunter2\n')
        self.assertIn_any('Nothing sensitive', self.check()[0])

    def test_an_unreadable_ledger_line_is_a_failure(self):
        self.put('telemetry/events/s9.jsonl', 'not json\n')
        self.assertIn_any('unreadable ledger line', self.check()[0])


class Reviews(Case):
    BODY = '## Repeated causes\n\nNone found, 1 session compared.\n\n## Standing warnings\n\nThe health check printed none.\n'

    def setUp(self):
        super().setUp()
        event.main(['emit', '--ws', str(self.ws), '--sid', 's1', '--kind', 'card', '--ev', 'start', '--subject', 'billing-export'])
        event.main(['emit', '--ws', str(self.ws), '--sid', 's1', '--kind', 'card', '--ev', 'end', '--outcome', 'done',
                    '--goal-met', 'the export ran and its row count matched'])
        self.line = event.stats_lines(doctor.load_events(self.ws)[0])[0]

    def test_a_review_that_quotes_the_totals_line_passes_and_a_fresh_copy_recounts_it(self):
        self.put('retros/2026-01-12.md', f'# Review\n\n`{self.line}`\n\n{self.BODY}')
        self.assertEqual(self.check()[0], [])
        copy = Path(self.tmp.name) / 'clone'
        testenv.sh(self.tmp.name, 'cp', '-R', str(self.ws), str(copy))
        self.assertEqual(doctor.check(copy)[0], [])

    def test_a_review_with_no_totals_line_or_one_the_ledger_does_not_give_fails(self):
        self.put('retros/2026-01-12.md', f'# Review\n\n{self.BODY}')
        self.assertIn_any('quotes no totals line', self.check()[0])
        self.put('retros/2026-01-12.md', f"# Review\n\n`{self.line.replace('1 sessions ended', '4 sessions ended')}`\n\n{self.BODY}")
        self.assertIn_any('does not match the ledger', self.check()[0])

    def test_only_the_newest_review_is_recounted_and_each_needs_its_two_sections(self):
        self.put('retros/2026-01-05.md', f'# Review\n\nwritten before the totals line\n\n{self.BODY}')
        self.put('retros/2026-01-12.md', f'# Review\n\n`{self.line}`\n\n## Repeated causes\n\nNone found.\n')
        fails = self.check()[0]
        self.assertIn_any('retros/2026-01-12.md has no "Standing warnings" section', fails)
        self.assertFalse(any('2026-01-05' in f for f in fails), fails)


if __name__ == '__main__':
    unittest.main()
