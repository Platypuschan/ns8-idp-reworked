# ns8-idp-reworked

Vorbereitete Vorabversion **0.1.0-rc.6**; zuletzt veröffentlicht ist **0.1.0-rc.5**. Eigenständiges angepasstes Modul mit optionaler Client-Gruppenregel, einstellbar auf der Seite **Zugriff**, optionaler Tokenlaufzeit und optionaler [Anmeldung mit Gerätezertifikat](docs/CERTIFICATES.md); keine externen Identitätsanbieter; kein Stable-/Katalogrelease.

[Prüfnachweise und Image-Digests](docs/RELEASE-0.1.0-rc.5.md) ([0.1.0-rc.3](docs/RELEASE-0.1.0-rc.3.md), [0.1.0-rc.2](docs/RELEASE-0.1.0-rc.2.md), [0.1.0-rc.1](docs/RELEASE-0.1.0-rc.1.md)) · [Release-Ablauf](docs/PRERELEASE.md) · [Gitea-SSO-Prüfung](docs/GITEA-SSO.md)

Single sign-on for NethServer 8 applications, based on Keycloak

## Install

Install the module (application) on cluster node 1:

    add-module ghcr.io/platypuschan/idp-reworked:0.1.0-rc.5 1

The output of the command will return the module identifier:
Output example:

    {"module_id": "idp-reworked1", "image_name": "idp-reworked", "image_url": "ghcr.io/platypuschan/idp-reworked:0.1.0-rc.5"}

## Configure

Set the host name of the identity provider, and optionally request a
Let's Encrypt certificate for it:

    api-cli run module/idp-reworked1/configure-module --data '{"host": "sso.example.org", "lets_encrypt": true}'

The whole host name is routed to Keycloak. The action fails if the host
name is already used by another application, or if the Let's Encrypt
certificate cannot be obtained: in both cases the previous configuration
is kept.

Read the current configuration:

    api-cli run module/idp-reworked1/get-configuration

The host root, `https://sso.example.org/`, leads the users to the
account console of their user domain,
`https://sso.example.org/realms/<user domain>/account/`, where they
log in with their domain account. This works when the module has exactly
one enabled realm. With no realm, or more than one, the host root shows
a neutral page that asks to sign in from the application: no public page
lists the user domains, and the Administration Console is reachable only
from the node. The account console of each realm is always reachable at
its own URL.

## Register an application

An application module registers its OIDC client in the realm of its
user domain with the `register-client` action. The module image must
declare the `clientadm` role in its authorizations label:

    org.nethserver.authorizations=idp-reworked@any:clientadm

The client ID is the module ID. For example, the module agent of
`nextcloud1`, bound to the `dp.example.org` user domain, calls:

```python
response = agent.tasks.run(agent_id="module/idp-reworked1", action="register-client", data={
    "domain": "dp.example.org",
    "redirect_uris": ["https://cloud.example.org/apps/user_oidc/code"],
    "post_logout_redirect_uris": ["https://cloud.example.org/"],
})
agent.assert_exp(response["exit_code"] == 0)
# {"client_id": "nextcloud1", "client_secret": "...", "realm": "dp.example.org",
#  "issuer": "https://sso.example.org/realms/dp.example.org"}
```

Pass the exact URIs where the application logout returns the user in
`post_logout_redirect_uris`: Keycloak refuses any other one with an
"Invalid redirect uri" page. Without the attribute, `register-client`
allows a wildcard URI for each origin of the redirect URIs, like
`https://cloud.example.org/*`, as a fallback.

The same call updates an existing client and returns its current secret;
add `"rotate_secret": true` to generate a new one. A client without
redirect URIs can only authenticate its own requests, for example token
introspection. The `audience` attribute adds other client IDs to the
token audience, for example the mail module whose Dovecot introspects the
tokens. See the action input schema for all attributes.

Applications discover the OIDC providers of the cluster with
`agent.list_service_providers(rdb, "oidc")`. Each idp instance publishes
`module/{MODULE_ID}/srv/http/oidc`, and raises the
`service-oidc-changed` event when it changes. The record fields are:

- `host`: the host name of the provider;
- `issuer_url_prefix`: the issuer of a user domain is this prefix
  followed by the domain name, for example
  `https://sso.example.org/realms/dp.example.org`.

The event payload carries the record fields, so listeners can tell
whether the change concerns them, besides the record key and the
provider module:

```json
{
    "host": "sso.example.org",
    "issuer_url_prefix": "https://sso.example.org/realms/",
    "key": "module/idp-reworked1/srv/http/oidc",
    "module_id": "idp1",
    "module_uuid": "8d257122-0a7f-49c7-a620-08961a68cfa0"
}
```

Any module publishing the `oidc` service is expected to implement the
`register-client` action and the `clientadm` role as described here.

## Client group access

An administrator can restrict the OIDC client of an NS8 module to the
**direct** members of one group of its user domain. In the UI, open the
**Access** page of the idp, choose the group of the application and save;
**Check** runs the live check described below. With the API:

```sh
api-cli run module/idp-reworked1/alter-realm-client --data '{"domain":"ad.example.org","client_id":"vaultwarden1","access_group":"services_vaultwarden"}'
```

Omitting `access_group` preserves the policy; `null` removes it. Client
re-registration preserves both the policy and an administrator-disabled
state. Only administrators can set the policy. `list-realms` also reports
`access_group`.

The required action checks membership at password and SSO-cookie logins,
with any protocol: SAML logins of a client with the policy are denied too.
The protocol mapper checks code redemption, refresh, token exchange and
userinfo. The check evicts only the authenticating user's shared cache
entry, reloads LDAP membership, and denies access on directory failure. The
federation's cache policy and the realm login flows are preserved. Nested
membership is not supported.

Applying the policy switches off the implicit flow, direct grants, service
accounts, the device grant, CIBA and standard token exchange of the client.
If an administrator switches one on again in the Keycloak console, it is
reported as an issue; device logins and token exchanges of non-members are
still denied. Tokens already issued and application sessions keep their own
expiry: an application can end them itself, like the Vaultwarden module
does.

Setting a policy never disables the client. Clients registered with `access_required:true` also deny access when their
policy is removed or differs from the pinned group. For optional clients,
the checks act only on clients with the policy attribute, so the required action and the token mapper are
put in place first, and one client update then sets the policy: a failure
leaves the client as it was, unrestricted, or restricted already. Trying
again completes it.

### Client access status

A module with the `clientadm` role can read only its own policy:

```python
response = agent.tasks.run(agent_id="module/idp-reworked1", action="get-client-access",
    data={"domain": "ad.example.org", "live": True})
```

Administrators, in the UI or with `api-cli`, supply `client_id`. The
response contains `enforced`, `enabled`, `group`, `group_path` and
`issues`: `enforced` means that every part of the policy is configured.
With `"live": true` it also contains `live`:

- `ldap_connection`: Keycloak binds to LDAP with the federation settings;
- `group_in_ldap`: the group still exists in the user domain. A group
  removed from LDAP stays imported in Keycloak, so `enforced` stays true,
  while nobody can sign in;
- `user_allowed`: only for administrators, with `"user": "<name>"`: the
  user passes the token check now. It runs the token mapper of the client
  with a Keycloak example token, without signing in;
- `ok` and `issues`: false and the reasons if any live check fails.

Startup and cluster-event reconciliation restore missing parts of the
policies. Removing a module removes its client; registration of a new
instance requires a new policy.

### Optional access-token lifetime

Independently of the group policy, `register-client` accepts
`access_token_lifespan`, an integer from 60 to 86400 seconds. Omission keeps
an existing override; `null` restores the realm default. For example, an
application with a 600-second session requirement can include:

```python
{"domain": "ad.example.org", "access_token_lifespan": 600}
```

See [client-access testing and remaining work](docs/CLIENT-ACCESS.md) for
reproducible tests and the limitations of this draft.

## No external identity providers

This module does not federate realms with external identity providers,
like Microsoft Entra ID: users and groups come only from the NS8 user
domain, read-only. Realms of earlier versions with federated IdPs are
cleaned up at the next Keycloak start: the IdPs created by the module,
its login flow copies and the writable LDAP federation are removed, and
the service account of the module is removed from the user domain.
Accounts created in LDAP by federated logins stay, without a password.
IdPs added with the Keycloak console are left alone.

## Uninstall

To uninstall the instance:

    remove-module --no-preserve idp1

## Design notes

The design study and the prototype results are in
[INSTRUCTIONS.md](INSTRUCTIONS.md). This section describes how the
module implements them.

### Services

Keycloak and PostgreSQL run in a Podman pod with its own network
namespace. The pod publishes only the Keycloak HTTP port, on the host
loopback interface (`127.0.0.1:${TCP_PORT}`), and Traefik routes the
configured host name to it. PostgreSQL listens on `127.0.0.1` inside the
pod and is not reachable from the node.

| Unit | Role |
|---|---|
| `idp.service` | The pod. The only enabled unit |
| `postgres.service` | PostgreSQL server |
| `keycloak-init.service` | One-shot job that creates the admin client of the module, see below |
| `keycloak.service` | Keycloak server |

The units start in this order, and every unit is bound to the pod.
`keycloak.service` requires the init job: if the job fails, Keycloak
does not start and the error is in the journal of the init job.

Both server units are `Type=notify`, so units ordered after them wait
until the server is really ready:

- PostgreSQL uses the Debian-based image, which is built with systemd
  support, and notifies readiness itself (`--sdnotify=container`).
- Keycloak is ready when a Podman health check on its `/health/ready`
  endpoint passes (`--sdnotify=healthy`). The probe is the
  `ns8-healthcheck` script of the Keycloak image; at startup it waits
  until Keycloak is ready, so it runs once instead of failing every few
  seconds. Later the check runs every 30 seconds: after 3 consecutive
  failures Podman kills the container, and systemd restarts it. The
  management port of the endpoint is not published by the pod.

The pod uses the Pasta network. Pasta delivers connections from the host
loopback interface to the pod with the host address as source, not
`127.0.0.1`, so:

- Keycloak accepts the proxy headers from any source. The Keycloak port
  is published only on the host loopback interface, so only local
  processes, like Traefik, can reach it.
- Every Keycloak server runs with the HTTPS host name
  (`--hostname=https://${IDP_HOSTNAME}`), otherwise the master realm
  refuses plain HTTP requests from a non-local address.

A Unix socket in a shared volume was considered for the database
connection, and discarded: the PostgreSQL JDBC driver has no native
Unix socket support yet, and the workaround needs a third-party library.

### Keycloak image

The module builds its own Keycloak image, `idp-keycloak`, from
[keycloak-providers/Containerfile](keycloak-providers/Containerfile).
The image contains the NS8 providers and the build-time options
(database, features, health endpoints, cache), so every Keycloak server
starts with `--optimized`, without rebuilding its configuration. The
final stage adds only the build output to the upstream layers.

Renovate updates the base image and the Keycloak dependencies of the
providers together, so the providers are always built against the
Keycloak version of the image.

Runtime options are environment variables (`KC_*`):
[imageroot/etc/keycloak.env](imageroot/etc/keycloak.env) is shipped with
the module, and `state/passwords.env`, created by `create-module` with
mode 0600, holds the database password.

The `ns8` welcome theme, selected by `KC_SPI_THEME__WELCOME_THEME`,
replaces the default redirect of the host root to the Administration
Console of the master realm, which has no users of the user domains. A
theme template cannot read the realms, so the page forwards to the
`ns8-home` realm resource (`/realms/master/ns8-home`, in the provider
jar), which redirects to the account console of the only enabled realm
besides master, or shows the neutral page.

### Module configuration

`configure-module` validates the host name, sets the Traefik route, and
only then saves `IDP_HOSTNAME` and restarts the services. When the route
cannot be set, for example because the Let's Encrypt certificate is not
obtained, Traefik keeps the previous route and the module settings are
not changed. The Let's Encrypt flag is stored only in the Traefik route,
and `get-configuration` reads it from there.

### Realms and clients

A realm is named after an NS8 user domain, and the idp can serve any
user domain of the cluster. `register-client` creates the realm when it
does not exist yet, and binds the idp to the user domain
(`cluster:accountconsumer`). A realm has:

- a read-only LDAP federation of the user domain, through ldapproxy at
  `cluster-localnode`, with the core filters for hidden users and
  groups, and a group mapper;
- the `ldap_uuid` default client scope: the claim carries the LDAP
  account key of the user (`entryUUID`, or `objectGUID` in uppercase for
  Active Directory, as Nextcloud expects).

The client owner is the calling module, read from `AGENT_TASK_USER`, and
it must be bound to the user domain of the realm. An explicit
`module_id` attribute is accepted only from tasks without a calling user,
like those submitted by the cluster agent or with `api-cli`.
Registrations are serialized with a lock, because the idp replaces its
user domain binding as a whole.

Administrators manage realms and clients with these actions, which
are not granted to the `clientadm` role:

- `list-realms`: the realms, with their state and the clients of NS8
  modules;
- `add-realm`: create the realm of a user domain before any client
  registers in it;
- `alter-realm`: enable or disable a realm. A disabled realm refuses the
  logins of all its clients;
- `alter-realm-client`: enable or disable the client of a module.
  `register-client` does not change this flag, so a module cannot enable
  its client again by registering it;
- `remove-realm`: remove a realm and unbind the idp from its user
  domain. A realm with clients is removed only with `"force": true`, and
  its modules must register them again.

The client secret is returned in the task output, which the core keeps
in Redis for a while, like the bind credentials of user domains.

### Keycloak administration

Actions, event handlers and helper scripts configure Keycloak through
its admin REST API, from the host. The `kcadmin` Python module
([imageroot/pypkg/kcadmin.py](imageroot/pypkg/kcadmin.py)) obtains tokens
with the `client_credentials` grant and wraps the API calls. `kcadm.sh`
is not used: it needs the same credentials, starts a JVM for every call,
and loses its session when the container is recreated.

The module authenticates as `ns8-agent`, a confidential client of the
master realm. Its secret is stored in `state/ns8-agent.json`, never in
Redis. The service account has only the `create-realm` role: Keycloak
grants it the admin roles of every realm it creates, so it manages
exactly the realms of the module and has no rights on the master realm.

The init job runs only when `state/ns8-agent.json` is missing, so the
same job covers the first start and credential recovery:

1. `kc.sh bootstrap-admin service` creates a temporary admin client
   directly in the database. Its exit code is not reliable, so the job
   checks the client credentials instead.
2. A temporary Keycloak server starts in the pod.
3. The temporary client creates `ns8-agent`, or resets its secret, and
   grants it the `create-realm` role and the admin roles of the existing
   realms, which a new client would not have.
4. The job checks the new credentials, saves them, deletes the temporary
   clients and stops the temporary server.

To recover lost credentials, remove `state/ns8-agent.json` and restart
`keycloak.service`.

### Reconciliation

[imageroot/bin/keycloak-post-start](imageroot/bin/keycloak-post-start)
applies the cluster configuration to every realm of the module:

- the LDAP federation follows the user domain settings, like the bind
  password and the ldapproxy port, and federated IdPs of earlier
  versions are removed;
- the client of a module is deleted when the module is no longer bound
  to the user domain of the realm, for example after its removal;
- the SMTP settings follow the node smarthost;
- the access policies of the clients are complete: the required action
  is enabled and every restricted client has its token mapper.

It runs after every Keycloak start, because events can be lost, and on
the `user-domain-changed`, `module-domain-changed`, `module-removed` and
`smarthost-changed` events when Keycloak is running.

### SMTP settings

Keycloak has no server-wide SMTP configuration: each realm has its own
settings, set by the reconciliation.

The sender address is `IDP_SMTP_FROM`, or `no-reply@${IDP_HOSTNAME}` when
unset. The TLS certificate verification setting has no realm equivalent.

### Updates

`update-module.d/80restart` restarts the running services, so an update
takes effect immediately: the core has already reloaded the unit files.
`update-module.d/20grants` adds the `clientadm` role to instances created
before it existed.

## Running tests locally

Site policies (admin console, group memberships, host root, client addresses) are switched on the Settings page, see [ADR 0004](docs/decisions/0004-site-policies.md).

Optional personal device certificate sign-in is documented in
[CERTIFICATES.md](docs/CERTIFICATES.md). It includes an administrator-only
enrollment/revocation page and requires the accompanying NS8 Traefik route API
extension; the stock proxy cannot enable the feature. The existing password
login and live LDAP group access policy remain available.

This module uses the NS8 standard testing infrastructure. For instructions on how to run the test suite locally, refer to the [Running tests locally](https://github.com/NethServer/ns8-github-actions/blob/v1/README.md#running-tests-locally) section of the ns8-github-actions README.

The `Realms` suite creates an OpenLDAP user domain, and simulates an
application module bound to it, because the core binds only the module
that calls `bind-user-domains`. Its Keycloak checks are in
[tests/kccheck.py](tests/kccheck.py), run in the idp module environment.

The suite runs in the two scenarios of the NS8 test workflow, selected
by the `SCENARIO` variable: `install` tests a new installation of the
module image, `update` installs the latest stable release and updates it
to the module image. The `update` scenario is skipped while no stable
release exists.

## UI translation

Translated with [Weblate](https://hosted.weblate.org/projects/ns8/).

To setup the translation process:

- add [GitHub Weblate app](https://docs.weblate.org/en/latest/admin/continuous.html#github-setup) to your repository
- add your repository to [hosted.weblate.org](https://hosted.weblate.org) or ask a NethServer developer to add it to ns8 Weblate project
