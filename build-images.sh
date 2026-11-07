#!/bin/bash

#
# Copyright (C) 2023 Nethesis S.r.l.
# SPDX-License-Identifier: GPL-3.0-or-later
#

# Terminate on error
set -e

# Prepare variables for later use
images=()
# The image will be pushed to GitHub container registry
repobase="${REPOBASE:-ghcr.io/platypuschan}"
# Configure the image name
reponame="idp-reworked"

# Create a new empty container image
container=$(buildah from scratch)

# Use the production recipe's builder, never a stale container from an older Node.
node_image=$(awk '$1 == "FROM" && $4 == "ui" {print $2; exit}' Containerfile)
test -n "${node_image}"
nodebuilder=$(buildah from -v "${PWD}:/usr/src:Z" "${node_image}")
trap 'buildah rm "${nodebuilder}" >/dev/null' EXIT

echo "Build static UI files with node..."
buildah run \
    --workingdir=/usr/src/ui \
    --env="NODE_OPTIONS=--openssl-legacy-provider" \
    "${nodebuilder}" \
    sh ./build.sh

# Build the Keycloak image, with the NS8 providers built in
echo "Building the Keycloak image..."
buildah build --force-rm --layers --jobs=0 \
    --file keycloak-providers/Containerfile \
    --tag "${repobase}/idp-reworked-keycloak" \
    keycloak-providers
images+=("${repobase}/idp-reworked-keycloak")

# Add imageroot directory to the container image
buildah add "${container}" imageroot /imageroot
buildah add "${container}" ui/dist /ui
# Setup the entrypoint, ask to reserve one TCP port with the label and set a rootless container
buildah config --entrypoint=/ \
    --label="org.opencontainers.image.source=https://github.com/Platypuschan/ns8-idp-reworked" \
    --label="org.nethserver.authorizations=traefik@node:routeadm samba@any:domadm openldap@any:domadm cluster:accountconsumer" \
    --label="org.nethserver.tcp-ports-demand=1" \
    --label="org.nethserver.rootfull=0" \
    --label="org.nethserver.images=${repobase}/idp-reworked-keycloak:${IMAGETAG:-latest} docker.io/library/postgres:18.6-trixie" \
    "${container}"
# Commit the image
buildah commit "${container}" "${repobase}/${reponame}"

# Append the image URL to the images array
images+=("${repobase}/${reponame}")

#
# NOTICE:
#
# It is possible to build and publish multiple images.
#
# 1. create another buildah container
# 2. add things to it and commit it
# 3. append the image url to the images array
#

#
# Setup CI when pushing to Github. 
# Warning! docker::// protocol expects lowercase letters (,,)
if [[ -n "${CI}" ]]; then
    # Set output value for Github Actions
    printf "images=%s\n" "${images[*],,}" >> "${GITHUB_OUTPUT}"
else
    # Just print info for manual push
    printf "Publish the images with:\n\n"
    for image in "${images[@],,}"; do printf "  buildah push %s docker://%s:%s\n" "${image}" "${image}" "${IMAGETAG:-latest}" ; done
    printf "\n"
fi
