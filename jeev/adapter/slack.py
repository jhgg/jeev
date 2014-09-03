import json
import urlparse
import requests
from gevent.wsgi import WSGIServer
from gevent import spawn_raw
from ..message import Message


class SlackAdapter(object):
    """
        This adapter exposes a webhook that listens for slack messages.

        The web listener for this is independent of Jeev's WSGI server. They cannot run on the same port.

        This adapter works the same as Slack's Hubot adapter. So, when integrating with Jeev, from Slack's integration,
        use Hubot, and point it to the the adapter's listen host and port.
    """
    def __init__(self, jeev, opts):
        self._jeev = jeev
        self._opts = opts
        self._server = WSGIServer((self._opts('slack_listen_host', '0.0.0.0'),
                                   int(self._opts.get('slack_listen_port', 8080))), self._wsgi_app)

        self._link_names = str(self._opts.get('slack_link_names', False)).upper() == 'TRUE'
        self._channel_id_cache = {}
        self._requests = requests.Session()
        self._send_url = 'https://%s.slack.com/services/hooks/hubot?token=%s' % (self._opts['slack_team_name'],
                                                                                 self._opts['slack_token'])

    def _wsgi_app(self, environ, start_response):
        if environ['PATH_INFO'] == '/hubot/slack-webhook' and environ['REQUEST_METHOD'] == 'POST':
            status = '200 OK'
            data = environ['wsgi.input'].read()
            self._parse_message(data)

        else:
            status = '404 Not Found'

        start_response(status, [])
        return ['']

    def _parse_message(self, data):
        data = dict(urlparse.parse_qsl(data))

        if data['token'] == self._opts['token'] and data['team_domain'] == self._opts['team_name']:
            self._channel_id_cache[data['channel_name']] = data['channel_id']
            message = Message(data, data['channel_name'], data['user_name'], data['text'])
            self._jeev._handle_message(message)

    def start(self):
        self._server.start()

    def stop(self):
        self._server.stop()

    def send_message(self, channel, message):
        if channel not in self._channel_id_cache:
            return

        args = {
            'username': self._jeev.name,
            'text': message,
            'link_names': self._link_names,
            'channel': self._channel_id_cache[channel]
        }

        spawn_raw(self._requests.post, self._send_url, json.dumps(args))

    def send_messages(self, channel, *messages):
        for message in messages:
            self.send_message(channel, message)

    def send_attachment(self, channel, *attachments):
        if channel in self._channel_id_cache:
            channel = self._channel_id_cache[channel]
        elif not channel.startswith('#'):
            channel = '#' + channel

        args = {
            'username': self._jeev.name,
            'link_names': self._link_names,
            'channel': channel,
            'attachments': [a.serialize() for a in attachments]
        }

        for a in attachments:
            if not a.has_message_overrides:
                continue

            for k, v in a.message_overrides.items():
                args[k] = v

        spawn_raw(self._requests.post, self._send_url, json.dumps(args))


adapter = SlackAdapter