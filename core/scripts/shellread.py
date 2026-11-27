#!/usr/bin/env python3
"""The one place that reads shell command text for the hooks.

It is a reader of typed text, not a shell. A command can reach a file, a program or a push in ways no reading of
its text shows: a script file, a name built at run time, another language. The hooks that use it are tripwires for
the forms an assistant reaches for, and the boundary that holds is elsewhere (git's own pre-push hook, the health
check). The known ways around are tests in test_shellread.py, class Ceilings, and a list in docs/decisions.md.
"""
import re
import shlex

SEPARATORS = ';&|\n'
# Two shapes of text that cannot run, and only when nothing in them executes: a heredoc with a quoted delimiter read
# by cat or tee on a line with no pipe, and the whole segment of a search command
INERT_HEREDOC = re.compile(r'''^[^\n|`]*?\b(?:cat|tee)\b[^\n|`]*?<<-?\s*(['"])(\w+)\1[^\n|`]*\n[\s\S]*?\n\2(?=\n|$)''', re.M)
# a search tool's pre-processor and git grep's pager each run a program of their own
RUNS_INSIDE = re.compile(r'\$\(|`|--pre\b|--open-files-in-pager|\s-O')
SEARCH = re.compile(r'^\s*(?:\w+=\S*\s+)*(?:\S*/)?(?:grep|egrep|fgrep|rg|git\s+(?:grep|log))\b')


def segments(text):
    """The command split at ; & | and line breaks that sit outside quotes."""
    out, cur, quote = [], '', None
    for ch in text:
        if quote:
            quote = None if ch == quote else quote
            cur += ch
        elif ch in '"\'':
            quote, cur = ch, cur + ch
        elif ch in SEPARATORS:
            out.append(cur)
            cur = ''
        else:
            cur += ch
    return [*out, cur]


def live(cmd):
    """The command without the text in it that cannot run. Anything that could still reach a shell stays in."""
    text = INERT_HEREDOC.sub(lambda m: m.group(0) if '$(' in m.group(0) else m.group(0).split('\n')[0], cmd)
    return '\n'.join(s for s in segments(text) if not (SEARCH.search(s) and not RUNS_INSIDE.search(s)))


INTERPRETER = re.compile(r'(?<![\w./-])(?:python[\d.]*|node|ruby|perl|osascript)\b')
WRITE_API = re.compile(r'''open\([^)]*,\s*(?:mode\s*=\s*)?['"](?:[wax]|r\+)|\.open\(\s*['"][wax]|write_(?:text|bytes)|(?:append|write)FileSync|'''
                       r'createWriteStream|shutil\.(?:copy|move)|os\.(?:open|rename|replace)')
END = r'''["']?(?=$|[\s;&|)])'''
TOKEN = r'''["']?[^\s;&|<>"']*'''


def words(cmd):
    """The command as the arguments of each part, with the comments dropped: what a command line says it runs on, as
    opposed to every character in it."""
    out = []
    for seg in segments(cmd):
        try:
            toks = shlex.split(seg, comments=True)
        except ValueError:
            toks = []
            for t in seg.split():
                if t.startswith('#'):
                    break
                toks.append(t.strip('"\''))
        if toks:
            out.append(toks)
    return out


READS = ('--get', '--get-all', '--get-regexp', '--list', '-l', '--get-urlmatch')
GIT_VALUE_OPTIONS = ('-C', '-c', '--git-dir', '--work-tree', '--namespace')


def sets_git_name(cmd):
    """Whether the command sets, adds or removes the git user name: the one place a person's identity is read from on
    a git workspace. A courtesy check on the form an assistant reaches for, not a guard: a file written by another
    route, or a name given in an environment variable the hook never sees, passes."""
    for toks in words(live(cmd)):
        at = next((i for i, t in enumerate(toks) if t.rsplit('/', 1)[-1] == 'git'), None)
        if at is None:
            continue
        i = at + 1
        while i < len(toks) and toks[i].startswith('-'):
            i += 2 if toks[i] in GIT_VALUE_OPTIONS else 1
        rest = toks[i + 1:] if i < len(toks) and toks[i] == 'config' else []
        if 'user.name' in rest and not any(r in READS for r in rest):
            after = rest[rest.index('user.name') + 1:]
            if after or any(r.startswith(('--unset', '--add', '--replace')) for r in rest):
                return True
        if any(r in ('--unset', '--unset-all') for r in rest) and 'user.name' in rest:
            return True
    return False


def shell_write(cmd, names, raw=False):
    """Whether the command writes onto a file with one of these names, in a form an assistant reaches for: a
    redirect, tee, an in-place edit, a copy or move onto it, truncate, or an interpreter that names it and a write
    call. A variable assigned the name counts as the name. Reads pass. `raw` takes the names as patterns."""
    name = '(?:' + '|'.join(names if raw else map(re.escape, names)) + ')'
    if not re.search(name, cmd):
        return False
    held = re.findall(rf'(?:^|[\s;&(])(\w+)={TOKEN}{name}{END}', cmd)
    target = f'(?:{TOKEN}{name}{END}' + ''.join(rf'''|["']?\$\{{?{v}\}}?{END}''' for v in held) + ')'
    seg = r'[^;&|\n]*'
    forms = (rf'>>?\|?\s*{target}',
             rf'(?<![\w-])tee\b{seg}\s{target}',
             rf'(?<![\w-])(?:sed|perl)\b{seg}\s-\w*i{seg}\s{target}',
             rf'(?<![\w-])(?:cp|mv|install|rsync|ln|dd)\b{seg}\s(?:of=)?{target}\s*(?:$|[;&|\n)])',
             rf'(?<![\w-])truncate\b{seg}\s{target}')
    return any(re.search(f, cmd, re.M) for f in forms) or bool(INTERPRETER.search(cmd) and WRITE_API.search(cmd))


# ponytail: no parse ends the list of spellings (an alias, a pipe into a shell, another language's exec), so a line
# that names push and one of these words reads as a push that skips git's hooks, whatever it pushes
BYPASS_WORD = re.compile(r'--no-veri|hookspath|git_config|alias\.|claude_config_dir|(?<!\w)(?:home|xdg_config_home|git_dir|git_exec_path)=')
PUSH = re.compile(r'(?<![\w-])(?:git-)?push(?![\w-])')
RUNS_TEXT = re.compile(r'\$\(|`|<\(|>\(')
WRITES_FILE = re.compile(r'(?<![<>&\d])>{1,2}\s*(?!/dev/null|&)[^\s>&]')
SAYS = re.compile(r'^\s*(?:echo|printf)\b')
MESSAGE = re.compile(r'''\s(?:-[a-zA-Z]*m|--message)(?:\s+|=)(?:"[^"]*"|'[^']*'|\S+)''')
COMMIT = re.compile(r'^\s*git\s+(?:commit|tag)\b')

HEREDOC = re.compile(r"""^([^\n]*)<<-?\s*(['"]?)(\w+)\2([^\n]*)\n[\s\S]*?\n[ \t]*\3[ \t]*(?=\n|$)""", re.M)
QUOTED = re.compile(r""""[^"]*"|'[^']*'""")
# The few programs whose text is only recorded or printed: the event script's notes, a commit or tag message, and a
# part that reads or prints with its output going nowhere but the screen. Every other program is tested on all its words.
# The event script counts only where a program stands: after any variable assignments, an optional python and an
# optional path. A mention of its name further along is an argument of some other program.
EVENT = r"""\s*(?:\w+=\S*\s+)*(?:(?:\S*/)?python[\d.]*\s+(?:-[BIEsSuOqv]+\s+)*)?(?:\S*/)?event\.py\s"""
RECORDS = re.compile('^' + EVENT)
KEEPS_ITS_INPUT = re.compile(r'^\s*(?:cat|tee)\b|^' + EVENT + r'|^\s*git\s+(?:commit|tag)\b')
HANDS_ON = re.compile(r'(?<![\w./-])(?:(?:ba|z|da|k)?sh|eval|xargs|ssh)(?![\w.-])|\s-c(?=\s|$)')
ONLY_READS = re.compile(r'^\s*(?:\w+=\S*\s+)*(?:\S*/)?(?:cat|head|tail|less|more|ls|wc|file|stat|diff|cmp|echo|printf|'
                        r'grep|egrep|fgrep|rg|git\s+(?:show|diff|status|blame|ls-files|grep|log))(?=\s|$)')
# what one part prints, another part of the same line may run
PIPED_TO_A_RUNNER = re.compile(r'\|\s*(?:\w+\s+)?(?:\S*/)?(?:(?:ba|z|da|k)?sh|xargs|python[\d.]*|node|ruby|perl)\b')


def run(cmd):
    """What the command runs, as (text, words) for each part: the text is what a gate pattern is tested against, the
    words are every argument of that part. Left out of the text: a part that only reads or prints and sends its output
    to no file, a commit or tag message, the quoted notes handed to the event script, and a heredoc body one of those
    keeps. A part that redirects its output is tested whole, the file it writes included."""
    def said(m):
        opener = m.group(1) + m.group(4)
        return opener if KEEPS_ITS_INPUT.search(opener) and not re.search(r'\||\$\(|`', opener) and not HANDS_ON.search(opener) else m.group(0)

    fed, out = bool(PIPED_TO_A_RUNNER.search(cmd)), []
    for seg in segments(HEREDOC.sub(said, cmd)):
        writes = WRITES_FILE.search(QUOTED.sub('', seg))
        if not fed and not writes and ONLY_READS.search(seg) and not RUNS_INSIDE.search(seg):
            continue
        text = MESSAGE.sub(' ', seg) if COMMIT.search(seg) else seg
        if not fed and RECORDS.search(seg) and not HANDS_ON.search(QUOTED.sub('', seg)):
            text = QUOTED.sub(lambda q: q.group(0) if re.search(r'\$\(|`', q.group(0)) or not re.search(r'\s', q.group(0)) else ' ', text)
        toks, full = words(text), words(seg)
        if toks and full:
            out.append((' '.join(toks[0]), full[0]))
    return out


def spoken(cmd):
    """The line as the push tripwire reads it. On a line that pipes nothing, substitutes nothing and writes no file,
    echo and printf text, a search pattern, a commit message and an inert heredoc only name words, so they are
    dropped. Any other line is read whole: whether something on it runs the text is the parse this does not do."""
    bare = re.sub(r'''"[^"]*"|'[^']*\'''', '', cmd)
    if RUNS_TEXT.search(cmd) or WRITES_FILE.search(bare) or re.search(r'(?<!\|)\|(?!\|)', bare):
        return cmd
    kept = []
    for s in segments(live(cmd)):
        if SAYS.search(s):
            continue
        kept.append(MESSAGE.sub(' ', s) if COMMIT.search(s) else s)
    return ' ; '.join(kept)


def push_bypass(cmd):
    """Whether the line pushes and names a way to skip git's hooks, where the boundary check runs, or the variable
    that moves the runtime's transcript folder or git's own configuration and programs."""
    flat = re.sub(r'''['"\\]''', '', spoken(cmd)).lower()
    return bool(PUSH.search(flat) and BYPASS_WORD.search(flat))
