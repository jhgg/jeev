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


# Below is an example showing sharing a resource (in this case "store" between
# The web handler and the chat responder.
store = {}


@module.app.route('/<key>')
def get_key(key):
    if key not in store:
        abort(404, 'A value for key: %s was not found' % key)

    return Response(store[key], mimetype='text/plain')


@module.respond('set ([^ ]+) to (.*)$')
def do_setter(message, key, value):
    store[key] = value
    message.reply_to_user("Done. I set %s to %s" % (key, value))