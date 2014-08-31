from gevent import Greenlet
from gevent.fileobject import FileObject
import sys
from ..message import Message


class ConsoleAdapter(object):
    def __init__(self, jeev, opts):
        self.jeev = jeev
        self.opts = opts
        self.stdin = None
        self.reader = Greenlet(self.read_stdin)
        self.channel = opts.get('consoleChannel', 'console')
        self.user = opts.get('consoleUser', 'user')

    def read_stdin(self):
        sys.stdout.write("[Jeev Console Adapater]\n")
        while True:
            sys.stdout.write('> ')
            sys.stdout.flush()

            line = self.stdin.readline()
            if not line:
                break

            message = Message({}, self.channel, self.user, line.strip())
            self.jeev.handle_message(message)

    def start(self):
        self.stdin = FileObject(sys.stdin)
        self.reader.start()

    def stop(self):
        self.reader.stop()

    def join(self):
        self.reader.join()

    def send_message(self, channel, message):
        sys.stdout.write('\r')
        sys.stdout.write('< [#%s] %s' % (channel, message))
        sys.stdout.write('\n> ')
        sys.stdout.flush()

    def send_messages(self, channel, *messages):
        for message in messages:
            self.send_message(channel, message)

adapter = ConsoleAdapter