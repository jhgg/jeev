export = lambda mod: mod.hear('(?:sudo) ?(.*)')(
    lambda m, what: m.reply("Alright. I'll %s" % (what or "do whatever it is you wanted.")))