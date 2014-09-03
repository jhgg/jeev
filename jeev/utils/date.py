
_timeOrder = (
    ('week', 60 * 60 * 24 * 7),
    ('day', 60 * 60 * 24),
    ('hour', 60 * 60),
    ('minute', 60),
    ('second', 1)
)


def dateDiff(secs, n=True, short=False):
    """
        Converts seconds to x hour(s) x minute(s) (and) x second(s)

        >>> dateDiff(5)
        '5 seconds'
        >>> dateDiff(61)
        '1 minute and 1 second'
        >>> dateDiff(3615, n = False)
        '1 hour 15 seconds'

    """

    if not isinstance(secs, int):
        secs = int(secs)

    secs = abs(secs)
    if secs == 0:
        return '0 seconds'

    h = []
    a = h.append
    for name, value in _timeOrder:
        x = secs / value
        if x > 0:
            if short:
                a("%i%s" % (x, name[0]))
            else:
                a('%i %s%s' % (x, name, ('s', '')[x is 1]))
            secs -= x * value
    z = len(h)
    if n is True and not short and z > 1: h.insert(z - 1, 'and')

    return ' '.join(h)
