#!/usr/bin/env python3
"""hooks.json is what makes a rule more than prose. Each test here runs the command the plugin registers, found by
the event and the tool name the way the host finds it, so a rule whose hook is not registered fails its test."""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import testenv  # noqa: E402
import common  # noqa: E402

ROOT = HERE.parent
WIRING = json.loads((ROOT / 'hooks' / 'hooks.json').read_text())['hooks']
SHELL_TOOLS = ('Bash', 'mcp__plugin_context-mode_context-mode__ctx_execute', 'mcp__plugin_context-mode_context-mode__ctx_batch_execute',
               'mcp__plugin_context-mode_context-mode__ctx_execute_file')
FILE_TOOLS = ('Write', 'Edit', 'MultiEdit', 'NotebookEdit')
GATES = 'gated_commands:\n  send to client: deliver\\.sh\n'


def registered(event, tool=None):
    """The commands registered for this event, and this tool where the event has a matcher."""
    return [h['command'] for entry in WIRING.get(event, []) for h in entry['hooks']
            if tool is None or re.fullmatch(entry.get('matcher') or '.*', tool)]


def fire(event, data, tool=None):
    """Run every registered command as the host would: [(exit status, stdout, stderr)]."""
    out = []
    for command in registered(event, tool):
        r = subprocess.run(command.replace('${CLAUDE_PLUGIN_ROOT}', str(ROOT)), shell=True, input=json.dumps(data),
                           capture_output=True, text=True, env={**os.environ, 'CLAUDE_PLUGIN_ROOT': str(ROOT)})
        out.append((r.returncode, r.stdout, r.stderr))
    return out


def shell_input(tool, cmd):
    if tool.endswith('ctx_batch_execute'):
        return {'commands': [{'label': 'x', 'command': cmd}]}
    return {'command': cmd} if tool == 'Bash' else {'language': 'shell', 'code': cmd}


class Case(unittest.TestCase):
    extra = GATES

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = testenv.workspace(Path(self.tmp.name) / 'ws', extra=self.extra)
        self.transcript = testenv.transcript(Path(self.tmp.name) / 't.jsonl', ('human', 'carry on'))

    def tearDown(self):
        self.tmp.cleanup()

    def refused(self, tool, given):
        data = {'hook_event_name': 'PreToolUse', 'tool_name': tool, 'tool_input': given, 'cwd': str(self.ws), 'session_id': 'c1',
                'transcript_path': self.transcript}
        return [err for status, _, err in fire('PreToolUse', data, tool) if status == 2]

    def file_input(self, tool, path):
        return {'notebook_path' if tool == 'NotebookEdit' else 'file_path': str(path), 'content': 'x'}


class Registered(unittest.TestCase):
    def test_the_plugin_registers_hooks_at_all(self):
        self.assertTrue(WIRING, 'hooks.json registers nothing: every gate would be prose')
        self.assertTrue(all(h.get('command') for entries in WIRING.values() for e in entries for h in e['hooks']))

    def test_every_registered_command_names_a_script_that_exists(self):
        for commands in map(registered, WIRING):
            for command in commands:
                script = re.search(r'scripts/([\w.]+\.py)', command)
                self.assertTrue(script and (HERE / script.group(1)).is_file(), command)


class Sync(unittest.TestCase):
    def test_the_stop_gate_and_the_session_start_step_are_registered(self):
        self.assertTrue(any('hooks.py sync-gate' in c for c in registered('Stop')), 'no stop gate: a session could end with its work unsaved')
        self.assertTrue(any('hooks.py start' in c for c in registered('SessionStart')), 'no start step: git hooks and the sync never run')


class Habits(Case):
    def test_every_prompt_is_counted_and_the_hook_adds_nothing_to_the_prompt(self):
        subprocess.run([sys.executable, '-B', str(HERE / 'event.py'), 'open', '--ws', str(self.ws), '--kind', 'card', '--subject',
                        'refund-letter', '--session', 'c1'], capture_output=True, check=True)
        ran = fire('UserPromptSubmit', {'cwd': str(self.ws), 'session_id': 'c1', 'prompt': 'carry on'})
        self.assertEqual([(status, out) for status, out, _ in ran], [(0, '')], 'no prompt hook: touches would be counted by hand')
        touches = [e for e in common.load_events(self.ws)[0] if e.get('ev') == 'touch']
        self.assertEqual([t['cause'] for t in touches], ['untagged'])

    def test_a_bare_question_in_needs_you_blocks_the_stop(self):
        reply = '**Drafted the letter.**\n\n**Needs you:**\n1. Should I send it?\n'
        ran = fire('Stop', {'cwd': str(self.ws), 'session_id': 'c1', 'last_assistant_message': reply})
        self.assertTrue(any('"block"' in out and 'Should I send it?' in out for _, out, _ in ran), 'no answer-shape check on Stop')

    def test_the_memory_routes_and_gate_rules_are_said_at_start_after_a_clear_and_after_a_compaction(self):
        (self.ws / 'memory.md').write_text('## Categories\n\nshared: memory/shared/shared.md\n')
        for source in ('startup', 'clear', 'compact'):
            ran = fire('SessionStart', {'cwd': str(self.ws), 'session_id': 'c1', 'source': source}, source)
            self.assertTrue(any('memory/shared/shared.md' in out for _, out, _ in ran), source)


class Gate(Case):
    def test_a_gated_command_is_refused_through_every_shell_capable_tool(self):
        for tool in SHELL_TOOLS:
            self.assertTrue(self.refused(tool, shell_input(tool, './deliver.sh sessions/refund-letter/reply.txt')), tool)

    def test_the_hand_declared_name_is_guarded_on_every_tool_that_can_write(self):
        user = common.config_dir() / 'user'
        for tool in FILE_TOOLS:
            self.assertTrue(self.refused(tool, self.file_input(tool, user)), tool)
        for tool in SHELL_TOOLS:
            self.assertTrue(self.refused(tool, shell_input(tool, f'echo Robin Vale > {user}')), tool)

    def test_the_control_files_and_the_grants_file_are_guarded(self):
        for rel in ('workspace.yaml', 'memory/shared/grants.md', 'constitution.md'):
            for tool in FILE_TOOLS:
                self.assertTrue(self.refused(tool, self.file_input(tool, self.ws / rel)), (tool, rel))
        for tool in SHELL_TOOLS:
            self.assertTrue(self.refused(tool, shell_input(tool, 'echo "  - Sam Okoro" >> workspace.yaml')), tool)

    def test_a_grant_on_the_never_list_opens_nothing(self):
        subprocess.run([sys.executable, '-B', str(HERE / 'event.py'), 'open', '--ws', str(self.ws), '--kind', 'card', '--subject',
                        'refund-letter', '--session', 'c1'], capture_output=True, check=True)
        gates = self.ws / 'workspace.yaml'
        gates.write_text(gates.read_text() + '  change the approvers: approvers\\.sh\n')
        (self.ws / 'memory/shared').mkdir(parents=True)
        (self.ws / 'memory/shared/grants.md').write_text(
            '## Approvers may be changed freely (2026-01-05)\nGate: change the approvers\nScope: sessions\nHolder: card\n'
            'Approved-by: Robin Vale session c1\n')
        self.assertTrue(self.refused('Bash', {'command': './approvers.sh sessions/refund-letter'}))

    def test_the_ledger_and_every_control_directory_are_guarded_on_every_tool(self):
        ledger = self.ws / 'telemetry/events/s1.jsonl'
        for tool in FILE_TOOLS:
            self.assertTrue(self.refused(tool, self.file_input(tool, ledger)), tool)
            self.assertTrue(self.refused(tool, self.file_input(tool, self.ws / 'slots/tracker.md')), tool)
        for tool in SHELL_TOOLS:
            self.assertTrue(self.refused(tool, shell_input(tool, f'echo x >> {ledger}')), tool)
            self.assertTrue(self.refused(tool, shell_input(tool, 'echo x > .claude/hooks/gate.py')), tool)

    def test_a_changed_git_name_is_refused_on_every_shell_capable_tool(self):
        for tool in SHELL_TOOLS:
            self.assertTrue(self.refused(tool, shell_input(tool, 'git config user.name Robin')), tool)

    def test_the_bridge_records_are_guarded(self):
        record = self.ws / '.trampo/state/ask/desk.jsonl'
        self.assertTrue(self.refused('Write', self.file_input('Write', record)))
        self.assertTrue(self.refused('Bash', {'command': f'echo x >> {record}'}))

    def test_a_push_that_skips_the_boundary_is_refused(self):
        self.assertTrue(self.refused('Bash', {'command': 'git push --no-verify origin main'}))

    def test_the_runtimes_transcripts_are_guarded(self):
        mine = testenv.project(self.ws) / 'c1.jsonl'
        self.assertTrue(self.refused('Write', self.file_input('Write', mine)))
        self.assertTrue(self.refused('Bash', {'command': f'echo x >> {mine}'}))


class OutsideOn(Case):
    extra = GATES + 'outside: ask-first\n'

    def test_ask_first_outside_the_workspace_is_enforced_when_the_workspace_turns_it_on(self):
        target = Path.home() / 'elsewhere' / 'table.csv'
        for tool in FILE_TOOLS:
            self.assertTrue(self.refused(tool, self.file_input(tool, target)), tool)


if __name__ == '__main__':
    unittest.main()
