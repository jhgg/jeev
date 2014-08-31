import module


@module.hear('(?:throw|flip|toss) a coin')
def flip_coin(message):
    message.reply_with_one_of('heads', 'tails')