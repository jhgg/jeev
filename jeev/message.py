
class Message(object):
    def __init__(self, meta, channel, user, message):
        self.meta = meta
        self.channel = channel
        self.user = user
        self.message = message
        self.message_parts = message.split()
        self.jeev = None

    def __repr__(self):
        return "<Message user: {m.user}, channel: {m.channel}, message: {m.message}>".format(m=self)

    def reply_to_user(self, message):
        message = '%s: %s' % (self.user, message)
        self.reply(message)

    def reply(self, message):
        self.jeev.send_message(self.channel, message)

    def reply_with_attachment(self, attachment):
        self.jeev.send_attachment(self.channel, attachment)


class Attachment(object):

    def __init__(self, pretext, text="", fallback="", fields=None):
        self.pretext = pretext
        self.text = text
        self.fallback = fallback or text or pretext
        self._color = 'good'
        self.fields = fields or []
        self.message_overrides = {}

    def serialize(self):
        return {
            'pretext': self.pretext,
            'text': self.text,
            'color': self._color,
            'fallback': self.fallback,
            'fields': [
                f.serialize() for f in self.fields
            ]
        }

    def color(self, color):
        self._color = color
        return self

    def field(self, *args, **kwargs):
        self.fields.append(Attachment.Field(*args, **kwargs))
        return self

    def icon(self, icon):
        self.message_overrides['icon_url'] = icon
        return self

    def name(self, name):
        self.message_overrides['username'] = name
        return self

    class Field(object):
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