"""Listen for user commands to Dusty

Usage:
  dusty -d [--suppress-warnings] [--preflight-only]

Options:
  --suppress-warnings  Do not display run time warnings to the client
  --preflight-only  Only run the preflight_check, then exit
"""

import os
import atexit
import logging
import socket

from docopt import docopt

from .preflight import preflight_check, refresh_preflight_warnings
from .log import configure_logging, make_socket_logger, close_socket_logger
from .constants import SOCKET_PATH, SOCKET_TERMINATOR, SOCKET_ERROR_TERMINATOR
from .payload import Payload, get_payload_function
from .warnings import daemon_warnings
from .config import refresh_config_warnings, check_and_load_ssh_auth
from . import constants

connection = None

def _clean_up_existing_socket(socket_path):
    try:
        os.unlink(socket_path)
    except OSError:
        if os.path.exists(socket_path):
            raise

def _send_warnings_to_client(connection, suppress_warnings):
    if daemon_warnings.has_warnings and not suppress_warnings:
        connection.sendall("{}\n".format(daemon_warnings.pretty()))

def _get_payload_function_data(payload):
    return get_payload_function(payload['fn_key']), payload['args'], payload['kwargs']

def _refresh_warnings():
    if daemon_warnings.has_warnings:
        refresh_config_warnings()
        refresh_preflight_warnings()

def _run_pre_command_functions(connection, suppress_warnings, client_version):
    check_and_load_ssh_auth()
    _refresh_warnings()

def close_client_connection():
    try:
        connection.sendall(SOCKET_TERMINATOR)
    finally:
        close_socket_logger()
        connection.close()

def _listen_on_socket(socket_path, suppress_warnings):
    global connection
    _clean_up_existing_socket(socket_path)
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(socket_path)
    os.chmod(socket_path, 0777) # don't delete the 0, it makes Python interpret this as octal
    sock.listen(5)
    logging.info('Listening on socket at {}'.format(socket_path))

    while True:
        try:
            connection, client_address = sock.accept()
            make_socket_logger(connection)
            try:
                data = connection.recv(1024)
                if not data:
                    continue
                payload = Payload.deserialize(data)
                client_version = payload['client_version']
                fn, args, kwargs = _get_payload_function_data(payload)
                suppress_warnings |= payload['suppress_warnings']
                logging.info('Received command. fn: {} args: {} kwargs: {}'.format(fn.__name__, args, kwargs))
                try:
                    if client_version != constants.VERSION:
                        raise RuntimeError("Dusty daemon is running version: {}, and client is running version: {}".format(constants.VERSION, client_version))
                    _run_pre_command_functions(connection, suppress_warnings, client_version)
                    _send_warnings_to_client(connection, suppress_warnings)
                    fn(*args, **kwargs)
                except Exception as e:
                    logging.exception("Daemon encountered exception while processing command")
                    error_msg = e.message if e.message else str(e)
                    _send_warnings_to_client(connection, suppress_warnings)
                    connection.sendall('ERROR: {}\n'.format(error_msg).encode('utf-8'))
                    connection.sendall(SOCKET_ERROR_TERMINATOR)
            finally:
                close_client_connection()
        except KeyboardInterrupt:
            break
        except:
            logging.exception('Exception on socket listen')
    _clean_up_existing_socket(socket_path)

def main():
    args = docopt(__doc__)
    configure_logging()
    preflight_check()
    if args['--preflight-only']:
        return
    refresh_config_warnings()
    _listen_on_socket(SOCKET_PATH, args['--suppress-warnings'])

if __name__ == '__main__':
    main()
