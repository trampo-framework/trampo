#!/usr/bin/env python3
"""The one reader of shell command text: what it sees as running, as a write onto a guarded file, and as a push
that skips git's hooks. The cases under Ceilings pass on purpose: they are what a text reader cannot see."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import testenv  # noqa: E402,F401
import shellread as sr  # noqa: E402

NAMES = ['approvals.jsonl']


class Live(unittest.TestCase):
    def test_segments_split_outside_quotes_only(self):
        self.assertEqual(sr.segments('a "b; c" && d | e'), ['a "b; c" ', '', ' d ', ' e'])

    def test_text_that_cannot_run_is_not_a_run(self):
        self.assertNotIn('deliver.sh', sr.live("grep -n 'deliver.sh --to client' notes.md"))
        self.assertNotIn('deliver.sh', sr.live("cat > plan.md <<'EOF'\nrun deliver.sh --to client\nEOF"))
        self.assertNotIn('deliver.sh', sr.live('git log --grep "deliver.sh"'))

    def test_text_that_can_still_reach_a_shell_stays(self):
        self.assertIn('deliver.sh', sr.live('grep -l x * | xargs ./deliver.sh'))
        self.assertIn('deliver.sh', sr.live('cat <<EOF | sh\n./deliver.sh\nEOF'))
        self.assertIn('deliver.sh', sr.live("cat > x <<'EOF'\n$(./deliver.sh)\nEOF"))
        self.assertIn('deliver.sh', sr.live('rg --pre ./deliver.sh x'))
        self.assertIn('deliver.sh', sr.live('echo ok; ./deliver.sh'))


class Writes(unittest.TestCase):
    def w(self, cmd):
        return sr.shell_write(cmd, NAMES)

    def test_the_write_forms_an_assistant_reaches_for_are_seen(self):
        for cmd in ('echo x >> state/approvals.jsonl', 'echo x | tee -a state/approvals.jsonl', "sed -i '' s/no/yes/ state/approvals.jsonl",
                    'cp /tmp/a state/approvals.jsonl', 'mv /tmp/a "state/approvals.jsonl"', 'truncate -s 0 state/approvals.jsonl',
                    'F=state/approvals.jsonl; echo x > $F', "python3 -c \"open('state/approvals.jsonl','a').write('x')\"",
                    'dd if=/tmp/a of=state/approvals.jsonl'):
            self.assertTrue(self.w(cmd), cmd)

    def test_reads_pass(self):
        for cmd in ('cat state/approvals.jsonl', 'grep answer state/approvals.jsonl > /tmp/out', 'cp state/approvals.jsonl /tmp/copy',
                    'tail -3 state/approvals.jsonl | python3 -m json.tool', 'echo x > other.jsonl'):
            self.assertFalse(self.w(cmd), cmd)


class Push(unittest.TestCase):
    def test_a_push_that_names_a_hook_skipping_word_is_seen(self):
        for cmd in ('git push --no-verify origin main', 'git -c core.hooksPath=/dev/null push', 'GIT_CONFIG_GLOBAL=/dev/null git push',
                    'git -c alias.p=push p', "git pu''sh --no-verify", 'git commit -m x && git push --no-verify'):
            self.assertTrue(sr.push_bypass(cmd), cmd)

    def test_a_plain_push_and_words_that_only_name_it_pass(self):
        for cmd in ('git push origin HEAD:main', 'git commit -m "never push with --no-verify"', 'echo "git push --no-verify"',
                    "grep -rn 'push --no-verify' docs/", 'git commit --no-verify -m wip'):
            self.assertFalse(sr.push_bypass(cmd), cmd)

    def test_words_that_only_name_it_are_read_whole_once_the_line_could_run_them(self):
        self.assertTrue(sr.push_bypass('echo "git push --no-verify" | sh'))
        self.assertTrue(sr.push_bypass('echo "git push --no-verify" > run.sh'))
        self.assertTrue(sr.push_bypass('x=$(echo push); git $x --no-verify'))


class Ceilings(unittest.TestCase):
    """Ways around a reader of typed text. Each is listed in docs/decisions.md; none is closed here."""

    def test_a_script_file_hides_the_command(self):
        self.assertNotIn('deliver.sh', sr.live('sh ./wrapper.sh'))

    def test_a_name_built_at_run_time_hides_the_file(self):
        self.assertFalse(sr.shell_write('d=state; n=approvals; echo x > $d/$n.jsonl', NAMES))

    def test_a_directory_change_hides_the_ledger_and_the_control_folders(self):
        self.assertFalse(sr.shell_write('cd telemetry/events && echo x >> s1.jsonl', [r'telemetry/events/[^\s;&|<>"\']*\.jsonl'], raw=True))
        self.assertFalse(sr.shell_write('cd slots && echo x > tracker.md', [r'(?<![\w.-])slots/[^\s;&|<>"\']*'], raw=True))

    def test_a_git_name_set_by_a_file_or_an_environment_variable_is_not_seen(self):
        self.assertFalse(sr.sets_git_name('printf "[user]\\nname = X\\n" | git config --file /tmp/c --add user.email x'))
        self.assertFalse(sr.sets_git_name('GIT_AUTHOR_NAME=X git commit -m y'))

    def test_a_comment_is_not_an_argument_but_a_quoted_hash_is(self):
        self.assertEqual(sr.words('run a # b'), [['run', 'a']])
        self.assertEqual(sr.words('run "a # b"'), [['run', 'a # b']])

    def test_another_language_hides_the_push(self):
        self.assertFalse(sr.push_bypass("python3 -c \"import subprocess as s; s.run(['git','pu'+'sh','--no-'+'verify'])\""))


if __name__ == '__main__':
    unittest.main()
