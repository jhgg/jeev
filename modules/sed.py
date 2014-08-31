import random
import re
import string
from operator import or_
from collections import deque, defaultdict
import signal
import gevent
from werkzeug.utils import escape
import module


translations = {
    'i': re.I,
    's': re.S,
    'u': re.U,
    'g': 0x100,
    'r': 0x200,
    'U': 0x400,
    'l': 0x800,
    't': 0x1000,
    'c': 0x2000,
    'C': 0x4000,
    'S': 0x8000,
    'R': 0x10000,
}

translationTable = (
    (0x200, lambda s: s[::-1]),
    (0x400, lambda s: s.upper()),
    (0x800, lambda s: s.lower()),
    (0x1000, lambda s: s.strip()),
    (0x2000, lambda s: s.capitalize()),
    (0x4000, lambda s: string.capwords(s)),
    (0x8000, lambda s: (lambda p: (random.shuffle(p), ''.join(p))[1])(list(s))),
    (0x10000, lambda s: s.encode('rot13'))
)


def doTranslation(str, flags):
    for flag, callback in translationTable:
        if flags & flag:
            str = callback(str)

    return str


channels = defaultdict(lambda: deque(maxlen=25))


def do_sed(message):
    if message.channel not in channels:
        return

    try:
        regex, replacement, flags, target = parse_sed(message.message[1:])
    except ValueError:
        return

    try:
        c = re.compile(regex, flags & 127)
    except re.error, e:
        return

    g = gevent.getcurrent()

    def raiseKeyboardInterrupt(s, i):
        print "timing out!", g
        gevent.spawn(message.reply, 'fk off with ur evil regex bro')
        g.throw(gevent.GreenletExit)

    # ## We install a signal handler, to timeout the regular expression match if it's taking too long, i.e. evil regexp
    # ##  s/^(a+)+$/rip/
    old_sighandler = signal.signal(signal.SIGALRM, raiseKeyboardInterrupt)
    signal.setitimer(signal.ITIMER_REAL, 0.05)
    try:
        m = c.search
        q = channels[message.channel]
        for i in xrange(-1, -len(q) - 1, -1):
            nick, line = q[i]
            if m(line) and (not target or nick.lower() == target):
                q[i] = nick, doTranslation(c.sub(replacement, line, 0 if flags & 0x100 else 1)[:400], flags)
                gevent.spawn_later(0, message.reply, '*%s*: %s' % (nick, escape(q[i][1])))
                break

    except re.error, e:
        return

    finally:
        ### Restore original handlers.
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_sighandler)


def parse_sed(message):
    q = deque(message)
    pop = q.popleft
    first_char = pop()
    if first_char == '\\':
        raise ValueError("Cannot be a backslash.")
    regex, replacement, flags, target = [], [], 0, None

    last_char = ''
    while q:
        char = pop()
        if char == first_char and last_char != '\\':
            break
        if last_char == '\\' and char == last_char and regex:
            regex.pop()
        regex.append(char)
        last_char = char

    last_char = ''
    while q:
        char = pop()
        if char == first_char and last_char != '\\':
            break
        if last_char == '\\' and char == last_char and replacement:
            replacement.pop()
        replacement.append(char)
        last_char = char

    if q:
        r = set()
        while q:
            char = pop()
            if char == ' ':
                break
            if char in translations:
                r.add(translations[char])

        target = ''.join(q).strip().lower() or None
        flags = reduce(or_, r) if r else 0

    return ''.join(regex), ''.join(replacement), flags, target


@module.listen()
def listener(message):
    if message.message.startswith('s/'):
        module.spawn(do_sed, message)

    else:
        channels[message.channel].append((message.user, message.message))




