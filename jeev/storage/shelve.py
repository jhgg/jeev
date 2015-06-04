import UserDict
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
        return UnicodeShelveWrapper(shelve_open(os.path.join(self._module_data_path, module_name), writeback=True))

    def start(self):
        if not os.path.exists(self._module_data_path):
            os.makedirs(self._module_data_path)

    def stop(self):
        pass


class UnicodeShelveWrapper(UserDict.DictMixin):
    def __init__(self, shelf):
        self.shelf = shelf

    def keys(self):
        return [d.encode('utf8') for d in self.shelf.keys()]

    def __len__(self):
        return len(self.shelf)

    def has_key(self, key):
        return key.encode('utf8') in self.shelf

    def __contains__(self, key):
        return key.encode('utf8') in self.shelf

    def get(self, key, default=None):
        if key.encode('utf8') in self.shelf:
            return self[key]

        return default

    def __getitem__(self, key):
        return self.shelf[key.encode('utf8')]

    def __setitem__(self, key, value):
        self.shelf[key.encode('utf8')] = value

    def __delitem__(self, key):
        del self.shelf[key.encode('utf8')]

storage = ShelveStore