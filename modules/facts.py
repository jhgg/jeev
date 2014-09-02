import module


@module.hear('throw me the facts')
def facts(message):
    message.reply('just the basics?')


@module.hear('i feel the same')
def feel(message):
    message.reply('SUCCESS! These are designed to make you feel the same!')