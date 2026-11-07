#
# Copyright (C) 2026 Nethesis S.r.l.
# SPDX-License-Identifier: GPL-3.0-or-later
#

"""Access policy of the clients: only the current members of one LDAP
group of the user domain may sign in to a client.

The NS8 Keycloak providers implement the checks, and both succeed for
clients without a policy:

- the "ns8-client-access" required action, enabled in the realm.
  Keycloak evaluates it whenever an authentication completes: password
  and SSO cookie logins alike. The realm flows are not changed;
- the "ns8-client-group-token-gate" protocol mapper of each restricted
  client: it refuses token issuance and refresh, for example the
  redemption of an authorization code issued before a group removal.

Both read the current memberships from LDAP: they evict the user from
the user cache before the check, so the cache of the LDAP federation
stays enabled for everything else. The policy is stored in client
attributes, and only administrators set it: a module can read the
policy of its own client, not change it.

The checks only act on clients with the policy attribute. So the
required action and the token gate are put in place first, and a single
client update then sets the attribute: a failure leaves the client
either unrestricted, as before, or restricted. It never disables the
client.
"""

import sys
import urllib.parse

POLICY = "ns8.access_policy"
POLICY_GROUP = "group"
GROUP_ID = "ns8.access_group_id"
GROUP_PATH = "ns8.access_group_path"
REQUIRED = "ns8.access_required"
EXPECTED_GROUP = "ns8.access_expected_group_id"
EXPECTED_SOURCE = "ns8.access_group_binding"

ACTION = "ns8-client-access"
ACTION_NAME = "NS8 client access group"
TOKEN_GATE = "ns8-client-group-token-gate"
TOKEN_GATE_NAME = "ns8 access group"

GROUP_MAPPER_TYPE = "org.keycloak.storage.ldap.mappers.LDAPStorageMapper"
STORAGE_TYPE = "org.keycloak.storage.UserStorageProvider"

# The checks cover browser logins and the tokens issued to users. Grants
# that issue tokens without a browser login of the user, or that skip
# the login form, are switched off by set_policy and reported if they
# are switched on again.
GRANT_FLAGS = ("directAccessGrantsEnabled", "implicitFlowEnabled", "serviceAccountsEnabled")
GRANT_ATTRIBUTES = {
    "oauth2.device.authorization.grant.enabled": "device_grant_set",
    "oidc.ciba.grant.enabled": "ciba_grant_set",
    "standard.token.exchange.enabled": "token_exchange_set",
}

class PolicyError(ValueError):
    """The policy cannot be applied: the reason is in the error code."""
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _path(name):
    return urllib.parse.quote(name, safe="")

#
# Required action
#

def _required_action(kc, realm):
    return next((a for a in kc.get(f"/{realm}/authentication/required-actions")
        if a.get("providerId") == ACTION), None)

def action_installed(kc, realm):
    if _required_action(kc, realm):
        return True
    return any(a.get("providerId") == ACTION
        for a in kc.get(f"/{realm}/authentication/unregistered-required-actions"))

def ensure_required_action(kc, realm):
    """Register and enable the required action in the realm."""
    action = _required_action(kc, realm)
    if action is None:
        print(f"Registering required action {ACTION} in realm {realm}", file=sys.stderr)
        kc.post(f"/{realm}/authentication/register-required-action", {"providerId": ACTION, "name": ACTION_NAME})
        action = _required_action(kc, realm)
    if not action["enabled"] or action.get("defaultAction"):
        action.update({"enabled": True, "defaultAction": False})
        kc.put(f"/{realm}/authentication/required-actions/{_path(action['alias'])}", action)

def required_action_enabled(kc, realm):
    action = _required_action(kc, realm)
    return bool(action and action["enabled"])

#
# LDAP groups
#

def group_mapper(kc, realm):
    """Return (storage, mapper): the read-only LDAP federation and its
    group mapper, if it reads the memberships from LDAP only. Otherwise
    raise PolicyError. LDAP_ONLY would write memberships to a writable
    federation."""
    storages = [c for c in kc.get(f"/{realm}/components", params={"type": STORAGE_TYPE})
        if c.get("providerId") == "ldap" and c.get("config", {}).get("editMode") == ["READ_ONLY"]]
    if len(storages) != 1:
        raise PolicyError("ldap_federation_not_found")
    mappers = [m for m in kc.get(f"/{realm}/components", params={"parent": storages[0]["id"], "type": GROUP_MAPPER_TYPE})
        if m.get("providerId") == "group-ldap-mapper"
        and m.get("config", {}).get("mode") == ["LDAP_ONLY"]
        and m.get("config", {}).get("groups.path", ["/"]) == ["/"]
        and m.get("config", {}).get("user.roles.retrieve.strategy") == ["LOAD_GROUPS_BY_MEMBER_ATTRIBUTE"]]
    if len(mappers) != 1:
        raise PolicyError("ldap_group_mapper_not_found")
    return storages[0], mappers[0]

def find_group(kc, realm, group):
    """Import the LDAP groups and return the representation of a group,
    by name, or raise PolicyError. Memberships are not imported: the
    checks read them from LDAP."""
    storage, mapper = group_mapper(kc, realm)
    kc.post(f"/{realm}/user-storage/{storage['id']}/mappers/{mapper['id']}/sync?direction=fedToKeycloak")
    try:
        return kc.get(f"/{realm}/group-by-path/{_path(group)}")
    except Exception:
        raise PolicyError("group_not_found") from None

#
# Policy of a client
#

def _token_gates(kc, realm, client):
    models = f"/{realm}/clients/{client['id']}/protocol-mappers/models"
    return [m for m in kc.get(models) if m.get("protocolMapper") == TOKEN_GATE]

def _ensure_token_gate(kc, realm, client):
    if not _token_gates(kc, realm, client):
        kc.post(f"/{realm}/clients/{client['id']}/protocol-mappers/models", {
            "name": TOKEN_GATE_NAME,
            "protocol": "openid-connect",
            "protocolMapper": TOKEN_GATE,
            "config": {},
        })

def restricted(client):
    return (client.get("attributes") or {}).get(POLICY) == POLICY_GROUP

def access_state(kc, realm, client):
    """Return the policy of a client. "enforced" is true only if every
    part of the policy is in place; "issues" lists the missing parts.
    It does not query LDAP: see live_state()."""
    attributes = client.get("attributes") or {}
    if not restricted(client):
        return {"enforced": False, "group": None, "group_path": None, "issues": ["required_policy_missing"] if attributes.get(REQUIRED) == "true" else []}
    state = {"enforced": False, "group": None, "group_path": attributes.get(GROUP_PATH) or None, "issues": []}
    issues = state["issues"]
    if attributes.get(REQUIRED) == "true" and attributes.get(EXPECTED_GROUP) != attributes.get(GROUP_ID):
        issues.append("expected_group_mismatch")
    try:
        group = kc.get(f"/{realm}/groups/{_path(attributes.get(GROUP_ID) or '-')}")
        state["group"] = group["name"]
        state["group_path"] = group["path"]
    except Exception:
        # For example the group was renamed or removed in LDAP: nobody
        # can sign in until the policy is set again
        issues.append("group_not_found")
    try:
        group_mapper(kc, realm)
    except PolicyError as ex:
        issues.append(ex.code)
    if not required_action_enabled(kc, realm):
        issues.append("required_action_disabled")
    if not _token_gates(kc, realm, client):
        issues.append("token_gate_missing")
    for flag in GRANT_FLAGS:
        if client.get(flag):
            issues.append(f"{flag}_set")
    for attribute, issue in GRANT_ATTRIBUTES.items():
        if attributes.get(attribute) == "true":
            issues.append(issue)
    overrides = client.get("authenticationFlowBindingOverrides") or {}
    if any(overrides.values()):
        # A private flow of the client could differ from the realm flow,
        # for example in the login mode
        issues.append("flow_override_set")
    state["enforced"] = not issues
    return state

def set_policy(kc, realm, client, group):
    """Restrict a client to the members of an LDAP group, by name, and
    return the policy state. Every check that can fail runs before the
    first change. The client keeps its enabled flag: the policy is set
    by a single client update, after the parts that enforce it."""
    if client.get("protocol", "openid-connect") != "openid-connect":
        raise PolicyError("protocol_not_supported")
    if not action_installed(kc, realm):
        raise PolicyError("provider_not_installed")
    group_rep = find_group(kc, realm, group)
    # Without the policy attribute both checks allow every user: put them
    # in place first
    ensure_required_action(kc, realm)
    _ensure_token_gate(kc, realm, client)
    client = kc.get(f"/{realm}/clients/{client['id']}")
    client.setdefault("attributes", {}).update({
        POLICY: POLICY_GROUP,
        GROUP_ID: group_rep["id"],
        GROUP_PATH: group_rep["path"],
    })
    if not client["attributes"].get(EXPECTED_GROUP) or client["attributes"].get(REQUIRED) != "true":
        client["attributes"][EXPECTED_GROUP] = group_rep["id"]
    client["attributes"].update({attribute: "false" for attribute in GRANT_ATTRIBUTES})
    client.update({flag: False for flag in GRANT_FLAGS})
    kc.put(f"/{realm}/clients/{client['id']}", client)
    state = access_state(kc, realm, kc.get(f"/{realm}/clients/{client['id']}"))
    if not state["enforced"]:
        # For example a concurrent change in the Keycloak console. The
        # client is restricted anyway: the required action denies the
        # logins of non-members
        print(f"Access policy of client {client['clientId']} is incomplete: {state['issues']}", file=sys.stderr)
        raise PolicyError("policy_incomplete")
    return state

#
# Live checks
#

# The masked value of a stored secret: Keycloak tests the connection
# with the bind password of the federation
MASKED_SECRET = "**********"

def _status(ex):
    return getattr(ex, "status", None)

def _ldap_connection(kc, realm):
    """Bind to LDAP with the stored settings of the federation. Return
    None on success, or an issue."""
    storages = [c for c in kc.get(f"/{realm}/components", params={"type": STORAGE_TYPE})
        if c.get("providerId") == "ldap"]
    if len(storages) != 1:
        return "ldap_federation_not_found"
    config = storages[0].get("config", {})
    first = lambda name, default="": (config.get(name) or [default])[0]
    try:
        kc.post(f"/{realm}/testLDAPConnection", {
            "action": "testAuthentication",
            "componentId": storages[0]["id"],
            "connectionUrl": first("connectionUrl"),
            "authType": first("authType", "simple"),
            "bindDn": first("bindDn"),
            "bindCredential": MASKED_SECRET,
            "useTruststoreSpi": first("useTruststoreSpi", "always"),
            "connectionTimeout": first("connectionTimeout"),
            "startTls": first("startTls", "false"),
        })
    except Exception as ex:
        print(f"LDAP connection test of realm {realm} failed: {ex}", file=sys.stderr)
        return "ldap_connection_failed"
    return None

def find_user(kc, realm, username):
    users = kc.get(f"/{realm}/users", params={"username": username, "exact": "true"})
    return next((u for u in users if u["username"].lower() == username.lower()), None)

def user_allowed(kc, realm, client, user):
    """Run the token gate of the client for a user, as at token
    issuance, without signing in: Keycloak builds an example access
    token. Return True or False, or raise the request error."""
    try:
        kc.get(f"/{realm}/clients/{client['id']}/evaluate-scopes/generate-example-access-token",
            params={"scope": "openid", "userId": user["id"]})
    except Exception as ex:
        if _status(ex) == 403 and "access_denied" in (getattr(ex, "body", "") or ""):
            return False
        raise
    return True

def live_state(kc, realm, client, group_exists, username=None):
    """Check the parts of a policy that access_state() cannot see:
    LDAP is reachable, the group still exists in LDAP, and optionally
    one user can sign in now. group_exists(name) looks the group up in
    the user domain. "ok" is true only if no issue is found: a user that
    is not allowed is a result, not an issue."""
    issues = []
    state = {"ldap_connection": None, "group_in_ldap": None, "user_allowed": None, "issues": issues}
    issue = _ldap_connection(kc, realm)
    state["ldap_connection"] = issue is None
    if issue:
        issues.append(issue)
    if restricted(client):
        attributes = client.get("attributes") or {}
        name = (attributes.get(GROUP_PATH) or "").rsplit("/", 1)[-1]
        try:
            group = kc.get(f"/{realm}/groups/{_path(attributes.get(GROUP_ID) or '-')}")
            name = group["name"]
        except Exception:
            pass
        if name and state["ldap_connection"]:
            try:
                state["group_in_ldap"] = bool(group_exists(name))
            except Exception as ex:
                print(f"LDAP lookup of group {name} failed: {ex}", file=sys.stderr)
                issues.append("group_lookup_failed")
            if state["group_in_ldap"] is False:
                issues.append("group_not_in_ldap")
    if username:
        user = find_user(kc, realm, username)
        if user is None:
            issues.append("user_not_found")
        else:
            try:
                state["user_allowed"] = user_allowed(kc, realm, client, user)
            except Exception as ex:
                print(f"Token check of user {username} failed: {ex}", file=sys.stderr)
                issues.append("user_check_failed")
    state["ok"] = not issues
    return state

def clear_policy(kc, realm, client):
    """Remove the access policy of a client.
    The required action stays registered: it does not restrict clients
    without a policy."""
    attributes = client.setdefault("attributes", {})
    names = (POLICY, GROUP_ID, GROUP_PATH)
    if attributes.get(REQUIRED) != "true":
        names += (EXPECTED_GROUP, EXPECTED_SOURCE)
    for name in names:
        if name in attributes:
            # An empty value removes the attribute
            attributes[name] = ""
    kc.put(f"/{realm}/clients/{client['id']}", client)
    if attributes.get(REQUIRED) == "true":
        return
    for mapper in _token_gates(kc, realm, client):
        kc.delete(f"/{realm}/clients/{client['id']}/protocol-mappers/models/{mapper['id']}")

#
# Reconciliation
#

def reconcile(kc, realm, clients):
    """Restore required actions and token gates without re-enabling clients."""
    if not action_installed(kc, realm):
        return
    restricted_clients = [c for c in clients if restricted(c) or (c.get("attributes") or {}).get(REQUIRED) == "true"]
    if restricted_clients:
        ensure_required_action(kc, realm)
    for client in restricted_clients:
        _ensure_token_gate(kc, realm, client)
