#
# INTEL CONFIDENTIAL
# Copyright (c) 2018 Intel Corporation
#
# The source code contained or described herein and all documents related to
# the source code ("Material") are owned by Intel Corporation or its suppliers
# or licensors. Title to the Material remains with Intel Corporation or its
# suppliers and licensors. The Material contains trade secrets and proprietary
# and confidential information of Intel or its suppliers and licensors. The
# Material is protected by worldwide copyright and trade secret laws and treaty
# provisions. No part of the Material may be used, copied, reproduced, modified,
# published, uploaded, posted, transmitted, distributed, or disclosed in any way
# without Intel's prior express written permission.
#
# No license under any patent, copyright, trade secret or other intellectual
# property right is granted to or conferred upon you by disclosure or delivery
# of the Materials, either expressly, by implication, inducement, estoppel or
# otherwise. Any license under such intellectual property rights must be express
# and approved by Intel in writing.
#

import os
import random
import string
from time import sleep
from typing import Optional

import docker
from docker.errors import NotFound
from docker.models.containers import Container
from cli_text_consts import UtilSocatTexts as Texts
from util.config import Config


client = docker.from_env()

SOCAT_CONTAINER_NAME_PREFIX = 'dlsctl-registry-bridge'

socat_container_name = 'socat-'

SOCAT_IMAGE_FILE_NAME = 'socat-container-image.tar.gz'

SOCAT_IMAGE_NAME = 'socat-container-image:latest'


def get() -> Optional[Container]:
    try:
        socat_container = client.containers.get(socat_container_name)  # type: Container
        if socat_container.status != 'running':
            socat_container.remove(force=True)
            return None
    except NotFound:
        return None

    return socat_container


def _ensure_socat_running():
    for _ in range(120):
        try:
            socat_container = client.containers.get(socat_container_name)
        except NotFound:
            sleep(1)
            continue

        if socat_container.status == 'running':
            return

        sleep(1)

    raise RuntimeError(Texts.SOCAT_CONTAINER_START_FAIL_MSG.format(container_status=socat_container.status))


def load_socat_image():
    config = Config()
    if config.config_path and not client.images.list(name=SOCAT_IMAGE_NAME):
        with open(os.path.join(config.config_path, SOCAT_IMAGE_FILE_NAME), "rb") as file:
            client.images.load(file)

        if not client.images.list(name=SOCAT_IMAGE_NAME):
            raise RuntimeError


def start(docker_registry_port: str):
    """
    This function is synchronous - it returns when socat container is running.
    :param docker_registry_port:
    :return:
    """
    global socat_container_name
    random_part = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits)
                          for _ in range(5))
    socat_container_name = f'{SOCAT_CONTAINER_NAME_PREFIX}-{random_part}-' \
                           f'{docker_registry_port}'
    load_socat_image()
    client.containers.run(detach=True, remove=True, network_mode='host', name=socat_container_name,
                          image=SOCAT_IMAGE_NAME, command=f'{docker_registry_port}')

    _ensure_socat_running()


def stop():
    socat_container = get()
    if socat_container:
        socat_container.stop()