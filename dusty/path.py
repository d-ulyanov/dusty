from __future__ import absolute_import

import os
import subprocess
import time

from . import constants
from .config import get_config_value
from .platform import platform_specific, OSX, LINUX

def parent_dir(path):
    """Return the parent directory of a file or directory.
    This is commonly useful for creating parent directories
    prior to creating a file."""
    return os.path.split(path)[0]

@platform_specific
def cp_path(app_or_service_name, platform):
    if platform == OSX:
        return os.path.join(constants.VM_CP_DIR, app_or_service_name)
    elif platform == LINUX:
        return os.path.join(constants.LOCAL_CP_DIR, app_or_service_name)

@platform_specific
def command_files_path(app_or_service_name, platform):
    if platform == OSX:
        return os.path.join(constants.VM_COMMAND_FILES_DIR, app_or_service_name)
    elif platform == LINUX:
        return os.path.join(constants.COMMAND_FILES_DIR, app_or_service_name)

@platform_specific
def mount_repos_dir(platform):
    if platform == OSX:
        return constants.VM_REPOS_DIR
    elif platform == LINUX:
        return constants.REPOS_DIR

def dir_modified_time(path):
    return time.ctime(os.path.getmtime(path))

def set_mac_user_ownership(path):
    command = "chown -R {} {}".format(get_config_value(constants.CONFIG_MAC_USERNAME_KEY), path).split()
    subprocess.check_call(command)
