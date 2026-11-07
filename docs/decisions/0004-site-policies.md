# 0004: Site policies as module settings

Date: 2026-10-31. User request: changes that only this deployment needs must be
switchable in the module settings, so the upstream module stays generally usable.

## Decision

`configure-module` accepts four booleans, stored in the module environment. An
omitted field keeps its value, and `get-configuration` reports all of them.

| Setting | On | Off |
|---|---|---|
| `restrict_admin_console` | `/admin` route limited to the node | no extra route, console on the host name |
| `directory_groups_only` | group mapper `LDAP_ONLY` | group mapper `READ_ONLY` |
| `account_home_redirect` | welcome theme `ns8` | Keycloak default, root leads to `/admin/` |
| `strict_client_uris` | `validate_client_endpoints` at registration | no extra validation |

This module defaults all four to on, so existing installations keep their
behavior. Only `DEFAULTS` in `idpsettings.py` and `IDP_WELCOME_THEME` in
`keycloak.service` hold this choice; an upstream build sets them to off.

Not switchable, because they are optional already: client access rules and token
lifespan (per client), certificate sign-in (per realm). Not switchable, because
they are fixes: realm lock, start budget, leader reads, Let's Encrypt on update.

## Failure behavior

Disabling `directory_groups_only` is refused while a client has an access rule.
The refusal is a convenience: with a stopped Keycloak nothing is checked, and the
access gate denies sign-ins without `LDAP_ONLY` either way. New rules are refused
in that state too, with the existing `ldap_group_mapper_not_found` error.

`strict_client_uris` applies to new registrations and does not revoke endpoints
of existing clients. A disabled restriction removes the `/admin` route, and
`certificate_transport` then manages the host route alone.
