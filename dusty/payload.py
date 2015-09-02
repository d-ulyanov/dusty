import json
import yaml

from .constants import VERSION

def _encode_utf8(args):
    for idx, arg in enumerate(args):
        if isinstance(arg, basestring):
            args[idx] = arg.encode('utf-8')
        if isinstance(arg, list):
            args[idx] = _encode_utf8(arg)
    return args

class Payload(object):
    def __init__(self, fn, *args, **kwargs):
        self.fn = fn
        self.run_on_daemon = True
        self.client_version = VERSION
        self.args = args
        self.kwargs = kwargs
        self.suppress_warnings = False

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return self.fn == other.fn and self.args == other.args and self.kwargs == other.kwargs
        return False

    def run(self):
        self.fn(*self.args, **self.kwargs)

    def serialize(self):
        fn_key = function_key(self.fn)
        if fn_key not in _daemon_command_mapping:
            raise RuntimeError('Function key {} not found; you may need to decorate your function'.format(fn_key))
        doc = {'fn_key': fn_key, 'client_version': self.client_version, 'suppress_warnings': self.suppress_warnings,
               'args': self.args, 'kwargs': self.kwargs}
        return json.dumps(doc, ensure_ascii=False)

    @staticmethod
    def deserialize(doc):
        loaded = yaml.safe_load(doc)
        loaded['args'] = _encode_utf8(loaded['args'])
        return loaded

_daemon_command_mapping = {}

def function_key(fn):
    return '{}.{}'.format(fn.__module__, fn.__name__)

def daemon_command(fn):
    key = function_key(fn)
    if key in _daemon_command_mapping and _daemon_command_mapping[key] != fn:
        raise RuntimeError("Function mapping key collision: {}. Name one of the functions something else".format(key))
    _daemon_command_mapping[key] = fn
    return fn

def get_payload_function(fn_key):
    if fn_key not in _daemon_command_mapping:
        raise RuntimeError('Function key {} not found'.format(fn_key))
    return _daemon_command_mapping[fn_key]
