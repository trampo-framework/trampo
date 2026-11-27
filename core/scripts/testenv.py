"""Imported first by every test module, before the scripts: no test reads or writes the real home folder or the
machine's git config. The machine's own config and state go to a temp folder for the whole test process, and for
every process it starts."""
import atexit
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = tempfile.mkdtemp(prefix='trampo-test-')
atexit.register(shutil.rmtree, ROOT, True)
os.environ['XDG_CONFIG_HOME'] = os.path.join(ROOT, 'config')
os.environ['XDG_STATE_HOME'] = os.path.join(ROOT, 'state')
os.environ['CLAUDE_CONFIG_DIR'] = os.path.join(ROOT, 'runtime')
os.environ['GIT_CONFIG_GLOBAL'] = '/dev/null'
os.environ['GIT_CONFIG_NOSYSTEM'] = '1'
for name in ('TRAMPO_USER', 'TRAMPO_SID', 'CLAUDE_CODE_SESSION_ID', 'CLAUDE_PROJECT_DIR', 'CLAUDECODE'):
    os.environ.pop(name, None)
VERSION = json.loads((Path(__file__).resolve().parent.parent / '.claude-plugin' / 'plugin.json').read_text())['version']


def sh(cwd, *args):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def workspace(path, storage='git', who='Robin Vale', extra=''):
    """A workspace folder with its workspace.yaml; on git, a repository on main whose user is `who`."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    (path / 'workspace.yaml').write_text(f'storage: {storage}\ncore_version: {VERSION}\napprovers:\n  - Robin Vale\n{extra}')
    if storage == 'git':
        sh(path, 'git', 'init', '-q', '-b', 'main')
        sh(path, 'git', 'config', 'user.name', who)
        sh(path, 'git', 'config', 'user.email', 'test@example.invalid')
        (path / '.gitignore').write_text('.trampo/state/\n')
    return path


def transcript(path, *lines):
    """A session transcript: each line is ('human', text), ('agent-said', text), ('wrote', file path) or a dict."""
    out, sitting = [], Path(path).stem
    for n, line in enumerate(lines):
        stamp = f'2026-01-05T09:{n:02d}:00.000Z'
        if isinstance(line, dict):
            out.append(line)
        elif line[0] == 'human':
            out.append({'type': 'user', 'sessionId': sitting, 'origin': {'kind': 'human'}, 'timestamp': stamp,
                        'message': {'content': line[1]}})
        elif line[0] == 'injected':
            out.append({'type': 'user', 'sessionId': sitting, 'origin': {'kind': 'peer'}, 'timestamp': stamp,
                        'message': {'content': line[1]}})
        elif line[0] == 'wrote':
            out.append({'type': 'assistant', 'message': {'content': [
                {'type': 'tool_use', 'name': 'Write', 'input': {'file_path': str(line[1])}}]}})
        else:
            out.append({'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': line[1]}]}})
    Path(path).write_text(''.join(json.dumps(l) + '\n' for l in out))
    return str(path)


def project(ws):
    """The folder the runtime keeps a workspace's transcripts in: under its config folder, named after the path."""
    return Path(os.environ['CLAUDE_CONFIG_DIR']) / 'projects' / re.sub(r'[^A-Za-z0-9]', '-', os.path.realpath(ws))


def sitting(ws, sid, *lines):
    """The transcript of sitting `sid` in that workspace, where the runtime keeps it: one file per sitting."""
    f = project(ws) / f'{sid}.jsonl'
    f.parent.mkdir(parents=True, exist_ok=True)
    return transcript(f, *lines)
