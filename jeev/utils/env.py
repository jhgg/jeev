import os


class EnvFallbackDict(object):
    """
        This dict will first search for a key inside of it, then search ENVIRON for it if the key isn't found.

        When constructed with a module_name of "test"
        Searching for key "foo" will search for "foo" inside of the dict, and if it's not there, it will then
        look in "JEEV_TEST_FOO" and return that value. If it's not inside the dict, or environ, it will raise
        KeyError like normal.

        This dict is read only, and will only return strings.
    """
    __slots__ = ['_module_name', '_data']

    def __init__(self, module_name, dict, **kwargs):
        self._module_name = module_name

        if self._module_name:
            self._module_name = self.module_name.replace('.', '_')

        self._data = {}

        if dict is not None:
            self._data.update(dict)

        if len(kwargs):
            self._data.update(kwargs)

    @property
    def module_name(self):
        return self._module_name

    @module_name.setter
    def module_name(self, value):
        self._module_name = value.replace('.', '_')

    def environ_key(self, key):
        if not self._module_name:
            return ('jeev_%s' % key).upper()

        return ('jeev_%s_%s' % (self._module_name, key)).upper()

    def __contains__(self, item):
        if item in self._data:
            return True

        if self.environ_key(item) in os.environ:
            return True

        return False

    def __repr__(self):
        return repr(self._data)

    def __cmp__(self, dict):
        if isinstance(dict, EnvFallbackDict):
            return cmp(self._data, dict._data)
        else:
            return cmp(self._data, dict)

    __hash__ = None  # Avoid Py3k warning

    def __len__(self):
        return len(self._data)

    def __getitem__(self, key):
        if key in self._data:
            return self.cast_val(key, self._data[key])

        env_key = self.environ_key(key)
        if env_key in os.environ:
            return self.cast_val(key, os.environ[env_key])

        raise KeyError(key)

    def copy(self):
        if self.__class__ is EnvFallbackDict:
            return EnvFallbackDict(self.module_name, self._data.copy())

        import copy

        data = self._data
        try:
            self._data = {}
            c = copy.copy(self)
        finally:
            self._data = data

        c.update(self)
        return c

    def keys(self):
        return self._data.keys()

    def items(self):
        return self._data.items()

    def iteritems(self):
        return self._data.iteritems()

    def iterkeys(self):
        return self._data.iterkeys()

    def itervalues(self):
        return self._data.itervalues()

    def values(self):
        return self._data.values()

    def has_key(self, key):
        return key in self._data

    def get(self, key, failobj=None):
        if key not in self:
            return failobj

        return self[key]

    def cast_val(self, key, val):
        if not isinstance(val, basestring):
            val = str(val)

        return val