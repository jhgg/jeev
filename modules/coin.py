import random

export = lambda mod: mod.hear('(?:throw|flip|toss) a coin')(lambda m: m.reply_to_user(random.choice(['heads', 'tails'])))