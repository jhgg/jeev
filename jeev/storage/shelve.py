from ..utils.importing import import_dotted_path
import os

# The solution to importing python's stdlib shelve from inside of a module named shelve :|
shelve_open = import_dotted_path('shelve.open')


class ShelveStore(object):
    def __init__(self, jeev, opts):
        self._jeev = jeev
        self._opts = opts
        self._module_data_path = opts['shelve_data_path']

    def get_data_for_module_name(self, module_name):
        return shelve_open(os.path.join(self._module_data_path, module_name), writeback=True)

    def start(self):
        if not os.path.exists(self._module_data_path):
            os.makedirs(self._module_data_path)

    def stop(self):
        pass



storage = ShelveStore