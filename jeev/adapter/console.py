from gevent import Greenlet
from gevent.fileobject import FileObject
import sys
from ..message import Message


class ConsoleAdapter(object):
    def __init__(self, jeev, opts):
        self._jeev = jeev
        self._opts = opts
        self._stdin = None
        self._reader = Greenlet(self._read_stdin)
        self._channel = opts.get('consoleChannel', 'console')
        self._user = opts.get('consoleUser', 'user')

    def _read_stdin(self):
        self.stdout.write(">>> Jeev Console Adapater\n")
        self.stdout.write(">>> Switch channel using \c channel_name\n")
        self.stdout.write(">>> Switch channel using \u user_name\n")
        self.stdout.flush()
        
        while True:
            self.stdout.write('[%s@%s] > ' % (self._user, self._channel))
            self.stdout.flush()

            line = self._stdin.readline()
            if not line:
                break

            if line.startswith('\c'):
                self._channel = line[2:].strip().lstrip('#')
                self.stdout.write("Switched channel to #%s\n" % self._channel)
                self.stdout.flush()

            elif line.startswith('\u'):
                self._user = line[2:].strip()
                self.stdout.write("Switched user %s\n" % self._user)
                self.stdout.flush()

            else:
                message = Message({}, self._channel, self._user, line.strip())
                self._jeev._handle_message(message)

    def start(self):
        self._stdin = FileObject(sys.stdin)
        self.stdout = FileObject(sys.stdout)
        self._reader.start()

    def stop(self):
        self._reader.stop()

    def join(self):
        self._reader.join()

    def send_message(self, channel, message):
        self.stdout.write('\r< [#%s] %s\n' % (channel, message))
        self.stdout.write('[%s@%s] > ' % (self._user, self._channel))
        self.stdout.flush()

    def send_messages(self, channel, *messages):
        for message in messages:
            self.send_message(channel, message)

adapter = ConsoleAdapter