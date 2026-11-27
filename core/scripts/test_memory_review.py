#!/usr/bin/env python3
"""One flagged and one clean case per memory-review check."""
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import testenv  # noqa: E402,F401
import memory_review  # noqa: E402

FILLER = ' '.join(['The export job reads the nightly snapshot and writes one file per region.'] * 8)


class Review(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name)
        (self.ws / 'memory' / 'archive').mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def checks(self, **files):
        for name, text in files.items():
            (self.ws / 'memory' / f'{name}.md').write_text(text)
        return [(f['check'], f['file'], f['heading']) for f in memory_review.review(self.ws)]

    def test_stale_correction_across_files(self):
        got = self.checks(
            a='# A\n\n## The export job cannot run twice on one nightly snapshot\n2026-01-05 (task/x). Seen once.\nHow to apply: wait a day.\n',
            b='# B\n\n## The export job reruns safely with the force flag\n2026-02-01 (task/y; corrects earlier claim that the export job cannot run twice on one nightly snapshot). Ran it twice.\nHow to apply: pass the flag.\n')
        self.assertEqual(got, [('stale-correction', 'memory/a.md', 'The export job cannot run twice on one nightly snapshot')])

    def test_corrected_entry_is_clean(self):
        got = self.checks(
            a='# A\n\n## Until 2026-02-01 the export job was believed single-run\n2026-01-05 (task/x).\nHow to apply: see b.\n',
            b='# B\n\n## The export job reruns safely with the force flag\n2026-02-01 (task/y; corrects earlier claim that the export job cannot run twice on one nightly snapshot).\nHow to apply: pass the flag.\n')
        self.assertEqual(got, [])

    def test_conflicting_count(self):
        got = self.checks(
            a='# A\n\n## Most regions export cleanly\n2026-01-05 (task/x). 3 of 9 regions failed.\nHow to apply: retry.\n\n## Region failures cluster at night\n2026-01-09 (task/z). 4 of 12 regions failed.\nHow to apply: retry.\n')
        self.assertEqual(got, [('conflicting-count', 'memory/a.md', 'Region failures cluster at night')])

    def test_scope_undone(self):
        got = self.checks(
            a='# A\n\n## Every export needs the region flag\n2026-01-05 (task/x).\nHow to apply: pass it, except for the global export.\n',
            b='# B\n\n## Every export except the global one needs the region flag\n2026-01-05 (task/x).\nHow to apply: pass it, except for the global export.\n')
        self.assertEqual(got, [('scope-undone', 'memory/a.md', 'Every export needs the region flag')])

    def test_buried_do_not(self):
        long = f'2026-01-05 (task/x). {FILLER}\nHow to apply: rerun it. Never delete the snapshot first.\n'
        got = self.checks(
            a='# A\n\n## The export job reads the nightly snapshot\n' + long,
            b='# B\n\n## Never delete the snapshot before the export job has run\n' + long,
            c='# C\n\n## Short entries hide nothing\n2026-01-05 (task/x).\nHow to apply: never skip the check.\n')
        self.assertEqual(got, [('buried-do-not', 'memory/a.md', 'The export job reads the nightly snapshot')])

    def test_archive_and_indexes_are_skipped(self):
        bad = '# A\n\n## Every export needs the region flag\nHow to apply: except the global one.\n'
        (self.ws / 'memory' / 'archive' / 'old.md').write_text(bad)
        (self.ws / 'memory' / 'task').mkdir()
        (self.ws / 'memory' / 'task' / 'index.md').write_text(bad)
        self.assertEqual(memory_review.review(self.ws), [])


if __name__ == '__main__':
    unittest.main()
