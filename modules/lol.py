import random
from gevent import sleep


def export(module):

    @module.listen()
    @module.async()
    def determine_if_funny(message):
        if random.randint(1, 100) > 98:
            sleep(random.randint(2, 5))
            message.reply('lol')