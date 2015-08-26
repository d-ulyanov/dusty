import logging

from prettytable import PrettyTable

from ..compiler.spec_assembler import get_assembled_specs
from ..log import log_to_client
from ..systems.docker import get_dusty_containers
from ..systems.virtualbox import docker_vm_is_running
from ..payload import daemon_command
from .. import constants
from ..config import get_env_config

def _has_active_container(spec_type, service_name):
    if spec_type == 'lib':
        return False
    return get_dusty_containers([service_name]) != []

def _has_env_override(app_or_service_name):
    return True if get_env_config().get(app_or_service_name) else False

@daemon_command
def get_dusty_status():
    if not docker_vm_is_running():
        log_to_client('Docker VM is powered off.  You can start it with `dusty up`')
        return
    assembled_specs = get_assembled_specs()
    table = PrettyTable(["Name", "Type", "Has Active Container", "Env Overridden?"])
    logging.error(assembled_specs._document)
    # Check for Dusty's special nginx container (used for host forwarding)
    table.add_row([constants.DUSTY_NGINX_NAME, '', 'X' if get_dusty_containers([constants.DUSTY_NGINX_NAME]) != [] else '', ''])
    for spec in assembled_specs.get_apps_libs_and_services():
        spec_type = spec.type_singular
        if spec_type == 'service' or spec_type == 'app':
            env_override = _has_env_override(spec.name)
        else:
            env_override = False
        service_name = spec.name
        has_activate_container = _has_active_container(spec_type, service_name)
        table.add_row([service_name, spec_type, 'X' if has_activate_container else '', 'X' if env_override else ''])
    log_to_client(table.get_string(sortby="Type"))
