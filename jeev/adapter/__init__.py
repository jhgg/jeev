from utils import importing


def get_by_name(name):
    return importing.import_dotted_path('jeev.adapter.%s.adapter' % name)