from datetime import datetime
from urllib import urlencode
import pytz
import requests
import module
from jeev.utils.date import dateDiff
from werkzeug.utils import escape

eastern = pytz.timezone("US/Eastern")


class TVRageParser(object):
    class episodeInfo(object):
        __slots__ = ['season', 'episode', 'name', 'date']

        def __init__(self, x):
            e, self.name, self.date = x.split('^', 2)
            self.season, self.episode = e.split('x', 1)

        def __repr__(self):
            return 'episodeInfo(season=%r, episode=%r, name=%r, date=%r)' % (
                self.season, self.episode, self.name, self.date
            )

    _specialParsers = {
        'Latest Episode': episodeInfo,
        'Next Episode': episodeInfo,
        'Genres': lambda x: x.split(' | '),
        'RFC3339': lambda x: None,
        'GMT+0 NODST': lambda x: datetime.fromtimestamp(int(x) + 3600, pytz.utc),
        'Started': lambda x: datetime.strptime(x, '%b/%d/%Y').date(),
        'Ended': lambda x: datetime.strptime(x, '%b/%d/%Y').date(),
        'Premiered': lambda x: datetime.strptime(x, '%Y').date(),
    }

    @classmethod
    def parse(cls, str):
        special = cls._specialParsers
        out = {}
        if str.startswith('<pre>'):
            str = str[5:]
        for line in str.splitlines():
            if '@' in line:
                key, val = line.split('@', 1)
                if key in special and val:
                    val = special[key](val)
                if val:
                    out[key] = val

        return out


@module.respond('when does (?:the next episode of )?(.*) air\??')
@module.async(timeout=5)
def next(message, show):
    res = requests.get('http://services.tvrage.com/tools/quickinfo.php?%s' % urlencode({'show': show}))
    if res.status_code != requests.codes.ok:
        return

    info = TVRageParser.parse(res.text)

    if 'Next Episode' in info:
        e = info['Next Episode']
        out = "The next episode(s) of *%s* " % info['Show Name']
        out += '(%s [%sx%s]) will air on %s' % (
            e.name, e.season, e.episode, info['Network'])

        if 'GMT+0 NODST' in info:
            airdate = info['GMT+0 NODST']
            now = eastern.normalize(pytz.utc.localize(datetime.now()))
            if now < airdate:
                diff = airdate - now
                out += ' in about *%s* on *%s*' % (dateDiff(
                    diff.seconds + diff.days * 3600 * 24
                ), eastern.normalize(airdate).strftime('%A, %B %d, %Y* at *%I:%M %p %Z')
                )

        message.reply_to_user(out)

    else:
        message.reply_to_user("I'm not sure when the next episode of *%s* will air." % (escape(info['Show Name'])))
