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
        self.stdout.write(">>> Jeev Console Adapater\n")
        self.stdout.write(">>> Switch channel using \c channel_name\n")
        self.stdout.write(">>> Switch channel using \u user_name\n")
        self.stdout.flush()
        
        while True:
            self.stdout.write('[%s@%s] > ' % (self.user, self.channel))
            self.stdout.flush()

            line = self.stdin.readline()
            if not line:
                break

            if line.startswith('\c'):
                self.channel = line[2:].strip().lstrip('#')
                self.stdout.write("Switched channel to #%s\n" % self.channel)
                self.stdout.flush()

            elif line.startswith('\u'):
                self.user = line[2:].strip()
                self.stdout.write("Switched user %s\n" % self.user)
                self.stdout.flush()

            else:
                message = Message({}, self.channel, self.user, line.strip())
                self.jeev.handle_message(message)

    def start(self):
        self.stdin = FileObject(sys.stdin)
        self.stdout = FileObject(sys.stdout)
        self.reader.start()

    def stop(self):
        self.reader.stop()

    def join(self):
        self.reader.join()

    def send_message(self, channel, message):
        self.stdout.write('\r< [#%s] %s\n' % (channel, message))
        self.stdout.write('[%s@%s] > ' % (self.user, self.channel))
        self.stdout.flush()

    def send_messages(self, channel, *messages):
        for message in messages:
            self.send_message(channel, message)

adapter = ConsoleAdapter