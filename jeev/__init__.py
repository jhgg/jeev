version = '0.2.0-dev'

__author__ = 'mac'


def run(config):
    import atexit
    import sys

    # Reset sys.modules so that g-event can re-monkeypatch.
    # This is needed because distribute's pkg_resources imports urllib & co, before we can properly monkey patch it. ;(
    modules_to_reset = {'urllib', 'socket', '_ssl', 'ssl', 'select', 'thread',
                        'threading', 'time', 'os', 'subprocess'}
    for k in sys.modules.keys():
        if k.startswith('jeev.') or k in modules_to_reset:
            del sys.modules[k]

    from gevent.monkey import patch_all

    patch_all()

    from .jeev import Jeev
    import logging

    logging.basicConfig(**getattr(config, 'logging', {}))
    j = Jeev(config)

    try:
        j.run()
        atexit.register(j.stop)
        j.join()

    except KeyboardInterrupt:
        print "Got ^C. Stopping!"
        pass


def _iter_modules(config):
    from .jeev import Jeev

    j = Jeev(config)

    for module_name, opts in j.modules.iter_module_names_and_opts():
        try:
            module_instance = j.modules.load(module_name, opts, log_error=False, register=False)

        except ImportError:
            print 'ERROR: Module %s not found.' % module_name
            continue

        yield module_name, module_instance, j


def chkconfig(config):
    from .module import Module

    for module_name, module_instance, j in _iter_modules(config):
        try:
            module_instance._register(j.modules)

        except Module.ConfigError as e:

            print "ERROR: Could not load module %s. Some options failed to validate:" % module_name
            if hasattr(e, 'error_dict'):
                for k, v in e.error_dict.iteritems():
                    print('\t%s: %s' % (k, ', '.join(v)))
                    if k in module_instance.opts._opt_definitions:
                        print('\t * description: %s' % module_instance.opts._opt_definitions[k].description)

                    print('\t * environ key: %s' % module_instance.opts.environ_key(k))
            pass

        else:
            print '%s OK' % module_name


def modopts(config):
    from .module import Module

    for module_name, module_instance, j in _iter_modules(config):
        opt_definitions = module_instance.opts._opt_definitions
        if not opt_definitions:
            print 'Module %s has no options.' % module_name
            continue

        print 'Module %s:' % module_name
        for opt in opt_definitions.values():
            print '  * %s:' % opt.name
            print '     - description: %s' % opt.description

            if opt.has_default:
                print '     - default:     %s' % opt.default

            print '     - environ key: %s' % module_instance.opts.environ_key(opt.name)

            print