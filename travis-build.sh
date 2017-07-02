#! /bin/sh
# vim:set sw=8 ts=8 noet:

set -e

printf 'travis_fold:start:build\r'
printf '>>> Building.\n\n'
make DOCKER_TAG="$TRAVIS_COMMIT" build
printf 'travis_fold:end:build\r'

# If this is a release, push the Docker image to Docker Hub.
if [ "$TRAVIS_PULL_REQUEST" = "false" -a -n "$TRAVIS_TAG" ]; then
	printf 'travis_fold:start:release\r'
	printf '>>> Creating release.\n\n'
	docker login -u $DOCKER_USERNAME -p $DOCKER_PASSWORD
	docker tag torchbox/kube-ldap-authn:$TRAVIS_COMMIT \
		torchbox/kube-ldap-authn:$TRAVIS_TAG
	docker push torchbox/kube-ldap-authn:$TRAVIS_TAG
	printf 'travis_fold:end:release\r'
fi
