class _Event(object):
    __slots__ = ['args', 'help_text', 'class_name', 'attribute_name']

    def __init__(self, *args, **kwargs):
        self.args = args
        self.help_text = kwargs.pop('help_text', None)
        self.class_name = kwargs.pop('class_name', None)
        self.attribute_name = kwargs.pop('attribute_name', None)

    def bind(self, class_name, attribute_name):
        return self.__class__(*self.args,
                              help_text=self.help_text, class_name=class_name, attribute_name=attribute_name)

    def __repr__(self):
        return '<jeev.events.%s.%s (%s)>' % (self.class_name, self.attribute_name, self.help_text)


class EventCategoryBase(type):
    def __new__(mcs, name, bases, dct):
        for k, v in dct.items():
            if isinstance(v, _Event):
                dct[k] = v.bind(name, k)

        return super(EventCategoryBase, mcs).__new__(mcs, name, bases, dct)


class Message(object):
    MessageChanged = _Event()
    MessageDeleted = _Event()


class Channel(object):
    __metaclass__ = EventCategoryBase

    Marked = _Event(help_text="Your channel read marker was updated.")
    Created = _Event(help_text="A team channel was created.")
    Joined = _Event(help_text="You joined a channel.")
    Left = _Event(help_text="You left a channel.")
    Deleted = _Event(help_text="A team channel was deleted.")
    Renamed = _Event(help_text="A team channel was renamed.")
    Archived = _Event(help_text="A team channel was archived.")
    UnArchived = _Event(help_text="A team channel was unarchived.")
    HistoryChanged = _Event(help_text="Bulk updates were made to a channel's history.")

    BotMessage = _Event()
    MeMessage = _Event()
    Message = _Event(help_text="A message was sent to a channel.")

    UserJoined = _Event(help_text="A team member joined a channel.")
    UserLeft = _Event(help_text="A team member left a channel.")
    TopicUpdated = _Event(help_text="A channel topic was updated.")
    PurposeUpdated = _Event(help_text="A channel purpose was updated.")
    NameUpdated = _Event(help_text="A channel was renamed.")


class User(object):
    __metaclass__ = EventCategoryBase
    Changed = _Event()
    PresenceChanged = _Event()


class DirectMessage(object):
    __metaclass__ = EventCategoryBase

    Created = _Event("A direct message channel was created.")
    Opened = _Event("You opened a direct message channel.")
    Closed = _Event("You closed a direct message channel.")
    Marked = _Event("A direct message read marker was updated.")
    HistoryChanged = _Event("Bulk updates were made to a DM channel's history.")

    Message = _Event(help_text="A direct message was received.")
    MeMessage = _Event()


class Group(object):
    __metaclass__ = EventCategoryBase

    Joined = _Event("You joined a private group.")
    Opened = _Event("You left a private group.")
    Closed = _Event("You opened a group channel.")
    Renamed = _Event("You closed a group channel.")
    Archived = _Event("A private group was archived.")
    UnArchived = _Event("A private group was unarchived.")
    HistoryChanged = _Event("A private group was renamed.")

    UserJoined = _Event(help_text="A team member joined a group.")
    UserLeft = _Event(help_text="A team member left a group.")
    TopicUpdated = _Event(help_text="A group topic was updated.")
    PurposeUpdated = _Event(help_text="A group purpose was updated.")
    NameUpdated = _Event(help_text="A group was renamed.")

    Message = _Event(help_text="A direct message was received.")
    MeMessage = _Event()


class Team(object):
    __metaclass__ = EventCategoryBase

    Joined = _Event("A new team member has joined.")