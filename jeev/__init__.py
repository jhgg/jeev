version = '0.1.0-dev'

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