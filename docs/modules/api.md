Documentation for the public module API with examples.

## Properties
### `module.name`
Gets the module's name.

### `module.jeev`
The `Jeev` instance that loaded this module.

### `module.opts`
A read only dictionary of options passed to the module (either via the config file, or ENVIRONMENT variables). All
values of this dictionary are strings.

### `module.data`
A persistent data store, that stores data using `SLACK_STORAGE`.

#### Example
```python
# Usually accessed like a `dict`. 
# Keys are persisted to the data store when they are written to:
module.data['foo'] = 'bar'

# Supports all the dict functions too:
print(module.data.keys())
del module.data['foo']
print 'foo' in module.data          # False

# However, when setting mutable objects (aka, dicts or lists as a value) special care has to be taken to make sure
# that they are properly persisted to the data store.

module.data['my_list'] = [1, 2, 3]  # Saved to the database, since you are writing to a value.
module.data['my_list'].append(4)    # Does not save to the database, as my_list is accessed but not set.

print module.data['my_list']        # [1, 2, 3, 4]
module.data.sync()                  # Persists 'my_list' to the data store (note that this function is smart, and won't
                                    # try to re-write everything in modules.data)
```

### `module.g`
A namespace to temporarily store data for the life of the module. Good to store resources, descriptors, or other things
that don't need to persist between restarts of Jeev or reloads of the module.

### Example
```python

module.g.db = MyDatabaseResource()
result = module.g.db.query("SELECT * FROM `bar`")

module.g.counter = 0
module.g.counter += 1
```

## Callback Decorators
### `@module.loaded`
Registers a function that will be called when the module is loaded. You can register more than one function to be 
called. Usually, this is used as a decorator.

#### Example
```python

@module.loaded
def connect_to_some_database():
    module.g.db = MyDatabaseResource()
```

### `@module.unloaded`
Registers a function that will be called when the module is unloaded. You can register more than one function to be
called.

#### Example
```python

@module.unloaded
def disconnect_from_database():
    module.g.db.close() # You don't have to unset this variable, module.g is cleared when the module is unloaded.
```

## Message Handler Decorators

### `@module.listen(priority=0)`
Called whenever Jeev sees a message.

#### Example
```python

@module.listen()
def on_message(message):
    print "Got message from", message.user, ":", message.message
    message.reply_to_user('You said: %s" % message.message)
```

### `@module.command(command, priority=0)`
A handler that gets called if `command` is seen as the first word in a message. This runs faster than `match`, `hear`,
and `respond`, as it uses a dict lookup that is pretty much constant time. 

#### Example
```python
# This will get called whenever anyone says '!ping' in the channel.
@module.command('!ping')
def ping(message):
    module.reply('Pong!')
```

### `@module.match(regex, flags=0, priority=0)`
Registers a function that will be called when a message is seen that matches a specific regex.

#### Example
```python

# Case sensitive match for 'throw me the facts'
# Will get called when a message contains 'throw me the facts' in all lower case.
@module.match('throw me the facts')
def the_facts(message):
    message.reply('just the basics?')
    
# Captures are passed to the handler function as arguments.

@module.match('what is (.*)')
def what_is(message, thing):
    if thing == 'love':
        message.reply('BABY DONT HURT ME!')
    else:
        message.reply('I'm not really sure what %s is' % thing)
        
        
# In addition, named captures work as well.
@module.match('search for (?P<thing>.*) on (?P<engine>google|ddg)')
def what_is(message, engine, thing):
    message.reply('searching for %s on %s' % (thing, engine))    
    
# Or even...
@module.match('search for (?P<thing>.*) on (?P<engine>google|ddg)')
def what_is(message, **kwargs):
    message.reply('searching for %(thing)s on %(engine)s' % kwargs)
    
```

### `@module.hear(regex, priority=0)`
Same as `@module.match(...)` but defaults to a case-insensitive match.


### `@module.respond(regex, flags=re.I, priority=0)`
Same as `@module.hear(...)` but only gets called if the message is addressing the bot (meaning the message starts with 
the bot name "jeev, throw me the facts!")

## Function Decorators
## `@module.async(sync_return_val=None, timeout=0)`
Makes it so that the function is called inside a greenlet. This is useful for functions which make web requests. 
Although, a function that makes a request will never block Jeev, it will prevent the other message handlers from being 
called for a specific message. However, since each incoming message is processed in it's own greenlet, a message handler
that performs code that can be made concurrent with gevent will never delay delay the processing of new messages. Where
this function really is useful is to set a timeout to the processing time of a handler.

#### Example

**Making a web request timeout**
```python

@module.hear('cat ?fact')
@module.async(timeout=5)
def cat_fact(message):
    # If this request takes more than 5 seconds, the greenlet that is running this function will be killed.
    response = requests.get('http://catfacts-api.appspot.com/api/facts?number=1')
    if response.status_code == requests.codes.ok:
        json = response.json()
        if json['success'] == "true":
            message.reply_to_user(json['facts'][0])
```

**You can also handle the timeout event**
```python

from gevent import Timeout, sleep

@module.hear('sleep for (\d+) seconds')
@module.async(timeout=5)
def sleep_for(message, seconds):
    try:
        message.reply("Okay, I'm going to try to sleep for %s seconds" % seconds)
        sleep(int(seconds))
        
    except Timeout:
        message.reply("OOPS! I slept for too long! Oh well :C")
```

## Greenlet Functions
### `module.spawn(f, *args, **kwargs)`
Spawns a greenlet to run a function. The greenlet will be killed if it doesn't finish before the module unloads. 

#### Example
```python

from gevent import sleep

def background_task(what):
    print "I'm doing %s in the background... not sure what" % what
    sleep(50)
    print "okay... it finished!"

@module.hear('do (.*?) in the background')
def do_background_task(message, what):
    module.spawn(background_task, what)
    message.reply("okay! started background task to do %s!" % what)
```


### `moudle.spawn_after(delay, f, *args, **kwargs)`
Schedules a greenlet that will run `f` after `delay` seconds. The greenlet will be killed/unscheduled if it doesn't
start/finish before the module unloads.

#### Example
```python
import random

@module.hear('reply to me slowly')
def reply_slowly(message):
    module.spawn_after(random.randint(5, 10), message.reply, "is this slow enough?")

```

## Web
If `JEEV_WEB` is set to `TRUE`, Jeev runs a WSGI server that dispatches requests to loaded modules by their name. 

Basically when Jeev gets a request at "/foo/bar", it will look and see if the `foo` is loaded, and that it has a wsgi
app bound (via `module.is_web`) and then call the module's WSGI handler (`module.app`) with an environment that has
`SCRIPT_NAME` and `PATH_INFO` modified and set to `/foo`, and `/bar` respectively.  

### `module.app`
By default, module.app when accessed for the first time will initialize an empty Flask application to handle requests.
This makes it super easy to write web hooks and functions.

#### Example
```python

# Assume the module name is `webtest`
from flask import Response, request

# Will get called when '/webtest' is requested.
@module.app.route('/')
def index():
    return Response("Hello, I am {}".format(module.jeev.name))

# Will get called when '/webtest/webhook' gets a POST request that will send a message to a channel specified
# in the POST body.
# $ curl -d "channel=jeev&message=hey+there+from+the+web" http://localhost:8080/webtest/webhook
# OK
@module.app.route('/webhook', methods=['POST'])
def handle_webhook():
    module.send_message(request.form['channel'], request.form['message'])
    return Response('OK')
```

*You can also set `module.app` to your own custom WSGI handler if you don't want to use Flask.*
```python
from some.package.web import app

module.app = app
```

### `module.is_web`
Returns True if the module has a WSGI handler bound.

### `module.set_wsgi_handler(handler)`
This is essentially the same as setting `module.app` but it can be used as a decorator.

#### Example
```python

@module.set_wsgi_handler
def wsgi_handler(environ, start_response):
    start_response('200 OK', [])
    return ['Hello World\n']
```

## Chat Functions

### `module.send_message(channel, message)`
Sends `message` to `channel`. This usually isn't called. Instead, use `message.reply(message)` to send a message
to the channel the message was received in. 

#### Example

```python
@module.hear('lol')
def handle(message):
    # These do the same thing:
    message.reply('what are you laughing about?')
    module.send_message(message.channel, 'what are you laughing about?')
     
    # These too, for addressing the user.
    message.reply_to_user('what?')
    module.send_message(message.channel, '%s: what?' % message.user)
```