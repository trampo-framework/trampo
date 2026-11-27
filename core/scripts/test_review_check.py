#!/usr/bin/env python3
"""The evidence rules of a review: a finding that breaks one is dropped in code, so a wrong one never reaches a person."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import review_check  # noqa: E402

CODE = '\n'.join(f'line {n}' for n in range(1, 61)) + '\n'
DIFF = '--- a/app.py\n+++ b/app.py\n@@ -10,2 +10,3 @@\n context\n+added\n context\n'


def finding(**kw):
    base = {'path': 'app.py', 'line': 11, 'severity': 'MAJOR', 'category': 'correctness', 'title': 'Wrong total',
            'body': 'The total is doubled for a refund.', 'evidence_quote': 'line 11'}
    return {**base, **kw}


class Rules(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tree = Path(self.tmp.name)
        (self.tree / 'app.py').write_text(CODE)
        (self.tree / 'other.py').write_text(CODE)

    def tearDown(self):
        self.tmp.cleanup()

    def verdict(self, *found, comments=(), cap=12):
        rows, _ = review_check.check({'findings': list(found)}, self.tree, DIFF, comments, cap)
        return [why for _, _, why in rows]

    def test_a_finding_that_meets_every_rule_is_kept(self):
        self.assertEqual(self.verdict(finding()), ['KEEP'])

    def test_the_path_and_the_line_must_exist_at_head(self):
        self.assertIn('path does not exist', self.verdict(finding(path='gone.py'))[0])
        self.assertIn('path does not exist', self.verdict(finding(path='../outside.py'))[0])
        self.assertIn('line is not in the file', self.verdict(finding(line=99, evidence_quote='x'))[0])

    def test_the_quote_must_be_the_text_of_the_cited_line(self):
        self.assertIn('not the text', self.verdict(finding(evidence_quote='line 12'))[0])
        self.assertEqual(self.verdict(finding(evidence_quote='  line   11 '))[0], 'KEEP')

    def test_the_line_must_be_near_a_hunk_unless_it_names_the_other_end(self):
        far = finding(line=50, evidence_quote='line 50')
        self.assertIn('more than 10 lines', self.verdict(far)[0])
        self.assertEqual(self.verdict({**far, 'cross_file': {'path': 'other.py', 'line': 3}})[0], 'KEEP')

    def test_a_claim_of_absence_carries_the_search_that_proved_it(self):
        self.assertIn('grep_evidence', self.verdict(finding(body='The refund path is never called.'))[0])
        self.assertEqual(self.verdict(finding(body='The refund path is never called.', grep_evidence='grep -rn refund . : no match'))[0], 'KEEP')

    def test_a_nit_is_never_posted_and_a_style_class_is_never_a_real_severity(self):
        self.assertIn('nit, not MAJOR', self.verdict(finding(category='naming'))[0])
        self.assertIn('never posted', self.verdict(finding(severity='NIT', category='naming'))[0])

    def test_a_finding_a_reply_refuted_is_not_raised_again_while_the_line_is_unchanged(self):
        old = [{'refuted': True, 'path': 'app.py', 'line': 11, 'quote': 'line 11'}]
        self.assertIn('refuted', self.verdict(finding(), comments=old)[0])
        changed = [{'refuted': True, 'path': 'app.py', 'line': 11, 'quote': 'line eleven'}]
        self.assertEqual(self.verdict(finding(), comments=changed)[0], 'KEEP')

    def test_only_the_worst_up_to_the_cap_are_posted(self):
        got = self.verdict(finding(severity='MINOR'), finding(severity='BLOCKER'), finding(severity='MAJOR'), cap=2)
        self.assertEqual(got, ['over the cap', 'KEEP', 'KEEP'])


if __name__ == '__main__':
    unittest.main()
