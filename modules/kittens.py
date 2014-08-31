import random
import module

def kitten_url(h=None, w=None):
    w = w or random.randint(250, 500)
    h = h or random.randint(250, 500)

    return "http://placekitten.com/%i/%i#.png" % (h, w)

@module.respond('kittens?(?: me)?.?$')
def kitten_me(message, *args):
    message.reply_to_user(kitten_url())