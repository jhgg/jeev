import module

@module.respond('hi')
def hi(message):
    message.reply_to_user('Hey! Check out more about creating modules for Jeev here: '
                          'https://github.com/jhgg/jeev/tree/master/docs/modules')