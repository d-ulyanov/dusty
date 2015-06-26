# Platform specific stuff

from __future__ import absolute_import

import subprocess
import sys

OSX = 'darwin'
LINUX = 'linux'

def _on_platform(platform):
    return sys.platform.startswith(platform)

def get_platform():
    if _on_platform(OSX):
        return OSX
    if _on_platform(LINUX):
        return LINUX
    raise RuntimeError('Platform not found: {}'.format(sys.platform))

def restrict_to_platform(platform):
    def wrap(f):
        def wrapped_f(*args, **kwargs):
            if not _on_platform(platform):
                raise RuntimeError("Not on platform {}".format(platform))
            return f(*args, **kwargs)
        return wrapped_f
    return wrap

def noop_on_platform(platform):
    def wrap(f):
        def wrapped_f(*args, **kwargs):
            if _on_platform(platform):
                return
            return f(*args, **kwargs)
        return wrapped_f
    return wrap

def platform_specific(f):
    def wrapped_f(*args, **kwargs):
        return f(*args, platform=get_platform(), **kwargs)
    return wrapped_f

def running_osx():
    return _on_platform(OSX)
