import module

module.opt("foo", "A test variable", default=1)
module.opt("bar", "A required variable.")


@module.loaded
def init():
    print module.opts['foo']


@module.opt_validator('foo')
def validate_foo(value):
    raise module.ConfigError('Foo sucks!')