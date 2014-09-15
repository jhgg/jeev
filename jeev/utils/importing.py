from importlib import import_module
import os
import sys

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


def _is_right_import_error(mod_name, tb):
    while tb is not None:
        g = tb.tb_frame.f_globals

        if '__name__' in g and g['__name__'] == mod_name:
            return True
        tb = tb.tb_next

    return False


def import_first_matching_module(mod_name, matches, try_mod_name=True, pre_import_hook=None, post_import_hook=None):
    """
        Tries to import a module by running multiple patterns, for example:

        >>> matched_name, module = import_first_matching_module('foo', ['test.%s', 'test.bar.%s'])

        Will try to import:
            * foo.py
            * test/foo.py
            * test/bar/foo.py

        And return the first one that exists. It will properly re-raise the ImportError that the module thew it
        because a dependency did not exist by inspecting the traceback.
    """
    if mod_name in sys.modules:
        return sys.modules[mod_name]

    if try_mod_name:
        matches = ['%s'] + matches

    tries = []
    for match in matches:
        match_name = match % mod_name
        tries.append(match_name)

        try:
            if pre_import_hook:
                pre_import_hook(match_name)

            __import__(match_name)
            return match_name, sys.modules[match_name]
        except ImportError:
            exc_info = sys.exc_info()
            sys.modules.pop(match_name, None)

            if _is_right_import_error(match_name, exc_info[2]):
                raise exc_info
        finally:

            if post_import_hook:
                post_import_hook(match_name)

    raise ImportError('No module named %s (tried: %s)' % (mod_name, ', '.join(tries)))