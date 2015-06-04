import module

from gevent import Timeout, sleep


@module.hear('countdown for (\d+) seconds')
@module.async()
def sleep_for(message, seconds):
    m = message.reply("Counting down from 0 -> %s" % seconds)
    for i in xrange(1, int(seconds) + 1):
        sleep(1)
        m.update("Counting down from %s -> %s" % (i, seconds))

    m.update('=== COUNTDOWN DONE ===')