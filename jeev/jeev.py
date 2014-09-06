import logging
import re
import gevent
import time
from gevent.event import Event
from .adapter import get_adapter_by_name
from .utils.periodic import Periodic
from .storage import get_store_by_name
from .web import Web
from .module import Modules
from .utils.env import EnvFallbackDict
from . import version

logger = logging.getLogger('jeev.jeev')


class Jeev(object):
    _name = None
    _web = None
    _targeting_me = None
    _targeting_me_re = None

    def __init__(self, config):
        opts_for = lambda name: EnvFallbackDict(name, getattr(config, '%s_opts' % name, {}))

        self._opts = EnvFallbackDict(None, getattr(config, 'jeev_opts', {}))
        storage_class = get_store_by_name(self._opts.get('storage', getattr(config, 'storage', 'shelve')))
        adapter_class = get_adapter_by_name(self._opts.get('adapter', getattr(config, 'adapter', 'console')))

        self.config = config

        self._storage = storage_class(self, opts_for('storage'))
        self.adapter = adapter_class(self, opts_for('adapter'))
        self.modules = Modules(self)
        self.name = self._opts.get('name', 'Jeev')
        self._storage_sync_periodic = Periodic(int(self._opts.get('storage_sync_interval', 600)),
                                               self.modules._save_loaded_module_data)
        self._stop_event = Event()
        self._stop_event.set()

    def _handle_message(self, message):
        # Schedule the handling of the message to occur during the next iteration of the event loop.
        gevent.spawn_raw(self.__handle_message, message)

    def __handle_message(self, message):
        logger.debug("Incoming message %r", message)
        start = time.time()

        message._jeev = self
        message.targeting_jeev = bool(self._targeting_me(message.message))
        self.modules._handle_message(message)
        end = time.time()

        logger.debug("Took %.5f seconds to handle message %r", end - start, message)

    def _get_module_data(self, module):
        logger.debug("Getting module data for module %s", module.name)
        return self._storage.get_data_for_module_name(module.name)

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
        return not self._stop_event.is_set()

    @property
    def stopped(self):
        return not self.running

    @property
    def version(self):
        return version

    def run(self, auto_join=False):
        """
            Runs Jeev, loading all the modules, starting the web service, and starting the adapter.

            If auto_join=True, this function will not return, and will run until jeev stops if starting jeev from
            outside of a greenlet.

        """
        if self.running:
            raise RuntimeError("Jeev is already running!")

        logger.info("Starting Jeev v%s", self.version)

        logger.info("Starting storage %s", self._storage)
        self._storage.start()

        logger.info("Loading modules")
        self.modules.load_all()

        if getattr(self.config, 'web', False) or str(self._opts.get('web', False).upper() == 'TRUE'):
            self._web = Web(self, EnvFallbackDict('web', getattr(self.config, 'web_opts', {})))
            self._web.start()

        logger.info("Starting adapter %s", self.adapter)
        self.adapter.start()
        self._storage_sync_periodic.start(right_away=False)
        self._stop_event.clear()

        # If we are the main greenlet, chances are we probably want to never return,
        # so the main greenlet won't exit, and tear down everything with it.
        if auto_join and gevent.get_hub().parent == gevent.getcurrent():
            self.join()

    def join(self, timeout=None):
        """
            Blocks until Jeev is stopped.
        """
        if self.stopped:
            raise RuntimeError("Jeev is not running!")

        self._stop_event.wait(timeout)

    def stop(self):
        """
            Stops jeev, turning off the web listener, unloading modules, and stopping the adapter.
        """
        if self.stopped:
            raise RuntimeError("Jeev is not running!")

        logger.info('Stopping Jeev')
        try:
            self.modules.unload_all()

            if self._web:
                self._web.stop()
                self._web = None

            self.adapter.stop()
            self._storage_sync_periodic.stop()
            self._storage.stop()

        finally:
            self._stop_event.set()

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
