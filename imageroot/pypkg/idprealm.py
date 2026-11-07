#
# Copyright (C) 2026 Nethesis S.r.l.
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Keycloak realms of NS8 user domains, and OIDC clients of NS8 modules.

A realm is named after its user domain. Its users and groups come from
a read-only LDAP federation through ldapproxy. Every OIDC client is
owned by an NS8 module: the client ID is the module ID.
"""

import contextlib
import json
import os
import secrets
import subprocess
import sys
import urllib.parse

import agent
import agent.ldapproxy
import idpcert
import kcadmin

LDAP_COMPONENT_NAME = "ns8-ldap"
GROUP_MAPPER_NAME = "groups"
LDAP_UUID_SCOPE = "ldap_uuid"
# Client attribute recording the owner module of a client
MODULE_ATTRIBUTE = "ns8.module_id"
ACCESS_TOKEN_LIFESPAN = "access.token.lifespan"
# Default of optional client settings that are kept when not given
KEEP = object()
# ldapproxy listens on the node VPN address, reachable from the pod
LDAPPROXY_HOST = "cluster-localnode"

def fail_validation(parameter, value, error):
    """Abort the action with a validation error of one parameter."""
    agent.set_status("validation-failed")
    json.dump([{
        "field": parameter,
        "parameter": parameter,
        "value": value,
        "error": error,
    }], fp=sys.stdout)
    sys.exit(2)

@contextlib.contextmanager
def realms_lock():
    """Serialize the changes to realms and to the domain binding of the
    module: the binding is replaced as a whole."""
    with agent.exclusive_file_lock("realms"):
        yield

def _bound_domains():
    # Read the leader: a replica could miss a binding just changed
    return agent.get_bound_domain_list(agent.redis_connect())

def bind_domain(domain):
    """Add a user domain to the bound domains of the module. Call it
    with realms_lock() held."""
    bound_domains = _bound_domains()
    if domain not in bound_domains:
        agent.bind_user_domains(bound_domains + [domain], check=True)

def unbind_domain(domain):
    """Remove a user domain from the bound domains of the module. Call
    it with realms_lock() held."""
    bound_domains = _bound_domains()
    if domain in bound_domains:
        agent.bind_user_domains([d for d in bound_domains if d != domain], check=True)

def issuer_url(realm):
    return f"https://{os.environ['IDP_HOSTNAME']}/realms/{realm}"

def require_keycloak():
    """Exit with an error if Keycloak is not running."""
    if subprocess.run(["systemctl", "--user", "-q", "is-active", "keycloak.service"]).returncode != 0:
        print(agent.SD_ERR + "keycloak.service is not active", file=sys.stderr)
        sys.exit(1)

def ldap_component_config(domain):
    """Return the LDAP federation settings of a user domain, as
    component config of Keycloak. Return None if the domain does not
    exist."""
    lp = agent.ldapproxy.Ldapproxy()
    ldom = lp.get_domain(domain)
    if not ldom:
        return None
    users_clause = lp.get_ldap_users_search_filter_clause(domain)
    config = {
        "enabled": ["true"],
        "editMode": ["READ_ONLY"],
        "connectionUrl": [f"ldap://{LDAPPROXY_HOST}:{ldom['port']}"],
        "authType": ["simple"],
        "bindDn": [ldom["bind_dn"]],
        "bindCredential": [ldom["bind_password"]],
        "importEnabled": ["true"],
        "syncRegistrations": ["false"],
        "trustEmail": ["true"],
        "useTruststoreSpi": ["never"],
        "connectionPooling": ["true"],
    }
    if ldom["schema"] == "ad":
        config.update({
            "vendor": ["ad"],
            "usersDn": [ldom["base_dn"]],
            "searchScope": ["2"],
            "usernameLDAPAttribute": ["sAMAccountName"],
            "rdnLDAPAttribute": ["cn"],
            "uuidLDAPAttribute": ["objectGUID"],
            "userObjectClasses": ["person, organizationalPerson, user"],
            "customUserSearchFilter": [f"(&(objectCategory=person){users_clause})"],
            "pagination": ["true"],
        })
    else:
        config.update({
            "vendor": ["other"],
            "usersDn": [f"ou=People,{ldom['base_dn']}"],
            "searchScope": ["1"],
            "usernameLDAPAttribute": ["uid"],
            "rdnLDAPAttribute": ["uid"],
            "uuidLDAPAttribute": ["entryUUID"],
            "userObjectClasses": ["inetOrgPerson, posixAccount"],
            "customUserSearchFilter": [users_clause],
            "pagination": ["false"],
        })
    return config

def group_mapper_config(domain):
    lp = agent.ldapproxy.Ldapproxy()
    ldom = lp.get_domain(domain)
    config = {
        "group.name.ldap.attribute": ["cn"],
        "groups.ldap.filter": [lp.get_ldap_groups_search_filter_clause(domain)],
        "preserve.group.inheritance": ["false"],
        "mode": ["LDAP_ONLY"],
        "groups.path": ["/"],
        "user.roles.retrieve.strategy": ["LOAD_GROUPS_BY_MEMBER_ATTRIBUTE"],
        "drop.non.existing.groups.during.sync": ["false"],
    }
    if ldom["schema"] == "ad":
        config.update({
            "groups.dn": [ldom["base_dn"]],
            "group.object.classes": ["group"],
            "membership.ldap.attribute": ["member"],
            "membership.attribute.type": ["DN"],
            "membership.user.ldap.attribute": ["cn"],
        })
    else:
        config.update({
            "groups.dn": [f"ou=Groups,{ldom['base_dn']}"],
            "group.object.classes": ["posixGroup"],
            "membership.ldap.attribute": ["memberUid"],
            "membership.attribute.type": ["UID"],
            "membership.user.ldap.attribute": ["uid"],
        })
    return config

def ldap_uuid_mapper(schema):
    """The ldap_uuid claim exposes the LDAP_ID user attribute, the
    account key of applications that read LDAP. AD applications, like
    Nextcloud, use the objectGUID string in uppercase."""
    config = {
        "claim.name": "ldap_uuid",
        "jsonType.label": "String",
        "id.token.claim": "true",
        "access.token.claim": "true",
        "userinfo.token.claim": "true",
        "introspection.token.claim": "true",
    }
    if schema == "ad":
        mapper_type = "script-ldap-id-upper.js"
        config["multivalued"] = "false"
    else:
        mapper_type = "oidc-usermodel-attribute-mapper"
        config["user.attribute"] = "LDAP_ID"
    return {
        "name": "ldap_uuid",
        "protocol": "openid-connect",
        "protocolMapper": mapper_type,
        "config": config,
    }

def _find_component(kc, realm, parent_id, provider_type, name):
    for rep in kc.get(f"/{realm}/components", params={"parent": parent_id, "type": provider_type}):
        if rep["name"] == name:
            return rep
    return None

def ensure_realm(kc, domain):
    """Create the realm of a user domain if it does not exist, then
    apply its LDAP federation settings."""
    if domain not in kcadmin.managed_realms(kc):
        print(f"Creating realm {domain}", file=sys.stderr)
        kc.post("", {
            "realm": domain,
            "displayName": domain,
            "enabled": True,
            "registrationAllowed": False,
        })
        # The realm creator gets the admin roles of the new realm: renew
        # the token to use them
        kc.renew_token()
        ensure_ldap_uuid_scope(kc, domain)
    ensure_federation(kc, domain)

def ensure_federation(kc, domain):
    """Create or update the LDAP federation of the realm, from the
    current user domain settings. The bind password and the ldapproxy
    port may change over time."""
    config = ldap_component_config(domain)
    if config is None:
        raise ValueError(f"user domain {domain} not found")
    realm_id = kc.get(f"/{domain}")["id"]
    storage_type = "org.keycloak.storage.UserStorageProvider"
    component = _find_component(kc, domain, realm_id, storage_type, LDAP_COMPONENT_NAME)
    if component is None:
        print(f"Creating the LDAP federation of realm {domain}", file=sys.stderr)
        kc.post(f"/{domain}/components", {
            "name": LDAP_COMPONENT_NAME,
            "providerId": "ldap",
            "providerType": storage_type,
            "parentId": realm_id,
            "config": config,
        })
        component = _find_component(kc, domain, realm_id, storage_type, LDAP_COMPONENT_NAME)
    else:
        component["config"].update(config)
        kc.put(f"/{domain}/components/{component['id']}", component)

    _ensure_mapper(kc, domain, component["id"], GROUP_MAPPER_NAME, "group-ldap-mapper",
                   group_mapper_config(domain))
    _ensure_mapper(kc, domain, component["id"], idpcert.ACCOUNT_MAPPER, "user-attribute-ldap-mapper",
                   idpcert.account_state_mapper_config(config["vendor"] == ["ad"]))

def _ensure_mapper(kc, domain, parent_id, name, provider_id, config):
    mapper_type = "org.keycloak.storage.ldap.mappers.LDAPStorageMapper"
    mapper = _find_component(kc, domain, parent_id, mapper_type, name)
    if mapper is None:
        kc.post(f"/{domain}/components", {
            "name": name,
            "providerId": provider_id,
            "providerType": mapper_type,
            "parentId": parent_id,
            "config": config,
        })
    else:
        mapper["config"].update(config)
        kc.put(f"/{domain}/components/{mapper['id']}", mapper)

def ensure_ldap_uuid_scope(kc, domain):
    """Add the ldap_uuid claim to every client of the realm, with a
    default client scope."""
    lp = agent.ldapproxy.Ldapproxy()
    schema = lp.get_domain(domain)["schema"]
    location = kc.post(f"/{domain}/client-scopes", {
        "name": LDAP_UUID_SCOPE,
        "protocol": "openid-connect",
        "attributes": {"include.in.token.scope": "false"},
        "protocolMappers": [ldap_uuid_mapper(schema)],
    })
    scope_id = location.rstrip("/").rsplit("/", 1)[-1]
    kc.put(f"/{domain}/default-default-client-scopes/{scope_id}")

def default_post_logout_redirect_uris(redirect_uris):
    """Return a wildcard URI for each origin of the redirect URIs, like
    https://cloud.example.org/*: a fallback for applications that do not
    pass their exact logout URIs."""
    origins = []
    for uri in redirect_uris:
        parts = urllib.parse.urlsplit(uri)
        origin = f"{parts.scheme}://{parts.netloc}/*"
        if parts.scheme and parts.netloc and origin not in origins:
            origins.append(origin)
    return origins

def validate_client_endpoints(redirect_uris, logout_uris, web_origins, audience):
    """Keep exact native callbacks and HTTPS endpoints; never host wildcards.
    A logout path may end in /* for compatibility with the upstream fallback.
    """
    import ipaddress
    import re
    def check(uri, logout=False):
        if not isinstance(uri, str) or any(c.isspace() or ord(c) < 32 for c in uri):
            raise ValueError('invalid_client_uri')
        url = urllib.parse.urlsplit(uri)
        if not url.scheme or url.fragment or url.username or url.password:
            raise ValueError('invalid_client_uri')
        if '*' in uri and not (logout and url.path.endswith('/*') and uri.count('*') == 1):
            raise ValueError('wildcard_client_uri')
        if url.scheme in ('https', 'http'):
            if not url.hostname or '*' in url.netloc:
                raise ValueError('invalid_client_host')
            try:
                loopback = ipaddress.ip_address(url.hostname).is_loopback
            except ValueError:
                loopback = url.hostname == 'localhost'
            if url.scheme == 'http' and not loopback:
                raise ValueError('https_client_uri_required')
            try:
                url.port
            except ValueError:
                raise ValueError('invalid_client_port') from None
        elif url.scheme in ('javascript', 'data', 'file', 'blob', 'about', 'ftp') or not (url.netloc or url.path):
            raise ValueError('invalid_native_callback')
        return url
    for uri in redirect_uris:
        check(uri)
    for uri in logout_uris:
        check(uri, logout=True)
    for origin in web_origins:
        if origin == '+':
            continue  # Keycloak derives origins from validated callbacks.
        url = check(origin)
        if url.scheme not in ('https', 'http') or url.path or url.query:
            raise ValueError('exact_web_origin_required')
    for target in audience:
        if (not isinstance(target, str) or not re.fullmatch(r'[a-zA-Z0-9_.-]+', target)
                or target in ('admin-cli', 'security-admin-console', 'realm-management', 'account', 'account-console')):
            raise ValueError('invalid_client_audience')

def ensure_client(kc, realm, module_id, redirect_uris=(), post_logout_redirect_uris=(),
        web_origins=(), audience=(), rotate_secret=False, access_token_lifespan=KEEP, access_required=False, expected_access_group=KEEP):
    """Create or update the OIDC client of a module, and return its
    secret. The secret is generated on creation, and when rotate_secret
    is set. The access token lifespan, in seconds, is kept unless given;
    None restores the realm default."""
    validate_client_endpoints(redirect_uris, post_logout_redirect_uris, web_origins, audience)
    rep = {
        "clientId": module_id,
        "name": module_id,
        "protocol": "openid-connect",
        "publicClient": False,
        "clientAuthenticatorType": "client-secret",
        # A client without redirect URIs authenticates only its own
        # requests, for example token introspection
        "standardFlowEnabled": bool(redirect_uris),
        "implicitFlowEnabled": False,
        "directAccessGrantsEnabled": False,
        "serviceAccountsEnabled": False,
        "redirectUris": list(redirect_uris),
        "webOrigins": list(web_origins),
        "attributes": {
            MODULE_ATTRIBUTE: module_id,
            "post.logout.redirect.uris": "##".join(post_logout_redirect_uris),
        },
        "protocolMappers": [audience_mapper(client_id) for client_id in audience],
    }
    if access_required:
        rep["attributes"]["ns8.access_required"] = "true"
    if expected_access_group is not KEEP:
        if not access_required:
            raise ValueError("expected_access_group_requires_access_required")
        import idpaccess
        expected = idpaccess.find_group(kc, realm, expected_access_group)
        rep["attributes"][idpaccess.EXPECTED_GROUP] = expected["id"]
        rep["attributes"][idpaccess.EXPECTED_SOURCE] = "consumer"
    if access_token_lifespan is not KEEP:
        # An empty value removes the attribute
        rep["attributes"][ACCESS_TOKEN_LIFESPAN] = str(access_token_lifespan or "")
    current = kc.find_client(realm, module_id)
    if access_required or (current and current.get("attributes", {}).get("ns8.access_required") == "true"):
        import idpaccess
        idpaccess.ensure_required_action(kc, realm)
        if current is None:
            rep["protocolMappers"].append({
                "name": idpaccess.TOKEN_GATE_NAME, "protocol": "openid-connect",
                "protocolMapper": idpaccess.TOKEN_GATE, "config": {},
            })
        else:
            idpaccess._ensure_token_gate(kc, realm, current)
    if current is None:
        print(f"Creating client {module_id} in realm {realm}", file=sys.stderr)
        rep["secret"] = secrets.token_urlsafe(32)
        kc.post(f"/{realm}/clients", rep)
        return rep["secret"]

    print(f"Updating client {module_id} in realm {realm}", file=sys.stderr)
    # Protocol mappers are not updated by a client update: replace the
    # audience mappers separately
    mappers = rep.pop("protocolMappers")
    if access_required and expected_access_group is KEEP and current.get("attributes", {}).get("ns8.access_required") != "true":
        # Pin the already approved group on first activation, never repin
        # a changed/missing policy during subsequent registrations.
        approved = current.get("attributes", {}).get("ns8.access_group_id")
        if approved:
            rep["attributes"]["ns8.access_expected_group_id"] = approved
    current.setdefault("attributes", {}).update(rep.pop("attributes"))
    current.update(rep)
    current.pop("protocolMappers", None)
    current.pop("secret", None)
    kc.put(f"/{realm}/clients/{current['id']}", current)
    models = f"/{realm}/clients/{current['id']}/protocol-mappers/models"
    for mapper in kc.get(models):
        if mapper["protocolMapper"] == "oidc-audience-mapper":
            kc.delete(f"{models}/{mapper['id']}")
    for mapper in mappers:
        kc.post(models, mapper)
    secret_path = f"/{realm}/clients/{current['id']}/client-secret"
    if rotate_secret:
        print(f"Rotating the secret of client {module_id}", file=sys.stderr)
        return kc.post(secret_path)["value"]
    return kc.get(secret_path)["value"]

def audience_mapper(client_id):
    """Add a client to the token audience. For example, Dovecot accepts
    a token only if its client is in the audience."""
    return {
        "name": f"aud-{client_id}",
        "protocol": "openid-connect",
        "protocolMapper": "oidc-audience-mapper",
        "config": {
            "included.client.audience": client_id,
            "access.token.claim": "true",
            "id.token.claim": "false",
            "introspection.token.claim": "true",
        },
    }

def module_clients(kc, realm):
    """Return the clients of the realm owned by NS8 modules."""
    return [rep for rep in kc.get(f"/{realm}/clients")
        if rep.get("attributes", {}).get(MODULE_ATTRIBUTE)]
