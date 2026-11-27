"""The publishing scan finds the shapes no public file needs, on every system it runs on."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCAN = Path(__file__).resolve().parent.parent.parent / 'scripts' / 'deny-scan.sh'
# built here so this file does not hold the shapes it tests for
KEY, ACCOUNT = 'TKT' + '-' + '1234', '4' * 12


class DenyScan(unittest.TestCase):
    def scan(self, files, terms=''):
        with tempfile.TemporaryDirectory() as tmp:
            env = {'PATH': os.environ['PATH'], 'HOME': tmp, 'GIT_CONFIG_GLOBAL': str(Path(tmp) / 'gitconfig'),
                   'GIT_CONFIG_NOSYSTEM': '1', 'DENY_TERMS': terms}
            repo = Path(tmp) / 'repo'
            repo.mkdir()
            subprocess.run(['git', 'init', '-q'], cwd=repo, env=env, check=True)
            for name, text in files.items():
                (repo / name).write_text(text)
            subprocess.run(['git', 'add', '.'], cwd=repo, env=env, check=True)
            r = subprocess.run(['bash', str(SCAN)], cwd=repo, env=env, capture_output=True, text=True)
            return r.returncode, r.stdout + r.stderr

    def test_a_ticket_key_and_a_twelve_digit_number_are_each_found(self):
        for text in (f'see {KEY} for the story\n', f'{KEY}\n', f'({KEY})\n', f'account {ACCOUNT}.\n', f'{ACCOUNT}\n'):
            code, out = self.scan({'notes.md': text})
            self.assertEqual(code, 1, text)
            self.assertIn('notes.md:1', out)

    def test_a_clean_tree_and_look_alikes_pass(self):
        code, out = self.scan({'notes.md': f'utf-8 and x{KEY}9 and {ACCOUNT}7 and sha-256 and item-12\n'})
        self.assertEqual((code, out.strip()), (0, 'deny-scan: clean'))

    def test_a_listed_term_is_still_found(self):
        self.assertEqual(self.scan({'notes.md': 'the Harbour team\n'}, terms='harbour')[0], 1)


if __name__ == '__main__':
    unittest.main()
