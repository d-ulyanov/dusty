import docker
from ...log import log_to_client


def _ensure_testing_spec_base_image(docker_client, testing_spec):
    log_to_client('Getting the base image for the new image')
    if 'image' in testing_spec and 'build' in testing_spec:
        raise RuntimeError('Only 1 of `image` and `build` keys are allowed in testing spec')
    elif 'image' in testing_spec:
        log_to_client('Base image is {}'.format(testing_spec['image']))
        return testing_spec['image']
    elif 'build' in testing_spec:
        image_tag = 'dusty_testing_base/image'
        log_to_client('Need to build the base image based off of the Dockerfile here: {}'.format(testing_spec['build']))
        docker_client.build(path=testing_spec['build'], tag=image_tag)
        return image_tag
    else:
        raise RuntimeError('One of `image` or `build` is required in testing spec')

def _get_split_volumes(volumes):
    split_volumes = []
    for volume in volumes:
        volume_list = volume.split(':')
        split_volumes.append({'host_location': volume_list[0],
                              'container_location': volume_list[1]})
    return split_volumes

def _get_create_container_volumes(split_volumes):
    return [volume_dict['container_location'] for volume_dict  in split_volumes]

def _get_create_container_binds(split_volumes):
    binds_dict = {}
    for volume_dict in split_volumes:
        binds_dict[volume_dict['host_location']] =  {'bind': volume_dict['container_location'], 'ro': False}
    return binds_dict


def _make_installed_requirements_image(docker_client, base_image_tag, command, image_name, volumes=[]):
    split_volumes = _get_split_volumes(volumes)
    create_container_volumes = _get_create_container_volumes(split_volumes)
    create_container_binds = _get_create_container_binds(split_volumes)

    container = docker_client.create_container(image=base_image_tag,
                                               command=command,
                                               volumes=create_container_volumes,
                                               host_config=docker.utils.create_host_config(binds=create_container_binds))
    # start does not wait for the command to finish
    docker_client.start(container=container['Id'])
    docker_client.wait(container=container['Id'])
    # new_image = docker_client.commit(container=container['Id'], tag=image_name)
    # Above command is not tagging the image, even though it seems like it should be sending
    # all of the arguments.  Below is a workaround
    new_image = docker_client.commit(container=container['Id'])
    docker_client.tag(image=new_image['Id'], repository=image_name, force=True)
    return image_name

def _make_installed_testing_image(docker_client, testing_spec, new_image_name, volumes=[]):
    base_image_tag = _ensure_testing_spec_base_image(docker_client, testing_spec)
    _make_installed_requirements_image(docker_client, base_image_tag, testing_spec['once'], new_image_name, volumes=volumes)
    return new_image_name

def ensure_image_exists(docker_client, testing_spec, image_name, volumes=[], force_recreate=False):
    images = docker_client.images()
    image_exists = False
    for image in images:
        if any(image_name in tag for tag in image['RepoTags']):
            image_exists = True
            break
    if force_recreate or not image_exists:
        log_to_client('Creating a new image named {}, with installed dependencies for the app or lib'.format(image_name))
        _make_installed_testing_image(docker_client, testing_spec, image_name, volumes=volumes)
        log_to_client('Image is now created')