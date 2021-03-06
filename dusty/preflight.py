"""This module contains checks for system dependencies that are run
when Dusty daemon first starts up. Any failed checks should throw an exception
which bubbles up to the daemon and causes it to crash."""

from __future__ import absolute_import

import os
import logging
import subprocess
import warnings

from .config import write_default_config, check_and_load_ssh_auth
from . import constants
from .warnings import daemon_warnings
from .subprocess import check_and_log_output_and_error
from . import constants

class PreflightException(Exception):
    pass

def returns_exception(f):
    def inner():
        try:
            f()
            return None
        except Exception as e:
            return e
    return inner

def _assert_executable_exists(executable_name):
    logging.info('Checking for existence of {}'.format(executable_name))
    try:
        subprocess.check_output('which {}'.format(executable_name), shell=True)
    except subprocess.CalledProcessError, OSError:
        raise PreflightException('Executable not found: {}'.format(executable_name))

@returns_exception
def _check_git():
    _assert_executable_exists('git')

@returns_exception
def _check_rsync():
    _assert_executable_exists('rsync')

@returns_exception
def _check_virtualbox():
    _assert_executable_exists('VBoxManage')

@returns_exception
def _check_docker_machine():
    _assert_executable_exists('docker-machine')

@returns_exception
def _check_docker():
    _assert_executable_exists('docker')

@returns_exception
def _check_docker_compose():
    _assert_executable_exists('docker-compose')

@returns_exception
def _assert_hosts_file_is_writable():
    if not os.access(constants.HOSTS_PATH, os.W_OK):
        raise OSError('Hosts file at {} is not writable'.format(constants.HOSTS_PATH))

def _ensure_run_dir_exists():
    if not os.path.exists(constants.RUN_DIR):
        os.makedirs(constants.RUN_DIR)

def _ensure_config_dir_exists():
    if not os.path.exists(constants.CONFIG_DIR):
        os.makedirs(constants.CONFIG_DIR)

def _ensure_command_files_dir_exists():
    if not os.path.exists(constants.COMMAND_FILES_DIR):
        os.makedirs(constants.COMMAND_FILES_DIR)

def _check_executables():
    return [check() for check in [_check_git, _check_rsync, _check_virtualbox,
                                  _check_docker_machine, _check_docker, _check_docker_compose]]

def refresh_preflight_warnings():
    daemon_warnings.clear_namespace('preflight')
    _check_executables()

def preflight_check():
    logging.info('Starting preflight check')
    logging.info('Checking for required executables. PATH is {}'.format(os.getenv('PATH')))
    errors = _check_executables()
    errors.append(_assert_hosts_file_is_writable())
    str_errors = [str(e) for e in errors if e is not None]
    if str_errors:
        raise PreflightException("Preflight Errors: \n\t{}".format('\n\t'.join(str_errors)))
    _ensure_run_dir_exists()
    _ensure_config_dir_exists()
    _ensure_command_files_dir_exists()
    if not os.path.exists(constants.CONFIG_PATH):
        logging.info('Creating default config file at {}'.format(constants.CONFIG_PATH))
        write_default_config()
    check_and_load_ssh_auth()
    logging.info('Completed preflight check successfully')
