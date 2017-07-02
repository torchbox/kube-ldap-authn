# vim:set ts=8 sw=8 noet:
#
# Copyright (c) 2016-2017 Torchbox Ltd.
#
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely. This software is provided 'as-is', without any express or implied
# warranty.

DOCKER_REPOSITORY	= torchbox/kube-ldap-authn
DOCKER_TAG		?= latest
DOCKER_IMAGE		?= ${DOCKER_REPOSITORY}:${DOCKER_TAG}

build:
	docker build -t ${DOCKER_IMAGE} .

push:
	docker push ${DOCKER_IMAGE}
