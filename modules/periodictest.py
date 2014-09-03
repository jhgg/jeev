import module


@module.loaded
def loaded():
    module.g.periodic = module.periodic(1, say_something)


def say_something():
    module.send_message(module.g.channel, 'something!')

@module.hear('periodic')
def periodic_go(message):
    if module.g.periodic.started:
        module.g.periodic.stop()
        message.reply('stopped')
    else:
        module.g.channel = message.channel
        module.g.periodic.start()
        message.reply('started')


@module.hear('stfu')
def unload_me(message):
    message.reply("shutting up forever!!!")
    import gevent
    gevent.spawn_raw(module.jeev.modules.unload, 'periodictest')