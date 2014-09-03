import UserDict
from gevent.lock import Semaphore
from ..utils.importing import import_dotted_path
try:
    from cStringIO import StringIO

except ImportError:
    from StringIO import StringIO

try:
    from cPickle import Unpickler, Pickler

except ImportError:
    from pickle import Unpickler, Pickler

try:
    StrictRedis = import_dotted_path('redis.StrictRedis')

except ImportError:
    raise ImportError("redis-py is not installed. Install it using `pip install redis` "
                      "(see https://github.com/andymccurdy/redis-py for more details)")


class RedisStorage(object):
    _redis_opt_keys = 'host', 'port', 'db', 'password', 'socket_timeout', 'socket_connect_timeout', 'socket_keepalive',\
                      'socket_keepalive_options', 'connection_pool', 'unix_socket_path', 'encoding', 'encoding_errors',\
                      'errors', 'decode_responses', 'retry_on_timeout', 'ssl', 'ssl_keyfile', 'ssl_certfile', \
                      'ssl_cert_reqs', 'ssl_ca_certs'

    _redis_int_opts = 'port', 'db', 'socket_timeout',
    _redis_float_opts = 'socket_timeout',
    _redis_bool_opts = 'decode_responses', 'ssl', 'retry_on_timeout'

    def __init__(self, jeev, opts):
        self._jeev = jeev
        self._opts = opts
        self._redis = None
        self._prefix = opts.get('redis_key_prefix', '')

    def _get_redis_kwargs(self):
        kwargs = {}
        for key in self._redis_opt_keys:
            opt_key = 'redis_%s' % key
            if opt_key in self._opts:
                kwargs[key] = self._opts[opt_key]

        for key in self._redis_int_opts:
            if key in kwargs:
                kwargs[key] = int(kwargs[key])

        for key in self._redis_float_opts:
            if key in kwargs:
                kwargs[key] = float(kwargs[key])

        return kwargs

    def _get_redis(self):
        if 'redis_url' in self._opts:
            return StrictRedis.from_url(self._opts['redis_url'])

        return StrictRedis(**self._get_redis_kwargs())

    def _get_hash_key(self, module_name):
        return '%s%s' % (self._prefix, module_name)

    @property
    def redis(self):
        if self._redis is None:
            raise RuntimeError("Attempting to access RedisStorage.redis from a RedisStorage that has not been started.")

        return self._redis

    def start(self):
        if self._redis is None:
            self._redis = self._get_redis()

    def stop(self):
        if self._redis:
            self._redis.connection_pool.disconnect()
            self._redis = None

    def get_data_for_module_name(self, module_name):
        return RedisDict(self, self._get_hash_key(module_name))

storage = RedisStorage


class RedisDict(UserDict.DictMixin):
    def __init__(self, storage, hash_key):
        self._storage = storage
        self._hash_key = hash_key
        self._protocol = 0
        self._cache = {}
        self._cache_write_lock = Semaphore()

    def keys(self):
        return self._storage.redis.hkeys(self._hash_key)

    def __len__(self):
        return self._storage.redis.hlen(self._hash_key)

    def has_key(self, key):
        return key in self

    def __contains__(self, key):
        if key in self._cache:
            return True

        return self._storage.redis.hexists(self._hash_key, key)

    def get(self, key, default=None):
        if key in self:
            return self[key]

        return default

    def __getitem__(self, key):
        try:
            value = self._cache[key]

        except KeyError:

            if key not in self:
                raise KeyError(key)

            f = StringIO(self._storage.redis.hget(self._hash_key, key))
            value = Unpickler(f).load()
            self._cache[key] = value

        return value

    def __setitem__(self, key, value):
        with self._cache_write_lock:
            self._cache[key] = value

        f = StringIO()
        p = Pickler(f, self._protocol)
        p.dump(value)

        self._storage.redis.hset(self._hash_key, key, f.getvalue())

    def __delitem__(self, key):
        self._storage.redis.hdel(self._hash_key, key)

        with self._cache_write_lock:
            self._cache.pop(key, None)

    def close(self):
        self.sync()
        self._storage = None

    def __del__(self):
        self.close()

    def sync(self):
        if not self._cache:
            return

        with self._cache_write_lock, self._storage.redis.pipeline() as pipeline:
            for key, entry in self._cache.iteritems():
                f = StringIO()
                p = Pickler(f, self._protocol)
                p.dump(entry)
                pipeline.hset(self._hash_key, key, f.getvalue())

            pipeline.execute()
            self._cache.clear()