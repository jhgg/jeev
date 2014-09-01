import logging
import re
import gevent
import time
from adapter import get_by_name
from .web import Web
from .module import Modules

logger = logging.getLogger('jeev.jeev')


class Jeev(object):
    def __init__(self, config):
        self.config = config
        self.adapter = get_by_name(config.adapter)(self, config.adapterOpts)
        self.modules = Modules(self)
        self.targeting_me_re = re.compile('^%s[%s]' % (re.escape(self.name.lower()), re.escape('!:, ')), re.I)
        self.web = None

    def _handle_message(self, message):
        # Schedule the handling of the message to occur during the next iteration of the event loop.
        gevent.spawn_later(0, self.__handle_message, message)

    def __handle_message(self, message):
        logger.debug("Incoming message %r", message)
        start = time.time()

        message.jeev = self
        message.targeting_jeev = bool(self.targeting_me_re.match(message.message))
        self.modules._handle_message(message)
        end = time.time()

        logger.debug("Took %.5f seconds to handle message %r", end - start, message)

    @property
    def name(self):
        return getattr(self.config, 'name', 'Jeev')

    def run(self, auto_join=True):
        self.adapter.start()
        self.modules.load_all()

        if getattr(self.config, 'web', False):
            self.web = Web(self)
            self.web.start()

        # If we are the main greenlet, chances are we probably want to never return,
        # so the main greenlet won't exit, and tear down everything with it.
        if auto_join and gevent.get_hub().parent == gevent.getcurrent():
            self.join()

    def join(self):
        self.adapter.join()

    def send_message(self, channel, message):
        self.adapter.send_message(channel, message)

    def send_attachment(self, channel, *attachments):
        if hasattr(self.adapter, 'send_attachment'):
            self.adapter.send_attachment(channel, *attachments)

        else:
            for a in attachments:
                self.adapter.send_message(channel, a.fallback)

    def on_module_error(self, module, e):
        print module, e