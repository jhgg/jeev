import logging
import os
import re
import gevent
import time
from adapter import get_by_name
from utils.env import EnvFallbackDict
from .web import Web
from .module import Modules
import shelve

logger = logging.getLogger('jeev.jeev')


class Jeev(object):
    _name = None
    _web = None
    _running = False
    _targeting_me = None
    _targeting_me_re = None

    def __init__(self, config):
        self.config = config
        self.adapter = get_by_name(config.adapter)(self, EnvFallbackDict('adapter', config.adapter_opts))
        self.modules = Modules(self)
        self.module_data_path = config.module_data_path
        self.opts = EnvFallbackDict('jeev', getattr(self.config, 'jeev_opts', {}))
        self.name = self.opts.get('name', 'Jeev')

    def _handle_message(self, message):
        # Schedule the handling of the message to occur during the next iteration of the event loop.
        gevent.spawn(self.__handle_message, message)

    def __handle_message(self, message):
        logger.debug("Incoming message %r", message)
        start = time.time()

        message._jeev = self
        message.targeting_jeev = bool(self._targeting_me(message.message))
        self.modules._handle_message(message)
        end = time.time()

        logger.debug("Took %.5f seconds to handle message %r", end - start, message)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value
        self._targeting_me_re = re.compile('^%s[%s]' % (re.escape(self._name.lower()), re.escape('!:, ')), re.I)
        self._targeting_me = self._targeting_me_re.match

    @property
    def running(self):
        return self._running

    @property
    def stopped(self):
        return not self._running

    def run(self, auto_join=True):
        """
            Runs Jeev, loading all the modules, starting the web service, and starting the adapter.

            If auto_join=True, this function will not return, and will run until jeev stops if starting jeev from
            outside of a greenlet.

        """
        if self._running:
            raise RuntimeError("Jeev is already running!")

        if not os.path.exists(self.module_data_path):
            os.makedirs(self.module_data_path)

        self.modules.load_all()

        if getattr(self.config, 'web', False):
            self._web = Web(self, EnvFallbackDict('web', getattr(self.config, 'web_opts', {})))
            self._web.start()

        self.adapter.start()
        self._running = True

        # If we are the main greenlet, chances are we probably want to never return,
        # so the main greenlet won't exit, and tear down everything with it.
        if auto_join and gevent.get_hub().parent == gevent.getcurrent():
            self.join()

    def join(self):
        """
            Blocks until Jeev is stopped.
        """
        if not self._running:
            raise RuntimeError("Jeev is not running!")

        self.adapter.join()

    def stop(self):
        """
            Stops jeev, turning off the web listener, unloading modules, and stopping the adapter.
        """
        if not self._running:
            raise RuntimeError("Jeev is not running!")

        try:
            self.modules.unload_all()

            if self._web:
                self._web.stop()
                self._web = None

            self.adapter.stop()

        finally:
            self._running = False

    def send_message(self, channel, message):
        """
            Convenience function to send a message to a channel.
        """
        self.adapter.send_message(channel, message)

    def send_attachment(self, channel, *attachments):
        if hasattr(self.adapter, 'send_attachment'):
            self.adapter.send_attachment(channel, *attachments)

        else:
            for a in attachments:
                self.adapter.send_message(channel, a.fallback)

    def on_module_error(self, module, e):
        print module, e

    def get_module_data(self, module):
        return shelve.open(os.path.join(self.module_data_path, module.name) + '.db', writeback=True)