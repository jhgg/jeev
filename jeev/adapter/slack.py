from collections import defaultdict
import json
import logging
import weakref
from gevent import Greenlet, sleep
from slackclient._server import Server
from jeev.message import Message
from jeev import events

logger = logging.getLogger('jeev.adapter.slack')


class SlackAdapter(object):
    """
        This adapter exposes a webhook that listens for slack messages.

        The web listener for this is independent of Jeev's WSGI server. They cannot run on the same port.

        This adapter works the same as Slack's Hubot adapter. So, when integrating with Jeev, from Slack's integration,
        use Hubot, and point it to the the adapter's listen host and port.
    """

    class SlackObject(object):
        def __init__(self, data):
            self.data = data
            self._in_name_sets = set()

        @property
        def id(self):
            return self.data['id']

        @property
        def name(self):
            return self.data['name']

        def _iter_name_sets(self):
            pass

        def _link(self, name):
            self._in_name_sets.add(name)

        def _unlink(self):
            self._in_name_sets.clear()

        def iter_names(self):
            return iter(self._in_name_sets)

        def _update(self, **kwargs):
            for k, v in kwargs.iteritems():
                if k == 'ok':
                    continue

                self.data[k] = v

        def __str__(self):
            return self.name

    class SlackUser(SlackObject):
        @property
        def presence(self):
            return self.data['presence']

        def __repr__(self):
            return '<SlackUser id=%r, name=%r, presence=%s>' % (self.id, self.name, self.presence)

    class _SlackChannelBase(SlackObject):
        is_direct_message = False

        def __init__(self, data, adapter):
            super(SlackAdapter._SlackChannelBase, self).__init__(data)
            self._adapter = adapter

        @property
        def topic(self):
            if 'topic' in self.data:
                return self.data['topic']['value']

        @topic.setter
        def topic(self, val):
            if val != self.data['topic']:
                self._adapter.api.channels.setTopic(channel=self, topic=val)

        @property
        def purpose(self):
            if 'purpose' in self.data:
                return self.data['purpose']['value']

        @purpose.setter
        def purpose(self, val):
            raise NotImplementedError("Bots cannot set channel purpose.")

    class SlackChannel(_SlackChannelBase):
        @property
        def members(self):
            members = []
            for m in self.data['members']:
                members.append(self._adapter._users[m])

            return members

        def _left(self, archive=False):
            keep_keys = 'created', 'creator', 'id', 'is_archived', 'is_channel', 'is_general'
            for k in self.data.keys():
                if k not in keep_keys:
                    del self.data[k]

            self.data.update(
                members=[],
                is_member=False
            )
            if archive:
                self.data['is_archived'] = True

        def __repr__(self):
            return "<SlackChannel id=%r, name=%r, members=%r>" % (
                self.id, self.name, self.members
            )

    class SlackDirectMessage(_SlackChannelBase):
        is_direct_message = True

        @property
        def user(self):
            return self._adapter._users[self.data['user']]

        @property
        def members(self):
            return [self.user]

        def __repr__(self):
            return '<SlackDirectMessage id=%r, name=%r, user=%r>' % (
                self.id, self.name, self.user
            )

    class SlackObjectList(object):
        def __init__(self):
            self._obj_by_id = {}
            self._obj_by_name = defaultdict(set)

        def clear(self):
            self._obj_by_id.clear()
            self._obj_by_name.clear()

        def add(self, obj):
            if obj in self:
                self.remove(obj)

            self._obj_by_id[obj.id] = obj
            name = obj.name.lower()
            obj._link(name)
            self._obj_by_name[obj.name.lower()].add(obj)

        def remove(self, obj):
            self._obj_by_id.pop(obj.id)
            for name in obj.iter_names():
                self._obj_by_name[name].discard(obj)

            obj._unlink()

        def __contains__(self, item):
            if isinstance(item, SlackAdapter.SlackObject):
                return item.id in self._obj_by_id and self._obj_by_id[item.id] is item

            else:
                return item in self._obj_by_id

        def __getitem__(self, key):
            if key in self._obj_by_id:
                return self._obj_by_id[key]

            raise KeyError(key)

        def __delitem__(self, key):
            if key in self._obj_by_id:
                obj = self._obj_by_id[key]
                self.remove(obj)
            else:
                raise KeyError(key)

        def find(self, name_or_id):
            if name_or_id in self:
                return self[name_or_id]

            name_or_id = name_or_id.lower()
            if name_or_id in self._obj_by_name:
                return next(iter(self._obj_by_name[name_or_id]), None)

        def names(self):
            return [k for k, v in self._obj_by_name.iteritems() if v]

    class SlackApi(object):
        def __init__(self, adapter=None, parent=None, part=None):

            if parent:
                self._adapter = parent._adapter
                self._parts = parent._parts[:]
            else:
                self._parts = []
                self._adapter = adapter

            if part:
                self._parts.append(part)

        def __getattr__(self, item):
            return SlackAdapter.SlackApi(parent=self, part=item)

        def __call__(self, **kwargs):
            for k, v in kwargs.items():
                if isinstance(v, SlackAdapter.SlackObject):
                    kwargs[k] = v.id

            method = '.'.join(self._parts) or '?'
            logger.debug('Making API call %r with args %r', method, kwargs)
            result = json.loads(self._adapter._server.api_call(method, **kwargs))
            logger.debug('Got response %r', result)
            result = self._adapter._process_post_method_hooks(method, kwargs, result)
            return result

    class MutableOutgoingMessage(object):
        def __init__(self, adapter, channel, message):
            self.channel = channel
            self.adapter = adapter
            self.id = adapter._generate_message_id()
            self.message = message
            self.needs_update = False
            self.ts = None

        def _recv_reply(self, data):
            self.ts = data['ts']
            if self.needs_update:
                self._do_update()

        def _do_update(self):
            self.adapter.api.chat.update(
                ts=self.ts,
                channel=self.channel.id,
                text=self.message
            )
            self.needs_update = False

        def update(self, message):
            self.message = message
            if self.ts:
                self._do_update()
            else:
                self.needs_update = True

        def serialize(self):
            return {
                'text': self.message,
                'channel': self.channel.id,
                'type': 'message',
                'id': self.id
            }

        def __repr__(self):
            return "<MutableOutgoingMessage id=%r, channel=%r, message=%r>" % (
                self.id, self.channel, self.message
            )

    def __init__(self, jeev, opts):
        self._jeev = jeev
        self._opts = opts
        self._server = None
        self._greenlet = None
        self._channels = self.SlackObjectList()
        self._dms = self.SlackObjectList()
        self._groups = self.SlackObjectList()
        self._users = self.SlackObjectList()
        self._outgoing_messages = {}
        self._last_id = 1
        self.api = self.SlackApi(self)

    def start(self):
        if self._greenlet:
            raise RuntimeError("SlackAdapter Already Started.")
        self._greenlet = Greenlet(self._run)
        self._greenlet.start()

    def stop(self):
        self._greenlet.kill()

    def _run(self):
        while True:
            self._do_slack_connection()
            sleep(10)

    def _do_slack_connection(self):
        if self._server:
            self._server.websocket.abort()

        self._server = Server(self._opts['slack_token'], False)
        self._server.rtm_connect()
        self._parse_login_data(self._server.login_data)
        self._server.websocket.sock.setblocking(1)
        self.api.im.close(channel='D038BM8HQ')

        while True:
            frame = self._server.websocket.recv()
            self._handle_frame(frame)

    def _handle_frame(self, frame):
        data = json.loads(frame)
        logger.debug("Got frame %r", frame)

        if 'reply_to' in data:
            message = self._outgoing_messages.pop(data['reply_to'], None)
            if message:
                logger.debug("Received reply for Message: %r", message)
                message._recv_reply(data)

        if 'type' not in data:
            return

        handler = getattr(self, '_handle_%s' % data['type'], None)
        if handler:
            return handler(data)

        else:
            logger.debug("No handler defined for message type %s", data['type'])

    def _handle_message(self, data):
        if 'subtype' not in data and 'reply_to' not in data:
            message = Message(data, self._get_channel_or_dm(data['channel']), self._users[data['user']],
                              data['text'])

            return self._jeev._handle_message(message)

    def _handle_user_change(self, data):
        user = self._users[data['user']['id']]
        user._update(**data['user'])
        self._users.add(user)
        self._broadcast_event(events.User.Changed, user=user)

    def _handle_presence_change(self, data):
        user = self._users[data['user']]
        user._update(presence=data['presence'])
        self._broadcast_event(events.User.PresenceChanged, user=user)

    def _handle_channel_created(self, data):
        channel = data['channel'].copy()
        channel.update(members=[], is_general=False, is_member=False, is_archived=False)
        channel = self.SlackChannel(channel, self)
        self._channels.add(channel)
        self._broadcast_event(events.Channel.Created, channel=channel)

    def _handle_channel_left(self, data):
        channel = self._channels[data['channel']]
        channel._left()
        self._broadcast_event(events.Channel.Left, channel=channel)

    def _handle_channel_deleted(self, data):
        self._handle_channel_left(data)
        channel = self._channels[data['channel']]
        self._channels.remove(channel)
        self._broadcast_event(events.Channel.Deleted, channel=channel)

    def _handle_channel_rename(self, data):
        channel = self._channels[data['channel']['id']]
        channel._update(**data['channel'])
        self._channels.add(channel)
        self._broadcast_event(events.Channel.Renamed, channel=channel)

    def _handle_channel_archive(self, data):
        channel = self._channels[data['channel']]
        channel._left(archive=True)
        self._broadcast_event(events.Channel.Archived, channel=channel)

    def _handle_channel_unarchive(self, data):
        channel = self._channels[data['channel']]
        channel._update(is_archived=False)
        self._broadcast_event(events.Channel.UnArchived, channel=channel)

    def _handle_channel_joined(self, data):
        channel_id = data['channel']['id']
        if channel_id in self._channels:
            channel = self._channels[channel_id]
            channel._update(**data['channel'])
            self._channels.add(channel)
        else:
            channel = self.SlackChannel(data['channel'], self)
            self._channels.add(channel)
            self._broadcast_event(events.Channel.Created, channel=channel)

        self._broadcast_event(events.Channel.Joined, channel=channel)

    def _process_team_join(self, data):
        user = self.SlackUser(data['user'])
        self._users.add(user)
        self._broadcast_event(events.Team.Joined, user=user)

    def _parse_login_data(self, login_data):
        import pprint

        pprint.pprint(login_data)
        self._users.clear()
        self._channels.clear()
        self._dms.clear()
        self._outgoing_messages.clear()

        for user in login_data['users']:
            self._users.add(self.SlackUser(user))

        for dm in login_data['ims']:
            self._dms.add(self.SlackDirectMessage(dm, self))

        for channel in login_data['channels']:
            self._channels.add(self.SlackChannel(channel, self))

    def _process_post_method_hooks(self, method, kwargs, data):
        if data['ok']:
            if method == 'channels.setTopic':
                channel = self._channels[kwargs['channel']]
                channel._update(**data)

        return data

    def _broadcast_event(self, event, **kwargs):
        pass

    def send_message(self, channel, message):
        if not isinstance(channel, SlackAdapter._SlackChannelBase):
            channel = self._channels.find(channel)

        if not channel:
            raise RuntimeError("Channel with name or ID of %s not found." % channel)

        message = SlackAdapter.MutableOutgoingMessage(self, channel, message)
        logging.debug("Sending message %r", message)
        self._server.send_to_websocket(message.serialize())
        self._outgoing_messages[message.id] = message
        return message

    def send_messages(self, channel, *messages):
        for message in messages:
            self.send_message(channel, message)

    def send_attachment(self, channel, *attachments):
        if not isinstance(channel, SlackAdapter._SlackChannelBase):
            channel = self._channels.find(channel)

        if not channel:
            raise RuntimeError("Channel with name or ID of %s not found." % channel)

        args = {
            'type': 'message',
            'channel': channel.id,
            'attachments': [a.serialize() for a in attachments]
        }

        for a in attachments:
            if not a.has_message_overrides:
                continue

            for k, v in a.message_overrides.items():
                args[k] = v

        self._server.send_to_websocket(args)

    def _generate_message_id(self):
        self._last_id += 1
        return self._last_id

    def _get_channel_or_dm(self, id):
        if id.startswith('D'):
            return self._dms[id]

        else:
            return self._channels[id]


adapter = SlackAdapter