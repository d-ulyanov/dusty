import os
import logging

import yaml

from . import (get_canonical_container_name, get_docker_env, get_docker_client,
               get_dusty_containers, get_app_or_service_name_from_container,
               get_container_for_app_or_service)
from ... import constants
from ...log import log_to_client
from ...subprocess import check_output_demoted, check_and_log_output_and_error_demoted
from ...compiler.spec_assembler import get_assembled_specs
from ...compiler.compose import links_for_app_or_service
from ...path import parent_dir

def write_composefile(compose_config, compose_file_location):
    compose_dir_location = parent_dir(compose_file_location)
    if not os.path.exists(compose_dir_location):
        os.makedirs(compose_dir_location)
    with open(compose_file_location, 'w') as f:
        f.write(yaml.safe_dump(compose_config, default_flow_style=False))

def _compose_base_command(core_command, compose_file_location, project_name):
    command = ['docker-compose']
    if compose_file_location is not None:
        command += ['-f', compose_file_location]
    if project_name is not None:
        command += ['-p', project_name]
    command += core_command
    return command

def compose_up(compose_file_location, project_name, recreate_containers=True, quiet=False):
    command = _compose_base_command(['up', '-d', '--allow-insecure-ssl'], compose_file_location, project_name)
    if not recreate_containers:
        command.append('--no-recreate')
    # strip_newlines should be True here so that we handle blank lines being caused by `docker pull <image>`
    check_and_log_output_and_error_demoted(command, env=get_docker_env(), strip_newlines=True, quiet_on_success=quiet)

def _compose_stop(compose_file_location, project_name, services):
    command = _compose_base_command(['stop', '-t', '1'], compose_file_location, project_name)
    if services:
        command += services
    check_and_log_output_and_error_demoted(command, env=get_docker_env())

def _compose_rm(compose_file_location, project_name, services):
    command = _compose_base_command(['rm', '-v', '-f'], compose_file_location, project_name)
    if services:
        command += services
    check_and_log_output_and_error_demoted(command, env=get_docker_env())

def _check_stopped_linked_containers(container, assembled_specs):
    stopped_containers = []
    app_or_service_name = get_app_or_service_name_from_container(container)
    linked_containers = links_for_app_or_service(app_or_service_name, assembled_specs)
    for linked_name in linked_containers:
        if get_dusty_containers([linked_name]) == []:
            stopped_containers.append(linked_name)
    return stopped_containers

def _compose_restart(services):
    """Well, this is annoying. Compose 1.2 shipped with the
    restart functionality fucking broken, so we can't set a faster
    timeout than 10 seconds (which is way too long) using Compose.
    We are therefore resigned to trying to hack this together
    ourselves. Lame.

    Relevant fix which will make it into the next release:
    https://github.com/docker/compose/pull/1318"""

    def _restart_container(client, container):
        log_to_client('Restarting {}'.format(get_canonical_container_name(container)))
        client.restart(container['Id'], timeout=1)

    assembled_specs = get_assembled_specs()
    if services == []:
        services = [spec.name for spec in assembled_specs.get_apps_and_services()]
    logging.info('Restarting service containers from list: {}'.format(services))
    client = get_docker_client()
    for service in services:
        container = get_container_for_app_or_service(service, include_exited=True)
        if container is None:
            log_to_client('No container found for {}'.format(service))
            continue
        stopped_linked_containers = _check_stopped_linked_containers(container, assembled_specs)
        if stopped_linked_containers:
            log_to_client('No running containers {0}, which are linked to by {1}.  Cannot restart {1}'.format(
                              stopped_linked_containers, service))
        else:
            _restart_container(client, container)

def update_running_containers_from_spec(compose_config, recreate_containers=True):
    """Takes in a Compose spec from the Dusty Compose compiler,
    writes it to the Compose spec folder so Compose can pick it
    up, then does everything needed to make sure the Docker VM is
    up and running containers with the updated config."""
    write_composefile(compose_config, constants.COMPOSEFILE_PATH)
    compose_up(constants.COMPOSEFILE_PATH, 'dusty', recreate_containers=recreate_containers)

def stop_running_services(services=None):
    """Stop running containers owned by Dusty, or a specific
    list of Compose services if provided.

    Here, "services" refers to the Compose version of the term,
    so any existing running container, by name. This includes Dusty
    apps and services."""
    if services is None:
        services = []
    _compose_stop(constants.COMPOSEFILE_PATH, 'dusty', services)

def restart_running_services(services=None):
    """Restart containers owned by Dusty, or a specific
    list of Compose services if provided.

    Here, "services" refers to the Compose version of the term,
    so any existing running container, by name. This includes Dusty
    apps and services."""
    if services is None:
        services = []
    _compose_restart(services)

def rm_containers(app_or_service_names):
    _compose_rm(constants.COMPOSEFILE_PATH, 'dusty', app_or_service_names)
