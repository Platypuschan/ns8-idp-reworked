FROM docker.io/library/node:24.22.1-slim AS ui
WORKDIR /src
ENV NODE_OPTIONS=--openssl-legacy-provider
COPY ui/ ./
RUN corepack enable && yarn install --immutable && yarn build
FROM scratch
COPY imageroot /imageroot
COPY --from=ui /src/dist /ui
ENTRYPOINT ["/"]
ARG KEYCLOAK_IMAGE
LABEL org.opencontainers.image.source="https://github.com/Platypuschan/ns8-idp-reworked" \
      org.nethserver.authorizations="traefik@node:routeadm samba@any:domadm openldap@any:domadm cluster:accountconsumer" \
      org.nethserver.tcp-ports-demand="1" \
      org.nethserver.rootfull="0" \
      org.nethserver.min-core="3.23.2" \
      org.nethserver.images="${KEYCLOAK_IMAGE} docker.io/library/postgres:18.6-trixie"
