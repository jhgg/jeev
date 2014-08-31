from gevent.monkey import patch_all
patch_all()

from .jeev import Jeev
import logging


__author__ = 'mac'


def run(config):
    logging.basicConfig(**getattr(config, 'logging', {}))

    j = Jeev(config)
    j.run()
    return j
