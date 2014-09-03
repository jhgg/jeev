from ..utils import importing


def get_adapter_by_name(name):
    if '.' not in name:
        name = 'jeev.adapter.%s.adapter' % name

    return importing.import_dotted_path(name)