from collections import defaultdict
import bisect
import functools
import logging
import re
import gevent
import sys
from .utils.importing import import_first_matching_module, import_dotted_path
from .utils.periodic import ModulePeriodic
from .utils.g import G
from .utils.env import EnvFallbackDict

logger = logging.getLogger('jeev.module')
_sentinel = object()


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
        def remove_from_sys_modules(module_name):
            for k in sys.modules.keys():
                if k.startswith(module_name):
                    del sys.modules[k]

        try:
            sys.modules['module'] = module_instance
            return import_first_matching_module(mod_name=name,
                                                matches=['modules.%s', 'jeev_modules.%s'],
                                                try_mod_name=('.' in name),
                                                pre_import_hook=module_instance._set_module_name,
                                                post_import_hook=remove_from_sys_modules)

        finally:
            sys.modules.pop('module', None)

    def load_all(self, modules=None):
        """
            Loads all the modules defined in Jeev's configuration
        """
        for module_name, opts in self.iter_module_names_and_opts(modules):
            self.load(module_name, opts)

        for module in self._module_list:
            module._loaded()

    def iter_module_names_and_opts(self, modules=None):
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
            yield module_name, opts

    def load(self, module_name, opts, log_error=True, register=True):
        """
            Load a module by name.
        """
        if module_name in self._module_dict:
            raise RuntimeError("Trying to load duplicate module!")

        if module_name in self._reserved_module_names:
            raise RuntimeError("Cannot load reserved module named %s" % module_name)

        logger.debug("Loading module %s", module_name)
        module_instance = Module(module_name, opts)

        try:
            imported_module = self._import_module(module_name, module_instance)

            module_instance.author = getattr(
                imported_module, 'author', getattr(imported_module, '__author__', None))

            module_instance.description = getattr(
                imported_module, 'description', getattr(imported_module, '__doc__', None))

            logger.debug("Registering module %s", module_name)
            if register:
                module_instance._register(self)
                self._module_list.append(module_instance)
                self._module_dict[module_name] = module_instance

            logger.info("Loaded module %s", module_name)

        except Module.ConfigError, e:
            if log_error:
                logger.error("Could not load module %s. Some options failed to validate:", module_name)
                if hasattr(e, 'error_dict'):
                    for k, v in e.error_dict.iteritems():
                        logger.error('\t%s: %s' % (k, ', '.join(v)))
                        if k in module_instance.opts._opt_definitions:
                            logger.error('\t * description: %s' % module_instance.opts._opt_definitions[k].description)

                        logger.error('\t * environ key: %s' % module_instance.opts.environ_key(k))

            raise e
        except Exception, e:
            if log_error:
                logger.exception("Could not load module %s", module_name)

            raise e

        return module_instance

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
    __slots__ = ['jeev', 'opts', '_name', 'author', 'description', '_module_name',
                 '_commands', '_message_listeners', '_regex_listeners', '_loaded_callbacks', '_unload_callbacks',
                 '_running_greenlets', '_data', '_app', '_g', '_opt_definitions']

    def __init__(self, name, opts, author=None, description=None):
        self.author = author
        self.description = description
        self.jeev = None
        self.opts = OptFallbackDict(name, opts)

        self._name = name
        self._module_name = name
        self._g = None
        self._commands = defaultdict(list)
        self._message_listeners = []
        self._regex_listeners = []
        self._loaded_callbacks = []
        self._unload_callbacks = []
        self._running_greenlets = set()
        self._data = None
        self._app = None
        self._opt_definitions = None

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

    def _register(self, modules):
        self.jeev = modules.jeev
        self._validate_opts()

    def _loaded(self):
        for callback in self._loaded_callbacks:
            self._call_function(callback)

    def _validate_opts(self):
        error_dict = defaultdict(list)

        for definition in self.opts._opt_definitions.itervalues():
            if definition.default is _sentinel and definition.name not in self.opts:
                error_dict[definition.name].append("This option is required.")

        defunct_keys = error_dict.keys()

        for validator in self.opts._opt_validators:
            if validator.name in defunct_keys:
                continue

            try:
                validator.clean(self.opts)
            except Module.ConfigError as e:
                error_dict[e.variable_name].append(e.error_message)

        if error_dict:
            raise Module.ConfigError(error_dict)

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
        return import_dotted_path('flask.Flask')(self.module_name)

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

    def _set_module_name(self, module_name):
        self._module_name = module_name

    @property
    def name(self):
        """
            The name of the module set in the config to be loaded.
        """
        return self._name

    @property
    def module_name(self):
        """
            The full module name (import path)

            >>> print self.name
            sample
            >>> print self.module_name
            modules.sample
        """
        return self._module_name

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

    def opt(self, *args, **kwargs):
        """
        Registers an option validator that allows you to check for a given option to be present, and if it isn't,
        tell Jeev to automatically throw an exception when the module is trying to be loaded, providing the user
        with the required option name and a description.

        Optionally, you can set a casting function, to convert the option from its string form to something else,
        or even, a default value, if it does not exist.
        """
        self.opts._register_opt(Opt(*args, **kwargs))

    def opt_validator(self, *names):
        """
        Registers a validator function that will be called with a given opt's value. The function must either raise
        a Module.ConfigError, or return a value that the opt should be set to. This lets you override (or clean)
        any option.
        """

        def register_validator(callback):
            for name in names:
                self.opts._register_validator(OptValidator(name, callback))

            return callback

        return register_validator

    def loaded(self, f):
        """
            Register a function to be called when the module is loaded.
        """
        self._loaded_callbacks.append(f)

    def unloaded(self, f):
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

    class ConfigError(Exception):
        module_instance = None

        def __init__(self, variable_name, error_message=None):
            if isinstance(variable_name, dict):
                self.error_dict = variable_name

            else:
                self.variable_name = variable_name
                self.error_message = error_message

        def __repr__(self):
            if hasattr(self, 'error_dict'):
                return '<ConfigError: %r>' % self.error_dict

            return '<ConfigError: %s, %s>' % (self.variable_name, self.error_message)


class Opt(object):
    """
        Stores the metadata for a given option.
    """
    __slots__ = ['name', 'description', 'cast', 'default']

    def __init__(self, name, description, cast=None, default=_sentinel):
        self.name = name
        self.description = description
        self.cast = cast
        self.default = default

    @property
    def has_default(self):
        return self.default is not _sentinel


class OptValidator(object):
    """
        Stores a validator for a given option.
    """
    __slots__ = ['name', 'callback']

    def __init__(self, name, callback):
        self.name = name
        self.callback = callback

    def clean(self, opt_fallback_dict):
        value = opt_fallback_dict[self.name]
        try:
            new_value = self.callback(value)

            # If the value changed, we'll override it in the opt_fallback_dict's private _data.
            if new_value is not None and value != new_value:
                opt_fallback_dict._opt_overrides[self.name] = new_value

        except Module.ConfigError as e:
            if e.error_message is None and e.variable_name:
                e.error_message = e.variable_name
                e.variable_name = self.name

            raise e


class OptFallbackDict(EnvFallbackDict):
    """
        An addition to EnvFallbackDict that supports definitions, validators and overrides.
    """

    def __init__(self, *args, **kwargs):
        # The Opt definitions.
        self._opt_definitions = {}
        # A list of OptValidators to call when the module is overriden.
        self._opt_validators = []
        # A dict containing opt overrides that will be returned without being cast (set by the opt validators)
        self._opt_overrides = {}

        super(OptFallbackDict, self).__init__(*args, **kwargs)

    def __getitem__(self, key):
        # See if the key is overridden first. If it is, we take no further action, as it will be returned in it's
        # original, uncasted form.
        if key in self._opt_overrides:
            return self._opt_overrides[key]

        # Try to fetch it from _data, and the environ.
        try:
            return super(OptFallbackDict, self).__getitem__(key)

        except KeyError:
            # If it didn't exist, see if a definition has a default for the given key.
            if key in self._opt_definitions:
                opt = self._opt_definitions[key]
                if opt.has_default:
                    return self.cast_val(key, opt.default)

        # Not anywhere, now we can raise KeyError like usual.
        raise KeyError(key)

    def __contains__(self, item):
        # Again, see if the item was somehow overridden.
        if item in self._opt_overrides:
            return True

        # Check EnvFallbackDict.
        if super(OptFallbackDict, self).__contains__(item):
            return True

        # See if it has a default.
        if item in self._opt_definitions:
            default = self._opt_definitions[item].default
            if default is not _sentinel:
                return True

        return False

    def cast_val(self, key, val):
        # See if the opt definitions specifcy a custom casting function.
        if key in self._opt_definitions:
            cast = self._opt_definitions[key].cast
            if cast:
                return cast(val)

        # Otherwise use the default cast to string implementation.
        return super(OptFallbackDict, self).cast_val(key, val)

    def _register_opt(self, opt):
        self._opt_definitions[opt.name] = opt

    def _unregister_opt(self, opt):
        if isinstance(opt, Opt):
            opt = opt.name

        self._opt_definitions.pop(opt)

    def _register_validator(self, opt_validator):
        self._opt_validators.append(opt_validator)