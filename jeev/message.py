import random


class Message(object):
    """
        Represents an incoming message.
    """
    __slots__ = ['user', 'message', 'message_parts', 'channel', '_meta', '_jeev', 'targeting_jeev']

    def __init__(self, meta, channel, user, message):
        self.channel = channel
        self.user = user
        self.message = message
        self.message_parts = message.split()
        self._meta = meta
        self._jeev = None
        self.targeting_jeev = False

    def __repr__(self):
        return "<Message user: {m.user}, channel: {m.channel}, message: {m.message}>".format(m=self)

    def reply_to_user(self, message):
        message = '%s: %s' % (self.user, message)
        self.reply(message)

    def reply(self, message):
        self._jeev.send_message(self.channel, message)

    def reply_with_attachment(self, *attachment):
        self._jeev.send_attachment(self.channel, *attachment)

    def reply_random(self, choices):
        self.reply_to_user(random.choice(choices))

    def reply_with_one_of(self, *choices):
        self.reply_random(choices)

    reply_with_attachments = reply_with_attachment


class Attachment(object):
    __slots__ = ['pretext', 'text', 'fallback', '_color', '_fields', '_message_overrides']

    def __init__(self, pretext, text="", fallback="", fields=None):
        self.pretext = pretext
        self.text = text
        self.fallback = fallback or text or pretext
        self._color = 'good'
        self._fields = fields or []
        self._message_overrides = None

    def serialize(self):
        return {
            'pretext': self.pretext,
            'text': self.text,
            'color': self._color,
            'fallback': self.fallback,
            'fields': [
                f.serialize() for f in self._fields
            ]
        }

    def color(self, color):
        self._color = color
        return self

    def field(self, *args, **kwargs):
        self._fields.append(Attachment.Field(*args, **kwargs))
        return self

    @property
    def message_overrides(self):
        if self._message_overrides is None:
            self._message_overrides = {}

        return self._message_overrides

    @property
    def has_message_overrides(self):
        return self._message_overrides is not None

    def icon(self, icon):
        self.message_overrides['icon_url'] = icon
        return self

    def name(self, name):
        self.message_overrides['username'] = name
        return self

    class Field(object):
        __slots__ = ['title', 'value', 'short']

        def __init__(self, title, value, short=False):
            self.title = title
            self.value = value
            self.short = short

        def serialize(self):
            return {
                'title': self.title,
                'short': self.short,
                'value': self.value
            }