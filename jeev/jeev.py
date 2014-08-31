import re
import gevent
from adapter import get_by_name
from .module import Modules


class Jeev(object):
    def __init__(self, config):
        self.config = config
        self.adapter = get_by_name(config.adapter)(self, config.adapterOpts)
        self.modules = Modules(self)
        self.targeting_me_re = re.compile('^%s[%s]' % (re.escape(self.name.lower()), re.escape('!:, ')), re.I)

    def run(self, join=True):
        self.adapter.start()
        self.modules.load()

        if join:
            self.join()

    def join(self):
        self.adapter.join()

    def handle_message(self, message):
        gevent.spawn_later(0, self._handle_message, message)

    @property
    def name(self):
        return getattr(self.config, 'name', 'Jeev')

    def _handle_message(self, message):
        message.jeev = self
        message.targeting_jeev = bool(self.targeting_me_re.match(message.message))
        self.modules.handle_message(message)

    def send_message(self, channel, message):
        self.adapter.send_message(channel, message)

    def send_attachment(self, channel, attachment):
        if hasattr(self.adapter, 'send_attachment'):
            self.adapter.send_attachment(channel, attachment)

        else:
            self.adapter.send_message(channel, attachment.fallback)

    def on_module_error(self, module, e):
        print module, e