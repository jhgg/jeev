import module

@module.command('!ping')
def ping(message):
    message.reply_to_user('pong!')


@module.respond('whats the weather')
def respond_weather(message):
    message.reply_to_user('the weather is swell')