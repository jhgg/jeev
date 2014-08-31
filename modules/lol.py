import random
import module


@module.listen()
def determine_if_funny(message):
    if random.randint(1, 100) > 98:
        module.spawn_after(random.randint(2, 5), message.reply, 'lol')