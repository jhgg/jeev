from .jeev import Jeev
from gevent.monkey import patch_all
patch_all()

__author__ = 'mac'


def run(config):
    j = Jeev(config)
    j.run()
