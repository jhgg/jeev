version = '0.2.0-dev'

__author__ = 'mac'


def run(config):
    import atexit
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


def chkconfig(config):
    from .jeev import Jeev
    from .module import Module

    j = Jeev(config)

    for module_name, opts in j.modules.iter_module_names_and_opts():
        try:
            j.modules.load(module_name, opts, log_error=False)

        except ImportError:
            print 'ERROR: Module %s not found.' % module_name

        except Module.ConfigError as e:
            module_instance = e.module_instance

            print("ERROR: Could not load module %s. Some options failed to validate:" % module_name)
            if hasattr(e, 'error_dict'):
                for k, v in e.error_dict.iteritems():
                    print('\t%s: %s' % (k, ', '.join(v)))
                    if k in module_instance.opts._opt_definitions:
                        print('\t * description: %s' % module_instance.opts._opt_definitions[k].description)

                    print('\t * environ key: %s' % module_instance.opts.environ_key(k))
            pass

        else:
            print '%s OK' % module_name
