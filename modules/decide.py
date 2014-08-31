import module
import random


module.respond('decide "(.*)"')(
    lambda m, what: m.reply_to_user('Definitely %s' % random.choice(what.split('" "')))
)

module.respond('decide ([^"]+)')(
    lambda m, what: m.reply_to_user('Definitely %s' % random.choice(what.split()))
)