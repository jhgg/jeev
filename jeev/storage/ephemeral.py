import UserDict


class EphemeralStorage(object):
    def __init__(self, jeev, opts):
        self._jeev = jeev
        self._opts = opts

    def start(self):
        pass

    def stop(self):
        pass

    def get_data_for_module_name(self, module_name):
        return EphemeralDict()

storage = EphemeralStorage


class EphemeralDict(UserDict):
    def sync(self):
        pass

    def close(self):
        self.data.clear()
        self.data = None