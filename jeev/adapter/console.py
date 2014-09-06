from gevent import Greenlet
from gevent.fileobject import FileObject
import sys
from ..message import Message


class ConsoleAdapter(object):
    """
        This adapter will run Jeev in console mode, listening to stdin for messages,
        and writing outgoing messages to stdout.
    """
    def __init__(self, jeev, opts):
        self._jeev = jeev
        self._opts = opts
        self._stdin = None
        self._stdout = None
        self._reader = None
        self._channel = opts.get('console_channel', 'console')
        self._user = opts.get('console_user', 'user')

    def _read_stdin(self):
        self._stdout.write(">>> Jeev Console Adapater, running jeev v%s\n" % self._jeev.version)
        self._stdout.write(">>> Switch channel using \c channel_name\n")
        self._stdout.write(">>> Switch user using \u user_name\n")
        self._stdout.write(">>> Jeev will respond to the user name %s\n" % self._jeev.name)
        self._stdout.flush()
        
        while True:
            self._stdout.write('[%s@%s] > ' % (self._user, self._channel))
            self._stdout.flush()

            line = self._stdin.readline()
            if not line:
                break

            if line.startswith('\c'):
                self._channel = line[2:].strip().lstrip('#')
                self._stdout.write("Switched channel to #%s\n" % self._channel)
                self._stdout.flush()

            elif line.startswith('\u'):
                self._user = line[2:].strip()
                self._stdout.write("Switched user %s\n" % self._user)
                self._stdout.flush()

            else:
                message = Message({}, self._channel, self._user, line.strip())
                self._jeev._handle_message(message)

    def start(self):
        self._reader = Greenlet(self._read_stdin)
        self._stdin = FileObject(sys.stdin)
        self._stdout = FileObject(sys.stdout)
        self._reader.start()

    def stop(self):
        self._reader.kill()
        self._reader = None

    def send_message(self, channel, message):
        self._stdout.write('\r< [#%s] %s\n' % (channel, message))
        self._stdout.write('[%s@%s] > ' % (self._user, self._channel))
        self._stdout.flush()

    def send_messages(self, channel, *messages):
        for message in messages:
            self.send_message(channel, message)

adapter = ConsoleAdapter