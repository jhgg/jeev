import urllib
from werkzeug.utils import escape
import module
import requests


@module.respond('search (?:hn|hacker ?news) for (.*)$')
@module.async()
def search_hn(message, query):
    r = requests.get('https://hn.algolia.io/api/v1/search?%s' % urllib.urlencode({
        'query': query,
        'tags': 'story',
        'hitsPerPage': 5

    }))
    if r.status_code == requests.codes.ok:
        json = r.json()
        hits = json['hits']
        body = ["%i results found, displaying first %i:" % (json['nbHits'], json['hitsPerPage'])]

        for i, hit in enumerate(hits, 1):
            text = ("%i. <%s|%s> by %s (%i points, %i comments)" % (
                i,
                escape(hit['url'] or 'https://news.ycombinator.com/item?id=%s' % hit['objectID']),
                escape(hit["_highlightResult"]['title']['value'].replace("<em>", "*").replace("</em>", '*')),
                hit['author'],
                hit['points'],
                hit['num_comments']
            ))

            body.append(text)

        message.reply('\n'.join(body))
