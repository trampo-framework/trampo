#!/usr/bin/env python3
"""The runbooks part: what ships, that it installs with only the core, what the health check reports, how a flow
becomes verified and stops being so, the first load's script support, and the session summariser's privacy rule."""
import contextlib
import hashlib
import io
import json
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
PART = ROOT / 'modules' / 'runbooks'
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(PART / 'scripts'))
import testenv  # noqa: E402
import doctor  # noqa: E402
import health  # noqa: E402
import runbooks  # noqa: E402
import session_summary  # noqa: E402

STAMP = '_Written 2026-01-05 from code at orders-service@3f2a91c04b7e; not yet replayed._'
SYSTEM = ('---\nbasis: code\nsources: orders-service@3f2a91c04b7e\n---\n\n# Orders service\n\n' + STAMP +
          '\n\n## Local\n\nRuns locally: not known _(verify)_.\n')
RECORD = '# Replay: place an order\n\nFlow: `runbooks/flows/place-order.md`\nVerdict: PASS as written\n'


def flow(status='not-yet-replayed', last='none', label='(traced from code)', stamp=STAMP, expect='The order page opens.', note='A note.'):
    return (f'---\nstatus: {status}\nsystem: runbooks/systems/orders-service.md\nwaits: none\nlast-replay: {last}\n---\n\n'
            f'# Flow: place an order\n\n{note}\n\n## Steps\n\n### 1. Open the order page {label}\n\n- Do: open the order page.\n'
            f'- Expect: {expect}\n\n{stamp}\n\n## Cleanup\n\nNothing is left behind.\n')


def tree_digest(top):
    h = hashlib.sha256()
    for f in sorted(p for p in Path(top).rglob('*') if p.is_file()):
        h.update(f.relative_to(top).as_posix().encode() + b'\0' + f.read_bytes())
    return h.hexdigest()


class Case(unittest.TestCase):
    replay = 'runbooks:\n  replay: on\n  test_environment: the practice copy\n'

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = testenv.workspace(Path(self.tmp.name) / 'ws')
        shutil.copytree(ROOT / 'core/seeds', self.ws, dirs_exist_ok=True)
        shutil.copytree(PART / 'seeds', self.ws, dirs_exist_ok=True)
        settings = self.ws / 'workspace.yaml'
        settings.write_text(settings.read_text().replace('approvers: []', 'approvers:\n  - Robin Vale'))

    def tearDown(self):
        self.tmp.cleanup()

    def put(self, rel, text):
        f = self.ws / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(text)
        return f

    def index(self, *rels):
        f = self.ws / 'runbooks/README.md'
        f.write_text(f.read_text() + ''.join(f'- `{r}`: listed by the test\n' for r in rels))

    def loaded(self, flow_text=None):
        self.put('runbooks/systems/orders-service.md', SYSTEM)
        self.put('runbooks/flows/place-order.md', flow_text or flow())
        self.index('systems/orders-service.md', 'flows/place-order.md')

    def turn_replay_on(self):
        settings = self.ws / 'workspace.yaml'
        settings.write_text(settings.read_text() + self.replay)

    def found(self, needle, kind=0):
        lines = doctor.check(self.ws)[kind]
        return [l for l in lines if needle in l]


class Shipped(unittest.TestCase):
    def test_the_part_is_in_the_marketplace_at_the_core_version_and_depends_on_the_core_alone(self):
        listed = json.loads((ROOT / '.claude-plugin/marketplace.json').read_text())['plugins']
        self.assertIn('./modules/runbooks', [p['source'] for p in listed])
        meta = json.loads((PART / '.claude-plugin/plugin.json').read_text())
        self.assertEqual((meta['name'], meta['version'], meta['dependencies']), ('trampo-runbooks', testenv.VERSION, ['trampo-core']))
        self.assertIn(f'version: {testenv.VERSION}\n', (PART / 'module.md').read_text())

    def test_it_ships_its_skills_seeds_templates_and_scripts(self):
        for rel in ('skills/first-load/SKILL.md', 'skills/replay/SKILL.md', 'seeds/modes/runbooks.md', 'seeds/runbooks/README.md',
                    'templates/system.md', 'templates/flow.md', 'templates/replay-brief.md', 'templates/replay-record.md',
                    'templates/skill-proposal.md', 'templates/first-load/session.md', 'templates/first-load/inventory.md',
                    'templates/first-load/writer-brief.md', 'templates/first-load/questions.md',
                    'templates/first-load/unblock-list.md', 'templates/first-load/skills.md', 'scripts/health.py',
                    'scripts/runbooks.py', 'scripts/session_summary.py', 'README.md'):
            self.assertTrue((PART / rel).is_file(), rel)

    def test_the_templates_keep_their_required_sections(self):
        want = {'system.md': ['basis:', 'sources:', '## What it is', '## Where it runs', '## Access and sign-in', '## Entry points',
                              '## Data it owns', '## What it calls and what calls it', '## Logs and signals', '## Local',
                              '## Gotchas', '_(verify)_', 'not yet replayed._'],
                'flow.md': ['status: not-yet-replayed', 'system:', 'waits:', 'last-replay: none', '## What this proves',
                            '## Source references', '## Inputs and test data', '## Steps', '(traced from code)', '- Do:',
                            '- Expect:', 'not yet replayed._', '## Cleanup', '## Not replayable', '## Gotchas'],
                'replay-brief.md': ['from the flow file', '## Authority', '## Rails', '## Exit', 'PASS, DIFFERS, BLOCKED or NOT RUN',
                                    'Never edit the flow'],
                'replay-record.md': ['Flow:', 'Verdict:', '## Steps', '## Flow edits', '## Findings', '## Not run',
                                     '## Side effects on the test environment'],
                'skill-proposal.md': ['status: proposed', 'approved-by:', '## Why', '## Draft', '## Before it is added'],
                'first-load/session.md': ['## Sources', '## Drafts written', '## Questions for a person', '## Unblock list',
                                          '## Skill suggestions', '## Not run'],
                'first-load/inventory.md': ['Read at:', '| Feature | Entry point | Covered by | Gap', 'Drift:', 'Proposed work:',
                                            'Risks:', '(inferred)'],
                'first-load/writer-brief.md': ['## Read', '## Write', '## Rails', 'not yet replayed._', 'git show',
                                               'nothing is run', 'questions.md', 'unblock-list.md'],
                'first-load/questions.md': ['| Q | System | Question | What was read | What an answer changes | Answer | By |',
                                            'assumed, not asked'],
                'first-load/unblock-list.md': ['| U | Access needed | For which flow or step | Who can give it | Status |'],
                'first-load/skills.md': ['## Covered already', '## Worth a new skill', '## Could not classify']}
        for rel, heads in want.items():
            text = (PART / 'templates' / rel).read_text()
            for head in heads:
                self.assertIn(head, text, f'{rel}: {head}')

    def test_the_templates_pass_the_checks_they_are_written_for(self):
        self.assertEqual(health.file_problems('flows/x.md', (PART / 'templates/flow.md').read_text()), [])
        self.assertEqual(health.file_problems('systems/x.md', (PART / 'templates/system.md').read_text()), [])
        self.assertEqual(runbooks.inventory_problems((PART / 'templates/first-load/inventory.md').read_text()), [])
        self.assertEqual(health.proposal_problems((PART / 'templates/skill-proposal.md').read_text()), [])

    def test_the_product_text_is_neutral_and_carries_the_rules(self):
        every = ''.join(f.read_text() for f in PART.rglob('*') if f.suffix in ('.md', '.py', '.json'))
        self.assertNotIn('\u2014', every)
        rules = (PART / 'seeds/runbooks/README.md').read_text() + (PART / 'seeds/modes/runbooks.md').read_text()
        for phrase in ('describe systems, never a single piece of work', 'in the same session', 'observed', 'traced from code',
                       'machine-local', '## Local', 'a draft', 'Nothing is run against a live system', 'one writer per system',
                       'An edit to a step', 'no session content'):
            self.assertIn(phrase, rules, phrase)
        first = (PART / 'skills/first-load/SKILL.md').read_text() + rules
        for phrase in ('test environment', 'a person approves', 'questions.md', 'unblock-list.md', 'session_summary.py'):
            self.assertIn(phrase, first, phrase)


class StandAlone(Case):
    def test_a_workspace_built_from_the_core_and_this_part_alone_is_healthy(self):
        self.assertEqual(doctor.check(self.ws), ([], []))
        self.assertFalse((self.ws / 'modes/card.md').exists())

    def test_the_part_names_no_other_part_as_required_and_reaches_no_slot(self):
        for f in PART.rglob('*.md'):
            text = f.read_text()
            self.assertNotIn('slot.py', text, f.name)
            if f.name != 'README.md' or f.parent != PART:
                for other in ('modes/card.md', 'modes/triage.md', 'modes/adhoc.md'):
                    self.assertNotIn(other, text, f.name)

    def test_a_loaded_workspace_with_drafts_is_healthy_and_the_drafts_are_not_verified(self):
        self.loaded()
        self.assertEqual(doctor.check(self.ws), ([], []))
        self.assertEqual([r['status'] for r in runbooks.flow_rows(self.ws)], ['not-yet-replayed'])

    def test_the_health_check_says_so_when_the_folder_exists_and_the_part_is_not_installed(self):
        from unittest import mock
        with mock.patch.object(doctor, 'part_checks', return_value=([], [], [])):
            self.assertTrue(any('runbooks/' in w and 'not installed' in w for w in doctor.check(self.ws)[1]))


class HealthCheck(Case):
    def test_a_runbook_not_in_the_index_is_reported(self):
        self.loaded()
        self.put('runbooks/systems/billing.md', SYSTEM)
        self.assertEqual(len(self.found('runbooks/systems/billing.md is not in the index', 1)), 1)

    def test_a_flow_marked_verified_with_no_replay_record_fails(self):
        self.loaded(flow(status='verified'))
        self.assertTrue(self.found('verified with no replay record'))
        self.loaded(flow(status='verified', last='2026-01-07 sessions/replay-place-order/replay.md'))
        self.assertTrue(self.found('verified with no replay record'), 'a record that is not in the workspace is no record')

    def test_a_step_with_no_label_and_a_code_derived_step_with_no_stamp_fail(self):
        self.loaded(flow(label=''))
        self.assertTrue(self.found('not labelled'))
        self.loaded(flow(stamp=''))
        self.assertTrue(self.found('traced from code and carries no stamp'))
        self.loaded(flow(label='(observed)', stamp=''))
        self.assertEqual(doctor.check(self.ws)[0], [])

    def test_a_system_runbook_written_from_code_needs_its_stamp_and_its_local_section(self):
        self.loaded()
        self.put('runbooks/systems/orders-service.md', SYSTEM.replace(STAMP, ''))
        self.assertTrue(self.found('written from code and carries no stamp'))
        self.put('runbooks/systems/orders-service.md', SYSTEM.replace('## Local', '## Elsewhere'))
        self.assertTrue(self.found('no "## Local" section', 1))
        self.put('runbooks/systems/orders-service.md', SYSTEM.replace('basis: code\n', ''))
        self.assertTrue(self.found('does not say whether it was observed'))

    def test_a_machine_local_path_fails(self):
        for path in ('/Users/robin/code/orders', '/home/robin/orders', 'C:\\Users\\robin\\orders', '/var/folders/x1/T/out'):
            self.loaded(flow(note=f'Read the handler at {path}.'))
            self.assertTrue(self.found('machine-local path'), path)
        self.loaded(flow(note='Read `orders-service@3f2a91c04b7e:app/orders.py:14`.'))
        self.assertEqual(doctor.check(self.ws)[0], [])

    def test_an_unknown_status_fails(self):
        self.loaded(flow(status='looks-fine'))
        self.assertTrue(self.found('status must be'))

    def test_a_skill_proposal_that_depends_on_the_workspace_or_was_added_unapproved_fails(self):
        draft = (PART / 'templates/skill-proposal.md').read_text()
        self.put('proposals/skill-read-ledger-export.md', draft)
        self.assertEqual(doctor.check(self.ws)[0], [])
        self.put('proposals/skill-read-ledger-export.md',
                 draft.replace('## Draft', '## Draft\n\nRead `runbooks/systems/orders-service.md` before the first call.', 1))
        self.assertTrue(self.found('depends on the workspace'))
        self.put('proposals/skill-read-ledger-export.md', draft.replace('status: proposed', 'status: added'))
        self.assertTrue(self.found('added with no approver'))


class Replay(Case):
    def record(self, text=RECORD):
        self.put('sessions/replay-place-order/replay.md', text)
        return 'sessions/replay-place-order/replay.md'

    def test_replay_is_off_until_a_person_turns_it_on_and_names_a_test_environment(self):
        self.loaded()
        self.assertEqual(runbooks.replay_setting(self.ws), ('off', ''))
        self.assertIn('replay is off', runbooks.verify(self.ws, 'runbooks/flows/place-order.md', self.record()))
        settings = self.ws / 'workspace.yaml'
        settings.write_text(settings.read_text() + 'runbooks:\n  replay: on\n')
        self.assertIn('names no test environment', runbooks.verify(self.ws, 'runbooks/flows/place-order.md', self.record()))
        self.assertIn('status: not-yet-replayed', (self.ws / 'runbooks/flows/place-order.md').read_text())

    def test_only_a_passing_replay_record_sets_a_flow_to_verified(self):
        self.loaded()
        self.turn_replay_on()
        name = 'runbooks/flows/place-order.md'
        self.assertIn('no replay record', runbooks.verify(self.ws, name, 'sessions/replay-place-order/replay.md'))
        for verdict in ('FAIL at step 1', 'DIFFERS at step 1', 'BLOCKED', 'PASS with step edits'):
            self.assertIn('did not pass as written', runbooks.verify(self.ws, name, self.record(RECORD.replace('PASS as written', verdict))), verdict)
        self.assertIn('does not name', runbooks.verify(self.ws, name, self.record(RECORD.replace('place-order.md', 'refund.md'))))
        self.assertIsNone(runbooks.verify(self.ws, name, self.record(), today='2026-01-07'))
        text = (self.ws / name).read_text()
        self.assertIn('status: verified\n', text)
        self.assertIn('last-replay: 2026-01-07 sessions/replay-place-order/replay.md\n', text)
        self.assertEqual(doctor.check(self.ws)[0], [])

    def test_an_edit_to_a_step_resets_a_verified_flow_and_an_edit_to_prose_does_not(self):
        self.loaded()
        self.turn_replay_on()
        name = 'runbooks/flows/place-order.md'
        self.assertIsNone(runbooks.verify(self.ws, name, self.record(), today='2026-01-07'))
        f = self.ws / name
        f.write_text(f.read_text().replace('A note.', 'A corrected note about why the page exists.') + '\n## Gotchas\n\nThe page is slow.\n')
        self.assertEqual(doctor.check(self.ws)[0], [])
        self.assertEqual(runbooks.flow_rows(self.ws)[0]['stale'], False)
        f.write_text(f.read_text().replace('The order page opens.', 'The order page opens with an empty basket.'))
        self.assertTrue(self.found('a step was edited after its replay'))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(runbooks.main(['flows', str(self.ws), '--reset']), 0)
        self.assertIn('status: not-yet-replayed\n', f.read_text())
        self.assertEqual(doctor.check(self.ws)[0], [])

    def test_a_record_outside_the_workspace_is_refused(self):
        self.loaded()
        self.turn_replay_on()
        (Path(self.tmp.name) / 'replay.md').write_text(RECORD)
        self.assertIn('inside the workspace', runbooks.verify(self.ws, 'runbooks/flows/place-order.md', '../replay.md'))


class FirstLoad(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / 'orders-service'
        (self.repo / 'app').mkdir(parents=True)
        (self.repo / 'app/orders.py').write_text('def place():\n    return 1\n')
        (self.repo / 'README.md').write_text('# Orders\n')
        testenv.sh(self.repo, 'git', 'init', '-q', '-b', 'main')
        testenv.sh(self.repo, 'git', 'config', 'user.name', 'Robin Vale')
        testenv.sh(self.repo, 'git', 'config', 'user.email', 'test@example.invalid')
        testenv.sh(self.repo, 'git', 'add', '.')
        testenv.sh(self.repo, 'git', 'commit', '-q', '-m', 'first')
        self.sha = testenv.sh(self.repo, 'git', 'rev-parse', 'HEAD')

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_repository_is_pinned_to_its_commit_by_name_and_left_untouched(self):
        (self.repo / 'app/orders.py').write_text('def place():\n    return 2\n')
        before = tree_digest(self.repo)
        pin = runbooks.pin(self.repo)
        self.assertEqual(before, tree_digest(self.repo), 'pinning wrote to the repository')
        self.assertEqual((pin['name'], pin['kind'], pin['files'], pin['dirty']), ('orders-service', 'code', 2, 1))
        self.assertTrue(self.sha.startswith(pin['ref']) and len(pin['ref']) >= 7)
        said = runbooks.render_pins([pin])
        self.assertIn(f'orders-service@{pin["ref"]}', said)
        self.assertIn('git show', said)
        self.assertNotIn(str(self.repo.parent), said, 'a machine-local path would be copied into the inventory')

    def test_a_document_folder_is_pinned_to_the_day_it_was_read(self):
        docs = Path(self.tmp.name) / 'handbook'
        docs.mkdir()
        (docs / 'returns.md').write_text('# Returns\n')
        pin = runbooks.pin(docs, today='2026-01-05')
        self.assertEqual((pin['name'], pin['kind'], pin['ref'], pin['files']), ('handbook', 'documents', '2026-01-05', 1))

    def test_an_inventory_row_needs_its_file_and_line_or_says_it_was_inferred(self):
        head = ('# Inventory: orders\n\nRead at: orders-service@3f2a91c04b7e\n\n## Orders service\n\n'
                '| Feature | Entry point | Covered by | Gap: what a runbook needs |\n| --- | --- | --- | --- |\n')
        good = head + '| Place an order | `orders-service:app/orders.py:1` | none | a flow |\n| Refunds | (inferred) | none | a flow |\n'
        self.assertEqual(runbooks.inventory_problems(good), [])
        bad = runbooks.inventory_problems(head + '| Place an order | the orders module | none | a flow |\n')
        self.assertEqual(len(bad), 1)
        self.assertIn('Place an order', bad[0])
        self.assertTrue(any('Read at' in p for p in runbooks.inventory_problems(good.replace('Read at: orders-service@3f2a91c04b7e', ''))))
        self.assertTrue(any('machine-local' in p for p in runbooks.inventory_problems(good + '\nClone: /Users/robin/code/orders\n')))


SECRETS = ('robin.vale@example.org', 'Robin Vale', 'hunter2hunter2', '0412 555 019', '/Users/robin/clients/acme-ledger.csv',
           'refund for the Harbour account', 'acme-ledger', 'Harbour', 'SELECT name FROM customers', 'customers',
           'overdue invoices', '4111111111111111', 'ledger-export.internal.example')


def tool(name, given, uid):
    return {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'id': uid, 'name': name, 'input': given}]}}


def result(uid, text, error=False):
    return {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'tool_use_id': uid, 'is_error': error,
                                                     'content': [{'type': 'text', 'text': text}]}]}}


class Summary(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name) / 'sessions'
        self.folder.mkdir()
        testenv.transcript(
            self.folder / 'a.jsonl',
            ('human', 'Robin Vale here, robin.vale@example.org: chase the overdue invoices, refund for the Harbour account'),
            ('agent-said', 'I will read /Users/robin/clients/acme-ledger.csv and call 0412 555 019'),
            tool('mcp__tracker__read_item', {'id': 'refund for the Harbour account'}, 't1'), result('t1', 'Robin Vale owes 40'),
            tool('mcp__tracker__read_item', {'id': 'x'}, 't2'), result('t2', 'Unauthorized: robin.vale@example.org', True),
            tool('Skill', {'skill': 'write-summary', 'args': 'overdue invoices'}, 't3'),
            tool('Read', {'file_path': '/Users/robin/clients/acme-ledger.csv'}, 't4'),
            tool('Bash', {'command': 'API_KEY=hunter2hunter2 curl -s https://ledger-export.internal.example/x?card=4111111111111111'}, 't5'),
            tool('Bash', {'command': '/Users/robin/bin/ledgerdump --account Harbour'}, 't6'),
            result('t6', 'zsh: command not found: ledgerdump for Robin Vale', True))
        (self.folder / 'nested').mkdir()
        testenv.transcript(
            self.folder / 'nested' / 'b.jsonl',
            tool('Bash', {'command': 'curl https://ledger-export.internal.example/y'}, 'u1'),
            tool('Bash', {'command': "curl -H 'X: hunter2hunter2' https://ledger-export.internal.example/z | psql -c 'SELECT name FROM customers'"}, 'u2'),
            tool('Bash', {'command': 'ledgerdump --all'}, 'u3'), result('u3', 'command not found', True),
            tool('Bash', {'command': 'ledgerdump --all'}, 'u4'), result('u4', 'command not found', True),
            tool('Bash', {'command': 'robin.vale@example.org'}, 'u5'),
            tool('refund for the Harbour account', {}, 'u6'),
            tool('mcp__acme-ledger customers__read', {}, 'u7'))
        (self.folder / 'broken.jsonl').write_text('not json Robin Vale\n{"type": "assistant", "message": "Harbour"}\n')
        (self.folder / 'notes.txt').write_text('Robin Vale: hunter2hunter2\n')

    def tearDown(self):
        self.tmp.cleanup()

    def test_the_summary_counts_tools_connectors_skills_and_what_was_missing(self):
        s = session_summary.summarise(self.folder)
        self.assertEqual(s['sessions'], 3)
        self.assertEqual(s['tools']['mcp__tracker__read_item'], {'calls': 2, 'failed': 1})
        self.assertEqual(s['tools']['Bash']['calls'], 7)
        self.assertEqual(s['connectors'], {'tracker': 2})
        self.assertEqual(s['skills'], {'write-summary': 1})
        self.assertEqual(s['programs'], {'curl': 3, 'ledgerdump': 3})
        self.assertIn(('ledgerdump', 'not installed', 3), s['missing'])
        self.assertIn(('mcp__tracker__read_item', 'no access', 1), s['missing'])
        self.assertEqual(s['unnamed'], 2, 'a tool whose name is not a plain identifier is counted, never named')

    def test_nothing_from_a_session_reaches_the_summary_but_names_and_counts(self):
        s = session_summary.summarise(self.folder)
        said = session_summary.render(s) + json.dumps(s)
        for secret in SECRETS:
            self.assertNotIn(secret, said, secret)
        self.assertNotIn(str(self.folder), said)
        allowed = set(session_summary.LABELS) | set(session_summary.FIXED_WORDS)
        for line in session_summary.render(s).splitlines():
            for cell in re.split(r'[|]', line):
                cell = cell.strip()
                self.assertTrue(not cell or cell in allowed or re.fullmatch(r'[-: ]+|\d+', cell) or session_summary.NAME.fullmatch(cell)
                                or line.startswith(('#', 'Sessions read', 'Only ')), f'unexpected text in the summary: {cell!r}')

    def test_a_program_run_fewer_times_than_the_minimum_is_not_named(self):
        self.assertNotIn('psql', json.dumps(session_summary.summarise(self.folder)))
        self.assertEqual(session_summary.summarise(self.folder, minimum=4)['programs'], {})

    def test_it_reads_only_the_folder_it_is_given_and_has_no_default(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(session_summary.main([]), 2)
            self.assertEqual(session_summary.main([str(self.folder / 'missing')]), 2)
        outside = Path(self.tmp.name) / 'elsewhere'
        outside.mkdir()
        testenv.transcript(outside / 'c.jsonl', tool('mcp__payroll__read', {}, 'v1'))
        (self.folder / 'link').symlink_to(outside)
        (self.folder / 'link.jsonl').symlink_to(outside / 'c.jsonl')
        self.assertNotIn('payroll', json.dumps(session_summary.summarise(self.folder)))
        source = (PART / 'scripts/session_summary.py').read_text()
        for word in ('environ', 'expanduser', 'Path.home', 'getenv'):
            self.assertNotIn(word, source, f'the summariser reaches for {word}')

    def test_the_written_summary_is_only_the_rendered_one(self):
        out = Path(self.tmp.name) / 'ws' / 'sessions' / 'first-load' / 'skill-usage.md'
        self.assertEqual(session_summary.main([str(self.folder), '--out', str(out)]), 0)
        text = out.read_text()
        self.assertEqual(text, session_summary.render(session_summary.summarise(self.folder)))
        for secret in SECRETS:
            self.assertNotIn(secret, text, secret)


if __name__ == '__main__':
    unittest.main()
