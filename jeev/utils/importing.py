from importlib import import_module
import os

_import_dotted_path_cache = {}
_get_model_cache = {}


def path_for_import(name):
    """
    Returns the directory path for the given package or module.
    """
    return os.path.dirname(os.path.abspath(import_module(name).__file__))


def import_dotted_path(path):
    """
    Takes a dotted path to a member name in a module, and returns
    the member after importing it.
    """
    member = _import_dotted_path_cache.get(path, None)
    if member is not None:
        return member

    try:
        module_path, member_name = path.rsplit(".", 1)
        module = import_module(module_path)
        member = getattr(module, member_name)
        _import_dotted_path_cache[path] = member
        return member
    except (ValueError, ImportError, AttributeError) as e:
        raise ImportError("Could not import the name: %s: %s" % (path, e))

