#!/usr/bin/env python3
"""How a gated action gets its yes.

Three things open a gate, and the assistant can write none of them: a message an approver typed in this session
that names the subject and says yes; an approver's bare yes through the team's ask-a-person bridge, read from the
bridge's own records; a standing grant an approver agreed to once. Who is an approver, what is gated and which
grants stand are read from the team's copy of the control files (origin's branch on storage: git), so an edit in
one working copy opens nothing until it has been approved and shared.

The typed-yes test is loose on purpose and is not a parse of the decision: verdict() reads the sentence that names
the subject and the sentences beside it, and the latest message with a verdict decides.
"""
import hashlib
import json
import os
import re
from datetime import date, datetime
from pathlib import Path

import common
from common import branch_of, git, listed, parse_yaml, same, state_dir, storage_of
from untrusted import shown

YES = re.compile(r'\b(yes|go ahead|approved?|do it|run it)\b', re.I)
NO = re.compile(r"\b(no|not|don'?t|wait|hold|stop)\b", re.I)
# A bridge reply approves only as a bare yes: any other word may carry a condition, and no word list names every one.
# A false refusal costs one more ask; a false pass runs the action.
SAID_YES = {'yes', 'y', 'approve', 'approved', 'ok', 'okay', 'agreed', 'agree', 'yep', 'yeah', 'sure'}
FILLER = {'please', 'go', 'ahead', 'run', 'it', 'thanks', 'for', 'and'}
WORD = re.compile(r"[a-z0-9']+")
BARE_MARKS = re.compile(r'^[\s,.!]*$')
CITE = re.compile(r'#\s*ask-yes\s+([\w.-]+)')
REPLIES = ('answer', 'note', 'objection')

# The paths that decide what the assistant may do. modes/ is left out: working instructions are edited directly.
# A directory counts whole, but only as a path component: hooks-old is not hooks.
CONTROL_FILES = ('workspace.yaml', 'constitution.md', 'memory/shared/grants.md', 'memory/shared/approval-gates.md', '.claude/settings.json')
CONTROL_DIRS = ('slots', 'agents', '.claude/hooks', '.claude/agents')
# each skill is approved under skills/<name>, never the bare name: a skill called notes is not opened by a yes about notes
SKILLS = '.claude/skills'
SKILL_NAME = re.compile(r'[a-z0-9][a-z0-9-]{2,}')
GRANTS = 'memory/shared/grants.md'


def control_label(rel):
    """The name a yes must carry to approve a change to this path, or None when the path is not a control path."""
    rel = Path(str(rel)).as_posix().casefold()
    rel = rel[2:] if rel.startswith('./') else rel
    for f in CONTROL_FILES:
        if rel == f.casefold():
            return f if f.startswith('.') else Path(f).name
    for d in CONTROL_DIRS:
        if rel.startswith(d.casefold() + '/'):
            return d + '/'
    if rel.startswith(SKILLS + '/'):
        first = rel[len(SKILLS) + 1:].split('/')[0]
        return 'skills/' + (first[:-3] if first.endswith('.md') else first)
    return None


def skill_problem(label):
    name = label[len('skills/'):] if label.startswith('skills/') else None
    if name is None or SKILL_NAME.fullmatch(name):
        return None
    return (f'{name!r} is not a name a skill can have: a skill is named in lower-case letters, digits and hyphens, three '
            'characters or more, so that a yes naming it cannot be a yes about something else')


def is_control(rel):
    return control_label(rel) is not None

# What no grant may open: approving or granting, and changing the gates, approvers, agents, grants, adapters or core rules
NEVER = re.compile(r'(?i)\b(approv(?:e|es|al|als|ing)|granting|standing grants?|grants? file|gates?|approvers?|agents?|adapters?|slots?|'
                   r'constitution|core rules?|hooks?|settings)\b')
STRONG = re.compile(r'(?i)\b(production|prod|merge|release|publish|create)\b')
FIELD = re.compile(r'(?m)^(Gate|Scope|Holder|Target|Ceiling|Expires|Reviewed|Approved-by):[ \t]*(.*)$')
DAY = re.compile(r'\d{4}-\d{2}-\d{2}')
REVIEW_DAYS = 90


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def approved_text(ws, rel):
    """A control file as the team last agreed it: origin's copy on storage: git once there is one, else the file
    on disk. An unshared edit in this copy counts for nothing."""
    if storage_of(ws) == 'git' and git(ws, 'rev-parse', '--verify', '-q', f'origin/{branch_of(ws)}')[0]:
        ok, out = git(ws, 'show', f'origin/{branch_of(ws)}:{rel}')
        return out + '\n' if ok else ''
    f = Path(ws) / rel
    return f.read_text(encoding='utf-8') if f.is_file() else ''


def approved_config(ws):
    return parse_yaml(approved_text(ws, 'workspace.yaml'))


def names(text, key):
    # a folder's key ends in its slash and is met by any path under it; agents/ is not met by .claude/agents/
    before = r'(?<![\w-])' + (r'(?<!\.claude/)' if key.endswith('/') and not key.startswith('.') else '')
    return bool(key) and bool(re.search(rf'{before}{re.escape(key)}' + ('' if key.endswith('/') else r'(?![\w-])'), text, re.I))


CONDITION = re.compile(r'\b(if|unless|until|once|after|when|provided|only|first|before|but|yet|as long as)\b', re.I)
OPENS_CONDITION = re.compile(r'^\W*(?:and |actually )?(?:if|unless|until|once|after|when|provided|only|but|as long as)\b', re.I)
SENTENCE = re.compile(r'(?<=[.!?])\s+')
# a refusal with fewer other words than this is about nothing else, so it is about the subject
ABOUT_SOMETHING = 4


def described(text, also):
    """Whether the text uses one of the other names the subject was shown under: a code whole, a word by its start."""
    return any(re.search(rf'(?<![\w-]){re.escape(a)}' + (r'(?![\w-])' if re.search(r'\d', a) else ''), text, re.I) for a in also)


# a refusal that points back at the thing just agreed to: "don't send it", "not that one", "hold this"
POINTS_BACK = re.compile(r"\b(?:no|not|don'?t|wait|hold|stop)\b(?:\W+[\w']+){0,2}?\W+(?:it|that|this)\b", re.I)


def action_words(gate):
    """The words of a gated action's name that a person would use for it."""
    return tuple(w for w in WORD.findall(str(gate).lower()) if len(w) > 3)


def verdict(text, key, also=(), action=()):
    """'yes', 'no' or None for what one typed message says about the subject. It is a no when the sentence naming the
    subject, or the one after it on the same line, refuses or sets a condition, or when the message holds a refusal
    too short to be about anything else. It is a yes when no such thing is found and a sentence that agrees, with no
    refusal or condition word in it, names the subject or is followed on its line by the sentence that does. A
    refusal elsewhere in the message is about another point and is not read. `also` is for the one item the sitting
    is waiting on: its other names count, and so does a short refusal that names nothing. `action` is the gated
    action's own words: one subject can have several gated actions, so beside an agreement that uses them, a longer
    sentence after it or a short refusal before it that does not use them is about another of those actions. What
    follows a colon in the agreeing sentence is the terms being agreed to, not a condition, unless it opens as one."""
    def named(s):
        return names(s, key) or described(s, also)

    def parts(s):
        head, colon, terms = s.partition(': ')
        return (head, terms) if colon and YES.search(head) and named(head) else (s, '')

    def refuses(s):
        head, terms = parts(s)
        return bool(NO.search(head) or CONDITION.search(head) or NO.search(terms) or OPENS_CONDITION.search(terms))

    def agrees(s, after):
        return bool(YES.search(parts(s)[0])) and not refuses(s) and (named(s) or named(after))

    def length(s):
        return len([w for w in WORD.findall(s.lower()) if not NO.fullmatch(w)])

    def elsewhere(s, other):
        return bool(action) and described(s, action) and not described(other, action) and not POINTS_BACK.search(other) \
            and not OPENS_CONDITION.search(other) and length(other) >= ABOUT_SOMETHING

    lines = [[s for s in SENTENCE.split(line.strip()) if s] for line in str(text).split('\n')]
    pairs = [(s, sents[i + 1] if i + 1 < len(sents) else '') for sents in lines for i, s in enumerate(sents)]
    if not also and not any(named(s) for s, _ in pairs):
        return None
    ours = max((i for i, (s, after) in enumerate(pairs) if action and agrees(s, after) and described(s, action)), default=-1)
    for i, (s, after) in enumerate(pairs):
        if named(s) and (refuses(s) or ((NO.search(after) or OPENS_CONDITION.search(after)) and not elsewhere(s, after))):
            return 'no'
        if NO.search(s) and length(s) < ABOUT_SOMETHING and not (i < ours and not described(s, action)):
            return 'no'
    if any(agrees(s, after) for s, after in pairs):
        return 'yes'
    return None


def typed(transcript):
    """What a person typed in this session, as [{text, at}]. Only a line the session itself marks as a person's:
    a message from another agent, a notification or the assistant's own words never count."""
    out = []
    for line in transcript.split('\n'):
        if '"user"' not in line:
            continue
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if not isinstance(e, dict) or e.get('type') != 'user' or (e.get('origin') or {}).get('kind') != 'human':
            continue
        c = (e.get('message') or {}).get('content')
        text = c if isinstance(c, str) else ' '.join(b.get('text', '') for b in c or [] if isinstance(b, dict) and b.get('type') == 'text')
        out.append({'text': text, 'at': when({'at': e.get('timestamp')}), 'stamp': e.get('timestamp'), 'sitting': e.get('sessionId')})
    return out


def when(e):
    try:
        return datetime.fromisoformat(str(e.get('at')).replace('Z', '+00:00')).timestamp()
    except ValueError:
        return 0


def bridge_files(ws):
    return sorted((state_dir(ws) / 'ask').glob('*.jsonl'))


def bridge_events(ws):
    """The bridge's records, one list per profile: ask, answer, withdrawn lines written by the team's adapter."""
    out = []
    for f in bridge_files(ws):
        events = []
        for line in f.read_text(encoding='utf-8', errors='replace').splitlines():
            e = json.loads(line) if line.strip() else None
            if isinstance(e, dict) and e.get('ev'):
                events.append(e)
        out.append(events)
    return out


def opens_yes(option):
    first = WORD.search(str(option[1]).lower()) if len(option) > 1 else None
    return bool(first) and first.group(0) in SAID_YES


def says_yes(text, options, key):
    """Whether a bridge reply is a bare yes. A letter is a yes only when the ask's option under that letter opens
    with one and no other option does. A question mark or any mark but , . ! may make it a question."""
    rest = re.sub(rf'(?<![\w-]){re.escape(key)}(?![\w-])', ' ', text.lower())
    words = WORD.findall(rest)
    if not words or not BARE_MARKS.match(WORD.sub(' ', rest)):
        return False
    picked = next((o for o in options if o and str(o[0]).lower() == words[0]), None)
    opens = opens_yes(picked) and sum(map(opens_yes, options)) == 1 if picked else words[0] in SAID_YES
    return opens and all(w in SAID_YES or w in FILLER for w in words[1:])


def thread_refusal(rid, key, threads, approvers):
    """Why the cited bridge reply does not approve this subject, or None."""
    for events in threads:
        reply = next((e for e in events if e.get('ev') == 'answer' and str(e.get('id')) == rid), None)
        if not reply:
            continue
        ask = next((e for e in events if e.get('ev') == 'ask' and e.get('key') == reply.get('key')), None)
        if not ask:
            return f'reply {rid} answers no ask for one subject'
        if not same(ask.get('subject', ''), key):
            return f"reply {rid} is on {shown(ask.get('subject'), 60)}'s ask, not {key}'s"
        if any(e.get('ev') == 'withdrawn' and e.get('key') == ask.get('key') for e in events):
            return f'reply {rid} answers an ask that was withdrawn'
        if not any(same(reply.get('by', ''), a) for a in approvers):
            return f"reply {rid} is {shown(reply.get('by'), 60)}'s, who is not an approver"
        last = sorted((e for e in events if e.get('ev') == 'answer' and e.get('key') == reply.get('key')
                       and same(e.get('by', ''), reply.get('by', ''))), key=when)[-1]
        if last.get('id') != reply.get('id'):
            return f"reply {rid} was followed by {last.get('id')} on the same ask; cite that one if it is a yes"
        if not says_yes(str(reply.get('text', '')), ask.get('options') or [], key):
            return (f"reply {rid}, {json.dumps(str(reply.get('text', ''))[:80])}, is not a yes: a reply approves only as a bare "
                    'yes, and a yes with a condition is a new question')
        return None
    return f'there is no reply {rid} in the bridge records'


NOBODY = ('nobody yet. A new workspace gets its approvers and its other control files from setup: `setup.py <workspace> show '
          "<answers>`, the person's typed agreement to that summary, then `setup.py <workspace> build <answers>`. Never ask a "
          'person to edit the file or type a command')


def decide(ws, key, transcript, text='', cfg=None, also=(), since=0, action=()):
    """(None, by, via, ref, proof) when an approver's latest word on this subject is a yes, else (why, None, None, None, {}).
    The proof ties the line the hook writes to the message it read, so that line cannot stand alone. `also` are other
    names the subject was shown under, read only in the messages typed from number `since` on."""
    approvers = listed(cfg if cfg is not None else approved_config(ws), 'approvers')
    me = common.identity(ws)
    mine = any(same(me, a) for a in approvers)
    read = [(t, verdict(t['text'], key, also if i >= since else (), action)) for i, t in enumerate(typed(transcript))]
    said = [{**t, 'yes': v == 'yes', 'who': me or 'the person here', 'via': 'typed'} for t, v in read if v]
    # an untimed typed line cannot be placed against a bridge reply, so it is placed where it fails closed
    said = [t if t['at'] else {**t, 'at': 0 if t['yes'] else float('inf')} for t in said]
    handed = [t for t in said if t['yes']] if not mine else []
    said = [t for t in said if mine or not t['yes']]
    why, rid = None, (CITE.search(text) or [None, None])[1]
    try:
        threads = bridge_events(ws)
        why = thread_refusal(rid, key, threads, approvers) if rid else None
        if rid and not why:
            reply = next(e for es in threads for e in es if e.get('ev') == 'answer' and str(e.get('id')) == rid)
            said.append({'text': reply.get('text'), 'at': when(reply), 'yes': True, 'who': reply.get('by'), 'via': 'bridge', 'ref': rid})
        for es in threads:
            asked = {e.get('key') for e in es if e.get('ev') == 'ask' and same(e.get('subject', ''), key)}
            said += [{'text': e.get('text'), 'at': when(e), 'yes': False, 'who': e.get('by')} for e in es
                     if e.get('ev') in REPLIES and e.get('key') in asked and NO.search(str(e.get('text', '')))
                     and any(same(e.get('by', ''), a) for a in approvers)]
    except (OSError, ValueError, StopIteration):
        why = f'reply {rid} could not be read from the bridge records'
    last = sorted(said, key=lambda t: t['at'])[-1] if said else None
    if last and last['yes'] and not why:
        proof = {'msg_sha': sha(str(last['text'])), 'msg_at': last.get('stamp')} if last['via'] == 'typed' else {}
        return None, last['who'], last['via'], last.get('ref'), proof
    if last and not last['yes'] and not why:
        why = (f"{shown(last['who'], 60)}'s latest message on {key}, {json.dumps(str(last['text'])[:80])}, is a no; it decides "
               'over any earlier yes')
    who = ', '.join(shown(a, 60) for a in approvers) or NOBODY
    if handed:
        why = (f"{shown(me, 60) or 'The person here'} is not an approver, so their yes does not open this gate. Hand over the "
               f'exact draft, say who can approve ({who}), and park the session: event.py close --park --cause approval-gate')
    return ((f'{why}.\n' if why else '') + f'This needs a yes for {key} from an approver ({who}): typed by them in this session, or '
            'their reply through the ask-a-person bridge, cited by ending the command with `# ask-yes <reply id>`. An '
            'unanswered ask is a no. Put it in your Needs you, with what a yes and a no would each change. A yes that '
            'carries a condition is a new question once the condition is met'), None, None, None, {}


def grants(ws, cfg=None, text=None):
    """Every entry of the grants file as the team agreed it, each with the problems that keep it from standing."""
    cfg = cfg if cfg is not None else approved_config(ws)
    text = approved_text(ws, GRANTS) if text is None else text
    approvers, out = listed(cfg, 'approvers'), []
    strong = [str(g).casefold() for g in listed(cfg, 'strong_gates')]
    parts = re.split(r'(?m)^## +(.+)$', text)
    for title, body in zip(parts[1::2], parts[2::2]):
        f = {k.lower(): v.strip() for k, v in FIELD.findall(body)}
        g = {'title': title.strip(), 'gate': f.get('gate', ''), 'target': f.get('target', ''), 'ceiling': f.get('ceiling', ''),
             'scope': [s.strip() for s in f.get('scope', '').split(',') if s.strip()],
             'holder': [s.strip().casefold() for s in f.get('holder', '').split(',') if s.strip()],
             'expires': (DAY.search(f.get('expires', '')) or [''])[0],
             'reviewed': (DAY.search(f.get('reviewed', '')) or DAY.search(title) or [''])[0], 'problems': []}
        by = f.get('approved-by', '')
        named = next((a for a in approvers if by.casefold().startswith(a.casefold())), None)
        for missing, word in ((not g['gate'], 'Gate'), (not g['scope'], 'Scope'), (not g['holder'], 'Holder')):
            if missing:
                g['problems'].append(f'it has no "{word}:" line; a grant names the gate it opens, its scope and its holder')
        if not named:
            g['problems'].append('its "Approved-by:" line names no approver; a grant stands only on an approver\'s recorded yes')
        elif not by[len(named):].strip():
            g['problems'].append('its "Approved-by:" line carries no reference (the session or the reply where they said yes)')
        if NEVER.search(g['gate']):
            g['problems'].append('it grants something on the never list (approving or granting, or changing the gates, approvers, '
                                 'agents, grants, adapters or core rules): a person does these through an approved proposal')
        if g['gate'].casefold() in strong or STRONG.search(g['gate']):
            if not g['target']:
                g['problems'].append('a strong action (production, merge, release, creating a tracker item) needs a "Target:" line '
                                     'naming the exact target')
            if 'any' in g['holder']:
                g['problems'].append('a strong action names its exact holder, never "any"')
        out.append(g)
    return out


def has_path(token, item):
    """Whether the item's path components appear, in order and whole, among the token's."""
    have, want = [x for x in token.split('/') if x], [x for x in item.split('/') if x]
    return bool(want) and any(have[i:i + len(want)] == want for i in range(len(have) - len(want) + 1))


def in_scope(ws, item, cwd, args):
    if item.startswith(('/', '~', './')):
        top = Path(os.path.realpath(os.path.expanduser(item if not item.startswith('./') else str(Path(ws) / item))))
        here = Path(os.path.realpath(cwd))
        return here == top or top in here.parents
    return any(has_path(t, item) for t in args)


def granted(ws, gate, kind, sid, cwd, args, cfg=None):
    """The standing grant that covers this action, or None. `args` are the words of the command the gate matched, comments
    dropped: a target or a scope named in a comment, or inside another word, is not what the command runs on."""
    today, me = date.today().isoformat(), common.identity(ws).casefold()
    for g in grants(ws, cfg):
        if (not g['problems'] and same(g['gate'], gate) and not (g['expires'] and g['expires'] < today)
                and any(h in ('any', str(kind).casefold(), str(sid).casefold(), me) for h in g['holder'])
                and any(in_scope(ws, s, cwd, args) for s in g['scope'])
                and (not g['target'] or any(t.rstrip('/') == g['target'].rstrip('/') for t in args))):
            return g
    return None


def grant_findings(ws, cfg):
    """(fails, warns) the health check reports about the grants file."""
    fails, warns = [], []
    days = (cfg.get('grants') or {}).get('review_days', REVIEW_DAYS) if isinstance(cfg.get('grants'), dict) else REVIEW_DAYS
    for g in grants(ws, cfg):
        fails += [f'{GRANTS}: "{shown(g["title"], 100)}": {p}. Until then it opens nothing' for p in g['problems']]
        try:
            age = (date.today() - date.fromisoformat(g['reviewed'])).days
        except ValueError:
            age = None
        if not g['problems'] and not g['ceiling'] and not g['expires'] and (age is None or age > days):
            warns.append(f'{GRANTS}: "{shown(g["title"], 100)}" has no ceiling and no expiry and has not been reviewed for '
                         f'{age if age is not None else "an unknown number of"} days (the team reviews at {days}): an approver '
                         'reads it and adds a "Reviewed: <date>" line, a ceiling or an expiry')
    return fails, warns


def proposal_targets(text):
    line = re.search(r'(?m)^target:[ \t]*(.+)$', text)
    return [t.strip() for t in line.group(1).split(',')] if line else []


def transcripts_dir():
    """Where the runtime keeps its transcripts: its config folder, which a person or a harness may have moved."""
    return Path(os.environ.get('CLAUDE_CONFIG_DIR') or Path.home() / '.claude') / 'projects'


def project_dirs(ws, top=None):
    """The folders the runtime keeps this workspace's transcripts in: one per spelling of the workspace's path."""
    # ponytail: the runtime names the folder after the path, each character that is no letter or digit made a dash,
    # and shortens a very long path its own way. A workspace on such a path is not found and its yes is refused at
    # the boundary; read the folder from the session start's own transcript path if that ever bites.
    top = Path(os.path.realpath(top or transcripts_dir()))
    return [top / re.sub(r'[^A-Za-z0-9]', '-', path) for path in dict.fromkeys((os.path.realpath(ws), os.path.abspath(ws)))]


def sitting_transcripts(ws, sitting, top=None):
    """The runtime's own transcripts of a sitting in this workspace, as text, found by the sitting's id. A path a
    ledger line names is never read, and neither is another workspace's folder: either would point the check at a
    file a session put there."""
    if not re.fullmatch(r'[\w-]{1,100}', sitting):
        return []
    files = [d / f'{sitting}.jsonl' for d in project_dirs(ws, top) if not d.is_symlink()]
    # the listing, not the open, says what the file is called: a file system that ignores case opens a look-alike
    return [f.read_text(encoding='utf-8', errors='replace') for f in files
            if f.is_file() and not f.is_symlink() and f.name in os.listdir(f.parent)]


def proof_problem(ws, e, approvers, strict=True, transcripts=None):
    """Why this approve line cannot be tied to a person's yes, or None. A line stands only on what the hook read: the
    message a person typed, found by its hash in the runtime's transcript of the line's sitting, or the bridge reply it
    cites. `strict` refuses a transcript that can no longer be read; the health check, reading old sittings, does not.
    `transcripts` names the runtime's transcript folder for a caller that must not take it from its environment."""
    if e.get('ev') != 'approve':
        return 'it is not an approve line'
    if e.get('via') == 'bridge':
        try:
            return thread_refusal(str(e.get('ref')), str(e.get('key', '')), bridge_events(ws), approvers)
        except (OSError, ValueError):
            return 'its bridge reply cannot be read from the bridge records'
    if e.get('via') != 'typed':
        return f"an approval of a control file is a typed yes or a bridge reply, not {shown(e.get('via'), 20)!r}"
    digest = str(e.get('msg_sha') or '')
    if not re.fullmatch(r'[0-9a-f]{64}', digest):
        return 'the approve line is not tied to a typed message: it carries no hash of one'
    sitting = str(e.get('sitting') or '')
    try:
        texts = sitting_transcripts(ws, sitting, transcripts)
    except OSError:
        texts = []
    if not texts:
        return ('the approve line cannot be tied to a typed message: the transcript of its sitting cannot be read on this '
                f'machine (looked in {project_dirs(ws, transcripts)[0]})') if strict else None
    for t in (t for text in texts for t in typed(text)):
        if t['sitting'] == sitting and sha(t['text']) == digest and verdict(t['text'], str(e.get('key') or '')) == 'yes':
            return None
    return 'no message a person typed in that sitting matches the approve line, so it is not a typed message'


def by_approver(e, approvers):
    return any(same(e.get('by', ''), a) for a in approvers)


def control_approval(ws, sid, rel, approval):
    """What a journaled write carries about its approval. A control file is written only under a proposal that names
    it under target: and that an approver said yes to, as the proposal reads now."""
    if not is_control(rel) and not approval:
        return {}
    if not approval:
        raise SystemExit(f'{rel} was not written: it is a control file, and it changes only as an approved proposal says. Write '
                         'proposals/<date>-<slug>.md with a "target:" line, show it to an approver, and journal with --approval '
                         'once they said yes to it by name')
    f = common.real(ws, approval)
    if not f or not re.fullmatch(r'proposals/[\w.-]+\.md', approval):
        raise SystemExit(f'{approval} is not a proposal file in this workspace (proposals/<date>-<slug>.md)')
    text = f.read_text(encoding='utf-8')
    if rel not in proposal_targets(text):
        raise SystemExit(f'{rel} was not written: {approval} does not name it under target:, and applying a proposal writes only '
                         'the files it names')
    approvers = listed(approved_config(ws), 'approvers')
    lines = [e for e in common.load_events(ws)[0] if e.get('ev') == 'approve' and e.get('proposal') == approval
             and e.get('text_sha') == sha(text) and by_approver(e, approvers)]
    problems = [proof_problem(ws, e, approvers) for e in lines]
    if not any(p is None for p in problems):
        why = f'; the approve line there says: {problems[-1]}' if problems else ''
        raise SystemExit(f'{rel} was not written: no approver has said yes to {approval} as it reads now{why}. Show them the whole '
                         'file; their typed yes naming it is read when the journal command runs. A changed proposal is shown again')
    return {'approval': approval, 'approval_sha': sha(text)}


def unapproved_control_writes(ws, events):
    """Journal lines that wrote a control file with no approval behind them: a ledger line someone wrote by hand, or an
    approve line the hook did not write."""
    approvers = listed(approved_config(ws), 'approvers')
    said = {(e.get('proposal'), e.get('text_sha')) for e in events if e.get('ev') == 'approve' and by_approver(e, approvers)
            and proof_problem(ws, e, approvers, strict=False) is None}
    return [f"{shown(e.get('path'), 120)} was written at {shown(e.get('ts'), 30)} with no approved proposal behind it, or one whose "
            'approve line is not tied to a typed message. It is a control file: a person reads the change and either restores '
            'the file or approves a proposal for it'
            for e in events if e.get('ev') in ('write', 'remove') and is_control(str(e.get('path', '')))
            and (e.get('approval'), e.get('approval_sha')) not in said]
