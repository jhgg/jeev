from collections import defaultdict
import bisect
from importlib import import_module
import re
import gevent


class Modules(object):
    def __init__(self, jeev):
        self.jeev = jeev
        self.module_list = []
        self.module_dict = {}

    def load(self):
        for module, opts in getattr(self.jeev.config, 'modules', {}).iteritems():
            if module in self.module_dict:
                raise RuntimeError("Trying to load duplicate module!")

            module_obj = self.import_module(module)

            if hasattr(module_obj, 'export'):
                module_inst = Module()
                module_obj.export(module_inst)
                module_obj = module_inst

            elif hasattr(module_obj, 'module'):
                module_obj = module_obj.module

            if isinstance(module_obj, Module):
                module_obj._register(self, opts)
                self.module_list.append(module_obj)
                self.module_dict[module] = module_obj

            else:
                print "Could not load", module

    def import_module(self, name):
        return import_module('modules.%s' % name)

    def handle_message(self, message):
        for module in self.module_list:
            module.handle_message(message)


class Module(object):
    STOP = object()

    def __init__(self, author=None, description=None):
        self.author = author
        self.description = description
        self.message_listeners = []
        self.commands = defaultdict(list)
        self.regex_listeners = []
        self.respond_regex_listeners = []

    def _register(self, modules, opts):
        self.jeev = modules.jeev
        self.opts = opts
        self.register()

    def register(self):
        pass

    def command(self, command, priority=0):
        def bind_command(f):
            bisect.insort(self.commands[command], (priority, f))

        return bind_command

    def match(self, regex, flags=0, priority=0):
        regex = re.compile(regex, flags)

        def bind_matcher(f):
            bisect.insort(self.regex_listeners, (priority, regex, False, f))

        return bind_matcher

    def hear(self, regex, flags=re.I, priority=0):
        return self.match(regex, flags, priority)

    def respond(self, regex, flags=re.I, priority=0):
        regex = re.compile(regex, flags)

        def bind_matcher(f):
            bisect.insort(self.regex_listeners, (priority, regex, True, f))

        return bind_matcher

    def async(self, sync_ret_val=None):
        def wrapper(f):
            def wrapped(*args, **kwargs):
                g = gevent.Greenlet(f, *args, **kwargs)
                g.link_exception(self.on_error)
                g.start_later(0)
                return sync_ret_val

            return wrapped

        return wrapper

    def call_f(self, f, *args, **kwargs):
        try:
            print "calling", f, "with", args, kwargs
            return f(*args, **kwargs)
        except Exception, e:
            self.on_error(e)

    def handle_message(self, message):
        if message.message_parts:

            command = message.message_parts[0]
            if command in self.commands:
                for _, f in self.commands[command]:
                    if self.call_f(f, message) is self.STOP:
                        return

            for _, regex, responder, f in self.regex_listeners:
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
        raise e