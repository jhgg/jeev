import json
import urlparse
import requests
from gevent.wsgi import WSGIServer
from ..message import Message


class SlackAdapter(object):
    def __init__(self, jeev, opts):
        self.jeev = jeev
        self.opts = opts
        self.server = WSGIServer((self.opts['listenHost'], self.opts['listenPort']), self.wsgi_app)
        self.channel_id_cache = {}
        self.requests = requests.Session()
        self.send_url = 'https://%s.slack.com/services/hooks/hubot?token=%s' % (self.opts['teamName'],
                                                                                self.opts['token'])

    def wsgi_app(self, environ, start_response):
        if environ['PATH_INFO'] == '/hubot/slack-webhook' and environ['REQUEST_METHOD'] == 'POST':
            status = '200 OK'
            data = environ['wsgi.input'].read()
            self.parse_message(data)

        else:
            status = '404 Not Found'

        start_response(status, [])
        return ['']

    def start(self):
        self.server.start()

    def stop(self):
        self.server.stop()

    def join(self):
        self.server.serve_forever()

    def parse_message(self, data):
        data = dict(urlparse.parse_qsl(data))

        if data['token'] == self.opts['token'] and data['team_domain'] == self.opts['teamName']:
            self.channel_id_cache[data['channel_name']] = data['channel_id']
            message = Message(data, data['channel_name'], data['user_name'], data['text'])
            self.jeev.handle_message(message)

    def send_message(self, channel, message):
        if channel not in self.channel_id_cache:
            return

        args = {
            'username': self.jeev.name,
            'text': message,
            'link_names': self.opts.get('linkNames', False),
            'channel': self.channel_id_cache[channel]
        }

        self.requests.post(self.send_url, json.dumps(args))

    def send_messages(self, channel, *messages):
        for message in messages:
            self.send_message(channel, message)

    def send_attachment(self, channel, *attachments):
        if channel in self.channel_id_cache:
            channel = self.channel_id_cache[channel]
        elif not channel.startswith('#'):
            channel = '#' + channel

        args = {
            'username': self.jeev.name,
            'link_names': self.opts.get('linkNames', False),
            'channel': channel,
            'attachments': [a.serialize() for a in attachments]
        }

        for a in attachments:
            for k, v in a.message_overrides.items():
                args[k] = v

        self.requests.post(self.send_url, json.dumps(args))

adapter = SlackAdapter