"""
This module is an example of how to use the Jeev WSGI server.

Use this as a basis to build web-hooks and stuff.
"""
import module
from flask import Response, abort

@module.app.route('/')
def index():
    module.send_message('test', 'i got a request')
    return Response('I am the module {m.name}.\n{m.description}'
                    ''.format(m=module), mimetype='text/plain')


# Below shows the sharing of resources between web / chat.
# We use `module.data` to store persistent data that will exist
# between restarts.

@module.hear('opt (.*)$')
def get_opt(message, opt):
    message.reply('%s = %r' % (opt, module.opts.get(opt, "Not Found")))

@module.app.route('/<key>')
def get_key(key):
    if key not in module.data:
        abort(404, 'A value for key: %s was not found' % key)

    return Response(module.data[key], mimetype='text/plain')


@module.respond('set ([^ ]+) to (.*)$')
def do_setter(message, key, value):
    module.data[key] = value
    message.reply_to_user("Done. I set %s to %s" % (key, value))


@module.respond('what is ([^ ]+)')
def do_setter(message, key):
    if key in module.data:
        message.reply_to_user('%s is %s' % (key, module.data[key]))

    else:
        message.reply_to_user("I'm not sure what %s is!" % key)


@module.respond('forget about ([^ ]+)')
def do_setter(message, key):
    if key in module.data:
        del module.data[key]
        message.reply_to_user('Its like %s never existed...' % key)

    else:
        message.reply_to_user("I'm not sure what %s is anyways!" % key)


from gevent import Timeout, sleep

@module.hear('sleep for (\d+) seconds')
@module.async(timeout=5)
def sleep_for(message, seconds):
    try:
        message.reply("Okay, I'm going to try to sleep for %s seconds" % seconds)
        sleep(int(seconds))
    except Timeout:
        message.reply("OOPS! I slept for too long! Oh well :C")