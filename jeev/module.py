from collections import defaultdict
import bisect
import functools
import logging
import re
import gevent
import sys

logger = logging.getLogger('jeev.module')


class Modules(object):
    def __init__(self, jeev):
        self.jeev = jeev
        self.module_list = []
        self.module_dict = {}

    def load_all(self):
        for module_name, opts in getattr(self.jeev.config, 'modules', {}).iteritems():
            self.load(module_name, opts)

    def load(self, module_name, opts):
        if module_name in self.module_dict:
            raise RuntimeError("Trying to load duplicate module!")

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
            self.module_list.append(module_instance)
            self.module_dict[module_name] = module_instance

            logger.info("Lodaed module %s", module_name)

        except Exception, e:
            logger.exception("Could not load module %s", module_name)
            raise e

    def unload(self, module_name):
        module = self.module_dict[module_name]
        module._unload()
        del self.module_dict[module_name]
        self.module_list.remove(module)

    def _import_module(self, name, module_instance):
        name = 'modules.%s' % name
        try:
            sys.modules['module'] = module_instance
            __import__(name)
            return sys.modules[name]

        finally:
            sys.modules.pop('module')
            sys.modules.pop(name, None)

    def get_module(self, name, default=None):
        return self.module_dict.get(name, default)

    def handle_message(self, message):
        for module in self.module_list:
            module.handle_message(message)


class Module(object):
    STOP = object()

    def __init__(self, name, author=None, description=None):
        self.name = name
        self.author = author
        self.description = description
        self._commands = defaultdict(list)
        self._message_listeners = []
        self._regex_listeners = []
        self._loaded_callbacks = []
        self._unload_callbacks = []
        self._running_greenlets = set()
        self._app = None
        self.jeev = None
        self.opts = None

    def _unload(self):
        for callback in self._unload_callbacks:
            callback(self)

        self._regex_listeners[:] = []
        self._loaded_callbacks[:] = []
        self._message_listeners[:] = []
        self._commands.clear()
        self._app = None
        self.jeev = None
        self.opts = None

        gevent.killall(list(self._running_greenlets), block=False)
        self._running_greenlets.clear()

    def _register(self, modules, opts):
        self.jeev = modules.jeev
        self.opts = opts
        for f in self._loaded_callbacks:
            f(self)

    @property
    def is_web(self):
        return self._app is not None

    @property
    def app(self):
        if self._app is None:
            self._app = self.make_app()

        return self._app

    def make_app(self):
        import flask
        return flask.Flask('modules.%s' % self.name)

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

    def command(self, command, priority=0):
        """
            Register a command handler.
        """
        def bind_command(f):
            bisect.insort(self._commands[command], (priority, f))

        return bind_command

    def match(self, regex, flags=0, priority=0):
        regex = re.compile(regex, flags)

        def bind_matcher(f):
            bisect.insort(self._regex_listeners, (priority, regex, False, f))

        return bind_matcher

    def hear(self, regex, flags=re.I, priority=0):
        return self.match(regex, flags, priority)

    def respond(self, regex, flags=re.I, priority=0):
        regex = re.compile(regex, flags)

        def bind_matcher(f):
            bisect.insort(self._regex_listeners, (priority, regex, True, f))

        return bind_matcher

    def listen(self, priority=0):
        def bind_listener(f):
            bisect.insort(self._message_listeners, (priority, f))

        return bind_listener

    def async(self, sync_ret_val=None, timeout=0):
        def wrapper(o_fn):
            if timeout:
                f = functools.partial(gevent.with_timeout, timeout, o_fn, timeout_value=sync_ret_val)

            else:
                f = o_fn

            @functools.wraps(o_fn)
            def wrapped(*args, **kwargs):
                g = gevent.Greenlet(f, *args, **kwargs)
                g.link_exception(self.on_error)
                g.link(lambda v: self._running_greenlets.discard(g))
                self._running_greenlets.add(g)
                g.start_later(0)
                return sync_ret_val

            return wrapped

        return wrapper

    def spawn(self, f, *args, **kwargs):
        g = gevent.Greenlet(f, *args, **kwargs)
        g.link_exception(self.on_error)
        g.link(lambda v: self._running_greenlets.discard(g))
        self._running_greenlets.add(g)
        g.start_later(0)
        return g

    def spawn_after(self, delay, f, *args, **kwargs):
        g = gevent.Greenlet(f, *args, **kwargs)
        g.link_exception(self.on_error)
        g.link(lambda v: self._running_greenlets.discard(g))
        self._running_greenlets.add(g)
        g.start_later(delay)
        return g

    def call_f(self, f, *args, **kwargs):
        try:
            logger.debug("calling %r with %r %r)", f, args, kwargs)
            return f(*args, **kwargs)
        except Exception, e:
            self.on_error(e)

    def handle_message(self, message):
        for _, f in self._message_listeners:
            if self.call_f(f, message) is self.STOP:
                return

        if message.message_parts:

            command = message.message_parts[0]
            if command in self._commands:
                for _, f in self._commands[command]:
                    if self.call_f(f, message) is self.STOP:
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

                    if self.call_f(f, message, *args, **kwargs) is self.STOP:
                        return

    def on_error(self, e):
        if isinstance(e, gevent.Greenlet):
            e = e.exception

        self.jeev.on_module_error(self, e)
        logger.exception("Exception raised %r", e)