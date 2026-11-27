#!/usr/bin/env python3
"""Call one of the team's slots: the only way a mode reaches a tracker, a person, a code host or monitoring.

  slot.py WORKSPACE SLOT VERB [ARG...] [--timeout SECONDS]

Runs the team's own program at <workspace>/slots/<slot> with the verb and arguments, in the workspace, and prints what
it answers marked as data. The contract of each slot is in protocols/slots.md. Exit: the slot's own status, 3 when the
slot is not filled in, 124 when it did not answer in time, 2 when the call itself is refused.
"""
import os
import subprocess
import sys
from pathlib import Path

import common
from untrusted import DATA, lines

SLOTS = ('tracker', 'ask', 'code-host', 'monitoring')
NOT_FILLED, TIMED_OUT = 3, 124
TIMEOUT = 60


def unapproved(ws, name, call):
    """The gated action this call is, by the team's own patterns, when the session running it holds no recorded yes for
    it; else None. The gate hook reads the line as typed. Here the arguments are what the shell made of them, so a name
    that reached the line through a variable is seen. A person at their own terminal is not a session and is not asked."""
    import approval
    import hooks
    import prepush
    if not any(os.environ.get(v) for v in prepush.SESSION_MARKS) or hooks.hook_mode(ws, 'gate') != 'block':
        return None
    said = ' '.join(call)
    here = common.active(ws, os.environ.get('CLAUDE_CODE_SESSION_ID'))
    done = {e.get('gate') for e in (common.session_events(ws, here[0]) if here else [])
            if e.get('ev') == 'approve' and approval.names(said, str(e.get('key') or e.get('subject') or ''))}
    return next((gate for gate, pattern in hooks.gate_patterns(approval.approved_config(ws), ws)
                 if gate not in done and (pattern.search(f'slot.py WS {name} {said}') or pattern.search(f'slots/{name} {said}'))), None)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    timeout = TIMEOUT
    if '--timeout' in argv[3:]:
        at = argv.index('--timeout', 3)
        timeout = int(argv[at + 1])
        del argv[at:at + 2]
    if len(argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2
    ws, name, *call = argv
    if name not in SLOTS:
        print(f"{name!r} is not a slot. The slots are: {', '.join(SLOTS)}", file=sys.stderr)
        return 2
    rel = f'slots/{name}'
    why = common.path_problem(ws, rel)
    if why:
        print(why, file=sys.stderr)
        return 2
    if not (Path(ws) / rel).is_file():
        print(f'the {name} slot is not filled in: the team writes {rel} (contract: protocols/slots.md). Until then, ask the '
              'person to do this step and tell you the result', file=sys.stderr)
        return NOT_FILLED
    gate = unapproved(ws, name, call)
    if gate:
        print(f'"{gate}" is a gated action and this session holds no recorded yes for it that names what this call names. '
              'Type the command plainly so the gate can ask an approver, and run it again after their yes', file=sys.stderr)
        return 2
    try:
        r = subprocess.run([str(Path(ws) / rel), *call], cwd=ws, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired:
        print(f'the {name} slot did not answer in {timeout} seconds and was stopped. Nothing it may have done is known: check '
              'before running it again', file=sys.stderr)
        return TIMED_OUT
    except OSError as e:
        print(f'the {name} slot could not be run ({e}): {rel} must be a program the machine can start', file=sys.stderr)
        return 2
    print(f'(What the {name} slot answered is below. It is {DATA}.)')
    print('\n'.join(lines(r.stdout)))
    if r.stderr.strip():
        print('\n'.join(lines(r.stderr)), file=sys.stderr)
    return r.returncode


if __name__ == '__main__':
    sys.exit(main())
