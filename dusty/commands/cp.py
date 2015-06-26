import os
import uuid
import tempfile
from contextlib import contextmanager
import shutil

from .. import constants
from ..path import cp_path
from ..systems.rsync import sync_local_path_to_vm, sync_local_path_from_vm, vm_path_is_directory
from ..systems.docker.files import (move_dir_inside_container, move_file_inside_container,
                               copy_path_inside_container)
from ..payload import daemon_command
from .. import platform

@contextmanager
def _cleanup_path(path):
    """Recursively delete a path upon exiting this context
    manager. Supports targets that are files or directories."""
    try:
        yield
    finally:
        if os.path.exists(path):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

@daemon_command
def copy_between_containers(source_name, source_path, dest_name, dest_path):
    """Copy a file from the source container to an intermediate staging
    area on the local filesystem, then from that staging area to the
    destination container.

    These moves take place without demotion for two reasons:
      1. There should be no permissions vulnerabilities with copying
         between containers because it is assumed the non-privileged
         user has full access to all Dusty containers.
      2. The temp dir created by mkdtemp is owned by the owner of the
         Dusty daemon process, so if we demoted our moves to/from that location
         they would encounter permission errors."""
    temp_path = os.path.join(tempfile.mkdtemp(), str(uuid.uuid1()))
    with _cleanup_path(temp_path):
        copy_to_local(temp_path, source_name, source_path, demote=False)
        copy_from_local(temp_path, dest_name, dest_path, demote=False)

def local_to_shared_cp(local_path, remote_name, temp_id, demote=True):
    if platform.get_platform() == platform.OSX:
        sync_local_path_to_vm(local_path, os.path.join(cp_path(remote_name), temp_identifier), demote=demote)
    elif platform.get_platform() == platform.LINUX:
        raise NotImplementedError

def local_from_shared_cp(local_path, remote_name, temp_id, demote=True):
    remote_path = os.path.join(cp_path(remote_name), temp_id)
    if platform.get_platform() == platform.OSX:
        is_dir = vm_path_is_directory(remote_path)
        sync_local_path_from_vm(local_path, remote_path, demote=demote, is_dir=is_dir)
    elif platform.get_platform() == platform.LINUX:
        raise NotImplementedError

@daemon_command
def copy_from_local(local_path, remote_name, remote_path, demote=True):
    """Copy a path from the local filesystem to a path inside a Dusty
    container. The files on the local filesystem must be accessible
    by the user specified in mac_username."""
    temp_identifier = str(uuid.uuid1())
    local_to_shared_cp(local_path, remote_name, temp_identifier, demote=demote)
    if os.path.isdir(local_path):
        move_dir_inside_container(remote_name, os.path.join(constants.CONTAINER_CP_DIR, temp_identifier), remote_path)
    else:
        move_file_inside_container(remote_name, os.path.join(constants.CONTAINER_CP_DIR, temp_identifier), remote_path)

@daemon_command
def copy_to_local(local_path, remote_name, remote_path, demote=True):
    """Copy a path from inside a Dusty container to a path on the
    local filesystem. The path on the local filesystem must be
    wrist-accessible by the user specified in mac_username."""
    temp_identifier = str(uuid.uuid1())
    copy_path_inside_container(remote_name, remote_path, os.path.join(constants.CONTAINER_CP_DIR, temp_identifier))
    local_from_shared_cp(local_path, remote_name, temp_identifier, demote=demote)
