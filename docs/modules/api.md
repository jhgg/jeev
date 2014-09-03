Documentation for the public module API with examples.

## Properties
### `module.name`
Gets the module's name.

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
### `@module.match(regex, flags=0, priority=0)`
### `@module.hear(regex, priority=0)`
### `@module.respond(regex, flags=re.I, priority=0)`

## Function Decorators
## `@module.async(sync_return_val=None, timeout=0)`

## Greenlet Functions
## `module.spawn(f, *args, **kwargs)`
## `moudle.spawn_after(delay, f, *args, **kwargs)`

## Web

### `module.is_web`
### `module.app`
#### getter:

##### Example

#### setter:
    
## `module.set_wsgi_handler(handler)`

## Chat Functions

### `module.send_message(channel, message)`
