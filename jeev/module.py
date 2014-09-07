from collections import defaultdict
import bisect
import functools
import logging
import re
import gevent
import sys
from .utils.importing import import_first_matching_module
from .utils.periodic import ModulePeriodic
from .utils.g import G
from .utils.env import EnvFallbackDict

logger = logging.getLogger('jeev.module')


class Modules(object):
    """
        Holds all the loaded modules for a given Jeev instance.
    """
    _reserved_module_names = {'jeev', 'web', 'adapter'}

    def __init__(self, jeev):
        self.jeev = jeev
        self._module_list = []
        self._module_dict = {}

    def _handle_message(self, message):
        for module in self._module_list:
            module._handle_message(message)

    def _save_loaded_module_data(self):
        logger.info('Saving loaded module data')
        for module in self._module_list:
            module._save_data()

    def _import_module(self, name, module_instance):
        try:
            sys.modules['module'] = module_instance
            name, module = import_first_matching_module(name, ['modules.%s', 'jeev_modules.%s'])
            return module

        finally:
            sys.modules.pop('module')
            sys.modules.pop(name, None)

    def load_all(self, modules=None):
        """
            Loads all the modules defined in Jeev's configuration
        """
        if modules is None:
            if 'modules' in self.jeev._opts:
                modules = self.jeev._opts['modules']

            else:
                modules = getattr(self.jeev.config, 'modules', {})

        if isinstance(modules, str):
            modules = modules.split(',')

        if not isinstance(modules, dict):
            modules = {k: {} for k in modules}

        for module_name, opts in modules.iteritems():
            self.load(module_name, opts)

    def load(self, module_name, opts):
        """
            Load a module by name.
        """
        if module_name in self._module_dict:
            raise RuntimeError("Trying to load duplicate module!")

        if module_name in self._reserved_module_names:
            raise RuntimeError("Cannot load reserved module named %s" % module_name)

        try:
            logger.debug("Loading module %s", module_name)

            module_instance = Module(module_name)
            imported_module = self._import_module(module_name, module_instance)

            module_instance.author = getattr(
                imported_module, 'author', getattr(imported_module, '__author__', None))

            module_instance.description = getattr(
                imported_module, 'description', getattr(imported_module, '__doc__', None))

            logger.debug("Registering module %s", module_name)
            module_instance._register(self, opts)
            self._module_list.append(module_instance)
            self._module_dict[module_name] = module_instance

            logger.info("Loaded module %s", module_name)

        except Exception, e:
            logger.exception("Could not load module %s", module_name)
            raise e

    def unload(self, module_name):
        """
            Unload a module by name.
        """
        logger.debug("Unloading module %s", module_name)
        module = self._module_dict[module_name]
        module._unload()
        del self._module_dict[module_name]
        self._module_list.remove(module)

    def get_module(self, name, default=None):
        """
            Gets a module by name.
        """
        return self._module_dict.get(name, default)

    def unload_all(self):
        """
            Unloads all modules.
        """
        for module in self._module_dict.keys():
            self.unload(module)


class Module(object):
    """
        The brains of a Jeev module.

        This class is not subclassed, but rather is imported from a module's file, and then used to bind events and
        handlers to by using decorator functions. The injection magic happens in `Modules.load`.

        A simple module that replies teo hello would look like this:

        import module

        @module.hear('hello')
        def hello(message):
            message.reply_to_user('hey!')

    """
    STOP = object()
    __slots__ = ['jeev', 'opts', '_name', 'author', 'description',
                 '_commands', '_message_listeners', '_regex_listeners', '_loaded_callbacks', '_unload_callbacks',
                 '_running_greenlets', '_data', '_app', '_g']

    def __init__(self, name, author=None, description=None):
        self.author = author
        self.description = description
        self.jeev = None
        self.opts = None

        self._name = name
        self._g = None
        self._commands = defaultdict(list)
        self._message_listeners = []
        self._regex_listeners = []
        self._loaded_callbacks = []
        self._unload_callbacks = []
        self._running_greenlets = set()
        self._data = None
        self._app = None

    def _unload(self):
        for callback in self._unload_callbacks:
            self._call_function(callback)

        self._regex_listeners[:] = []
        self._loaded_callbacks[:] = []
        self._message_listeners[:] = []
        self._commands.clear()
        self._save_data(close=True)
        self._clean_g()
        self._app = None
        self.jeev = None
        self.opts = None

        gevent.killall(list(self._running_greenlets), block=False)
        self._running_greenlets.clear()

    def _register(self, modules, opts):
        self.jeev = modules.jeev
        self.opts = EnvFallbackDict(self.name, opts)
        for callback in self._loaded_callbacks:
            self._call_function(callback)

    def _call_function(self, f, *args, **kwargs):
        try:
            logger.debug("module %s calling %r with %r %r)", self._name, f, args, kwargs)
            return f(*args, **kwargs)
        except Exception, e:
            self._on_error(e)

    def _handle_message(self, message):
        for _, f in self._message_listeners:
            if self._call_function(f, message) is self.STOP:
                return

        if message.message_parts:

            command = message.message_parts[0]
            if command in self._commands:
                for _, f in self._commands[command]:
                    if self._call_function(f, message) is self.STOP:
                        return

            for _, regex, responder, f in self._regex_listeners:
                if responder and not message.targeting_jeev:
                    continue

                match = regex.search(message.message)
                if match:
                    kwargs = match.groupdict()

                    if kwargs:
                        args = ()
                    else:
                        args = match.groups()

                    if self._call_function(f, message, *args, **kwargs) is self.STOP:
                        return

    def _on_error(self, e):
        """
            Called when an error happens by something this module called.
        """
        if isinstance(e, gevent.Greenlet):
            e = e.exception

        self.jeev.on_module_error(self, e)
        logger.exception("Exception raised %r", e)

    def _make_app(self):
        """
            Make a flask application to be the wsgi handler of this module.
            If you want to use your own WSGI handler, you can simply call `module.set_wsgi_handler(handler)` before
            accessing `module.app`.
        """
        import flask

        return flask.Flask('modules.%s' % self.name)

    def _save_data(self, close=False):
        if self._data is not None:
            if close:
                logger.debug("Closing module data for module %s", self._name)
                self._data.close()
                self._data = None
            else:
                logger.debug("Syncing module data for module %s", self._name)
                self._data.sync()

    def _load_data(self):
        return self.jeev._get_module_data(self)

    def _clean_g(self):
        if self._g:
            self._g.__dict__.clear()
            self._g = None

    @property
    def name(self):
        return self._name

    @property
    def data(self):
        """
            Persistent data store. Is really just a convenience accessor to a shelve.
        """
        if self._data is None:
            self._data = self._load_data()

        return self._data

    @property
    def g(self):
        """
            Module "globals", useful as a temporary namespace, put whatever you want here, objects, resources,
            descriptors. G will be cleared when the module is unloaded. If you want to persist data, use `module.data`.
        """
        if self._g is None:
            self._g = G()

        return self._g

    def loaded(self, f):
        """
            Register a function to be called when the module is loaded.
        """
        self._loaded_callbacks.append(f)

    def unload(self, f):
        """
            Register a function to be called before the module is unloaded.
        """

        self._unload_callbacks.append(f)
        return f

    def command(self, command, priority=0):
        """
            Register a command handler.
        """

        def bind_command(f):
            bisect.insort(self._commands[command], (priority, f))
            return f

        return bind_command

    def match(self, regex, flags=0, priority=0):
        """
            Decorator that registers a function that will be called when Jeev sees a message that matches regex.
        """
        regex = re.compile(regex, flags)

        def bind_matcher(f):
            bisect.insort(self._regex_listeners, (priority, regex, False, f))
            return f

        return bind_matcher

    def hear(self, regex, priority=0):
        """
            Same as match, except case insensitive matching.
        """
        return self.match(regex, re.I, priority)

    def respond(self, regex, flags=re.I, priority=0):
        """
            Decorator that registers a function that will be called when any message directed at Jeev matches the regex.
        """
        regex = re.compile(regex, flags)

        def bind_matcher(f):
            bisect.insort(self._regex_listeners, (priority, regex, True, f))
            return f

        return bind_matcher

    def listen(self, priority=0):
        """
            Decorator that registers a function that will be called any time Jeev sees a message.
        """

        def bind_listener(f):
            bisect.insort(self._message_listeners, (priority, f))
            return f

        return bind_listener

    def async(self, sync_ret_val=None, timeout=0):
        """
            Decorator that will call the wrapped function inside a greenlet, and do some book-keeping to make
            sure the greenlet is killed when the module is unloaded.
        """

        def wrapper(o_fn):
            if timeout:
                f = functools.partial(gevent.with_timeout, timeout, o_fn, timeout_value=sync_ret_val)

            else:
                f = o_fn

            @functools.wraps(o_fn)
            def wrapped(*args, **kwargs):
                g = gevent.Greenlet(f, *args, **kwargs)
                g.link_exception(self._on_error)
                g.link(lambda v: self._running_greenlets.discard(g))
                self._running_greenlets.add(g)
                g.start()
                return sync_ret_val

            return wrapped

        return wrapper

    def spawn(self, f, *args, **kwargs):
        """
            Spawns a greenlet and does some book-keeping to make sure the greenlet is killed when the module is
            unloaded.
        """
        g = gevent.Greenlet(f, *args, **kwargs)
        g.link_exception(self._on_error)
        g.link(lambda v: self._running_greenlets.discard(g))
        self._running_greenlets.add(g)
        g.start()
        return g

    def spawn_after(self, delay, f, *args, **kwargs):
        """
            Spawns a greenlet that will start after delay seconds. Otherwise, same as Module.spawn
        """
        g = gevent.Greenlet(f, *args, **kwargs)
        g.link_exception(self._on_error)
        g.link(lambda v: self._running_greenlets.discard(g))
        self._running_greenlets.add(g)
        g.start_later(delay)
        return g

    def periodic(self, interval, f, *args, **kwargs):
        """
            Creates a Periodic that can be used to schedule the calling of the provided function
            at a regular interval. The periodic will be automatically unscheduled when the module
            is unloaded.
        """
        return ModulePeriodic(self, interval, f, *args, **kwargs)

    @property
    def is_web(self):
        """
            Returns True if the module has a web application bound to it.
        """
        return self._app is not None

    @property
    def app(self):
        """
            Initializes or returns the wsgi handler for this module.
            Will call module._make_app if the handler hasn't been created yet.
        """
        if self._app is None:
            self._app = self._make_app()

        return self._app

    @app.setter
    def app(self, value):
        """
            Sets the underlying wsgi handler for the module. Won't allow it to be set twice.
        """
        if self._app is not None:
            raise AttributeError("Module.app has already been set.")

        self._app = value

    def set_wsgi_handler(self, handler):
        """
            Use this to set the wsgi handler for the module (can be used as a decorator):

            @module.set_wsgi_handler
            def handle(environ, start_response):
                start_response('200 OK', [])
                return ['Hello World!']
        """
        self.app = handler

    def send_message(self, channel, message):
        """
            Convenience function to send a message to a channel.
        """
        self.jeev.send_message(channel, message)