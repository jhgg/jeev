from lxml.html import fromstring
import requests
from werkzeug.utils import escape
import module


@module.respond('what should i eat')
@module.async(timeout=5)
def dinner(message):
    response = requests.get('http://whatthefuckshouldimakefordinner.com/')
    if response.status_code == requests.codes.ok:
        e = fromstring(response.text)
        dl = e.cssselect('dl')
        a, b = [(t.text_content()).strip() for t in dl[:2]]
        link = dl[1].xpath('dt/a')[0].attrib['href']
        message.reply_to_user(
            '%s <%s|%s>.' % (escape(a), link, escape(b))
        )