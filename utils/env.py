from UserDict import UserDict
import os


class EnvFallbackDict(UserDict):
    def __init__(self, data, module_name):
        self.module_name = module_name
        self.data = data

    def environ_key(self, key):
        return ('jeev_%s_%s' % (self.module_name, key)).upper()

    def __missing__(self, key):
        env_key = self.environ_key(key)
        if env_key in os.environ:
            return os.environ[env_key]

        raise KeyError(key)

    def __contains__(self, item):
        if item in self.data:
            return True

        if self.environ_key(item) in os.environ:
            return True

        return False