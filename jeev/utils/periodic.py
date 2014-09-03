from gevent import sleep, Greenlet, spawn_raw


class Periodic(object):
    def __init__(self, interval, f, *args, **kwargs):
        self.interval = interval
        self.f = f
        self.args = args
        self.kwargs = kwargs
        self._greenlet = None

    def _run(self):
        while True:
            spawn_raw(self.f, *self.args, **self.kwargs)
            sleep(self.interval)

    def _discard_greenlet(self, val):
        self._greenlet = None

    @property
    def started(self):
        return bool(self._greenlet)

    def start(self, right_away=True):
        if self._greenlet:
            raise RuntimeError("Periodic already started.")

        self._greenlet = Greenlet(self._run)
        self._greenlet.link(self._discard_greenlet)
        
        if right_away:
            self._greenlet.start()
        else:
            self._greenlet.start_later(self.interval)

    def stop(self, block=True, timeout=None):
        if not self._greenlet:
            raise RuntimeError("Periodic is not started")

        self._greenlet.kill(block=block, timeout=timeout)
        self._greenlet = None

    def __repr__(self):
        return "<Periodic[%.2f seconds, %s] %r(*%r, **%r)>" % (self.interval, 'running' if self.started else 'stopped',
                                                               self.f, self.args, self.kwargs)


class ModulePeriodic(Periodic):
    def __init__(self, module, *args, **kwargs):
        self.module = module
        super(ModulePeriodic, self).__init__(*args, **kwargs)

    def _discard_greenlet(self, val):
        self.module._running_greenlets.discard(self._greenlet)
        super(ModulePeriodic, self)._discard_greenlet(val)

    def start(self, right_away=True):
        super(ModulePeriodic, self).start(right_away)
        self.module._running_greenlets.add(self._greenlet)
