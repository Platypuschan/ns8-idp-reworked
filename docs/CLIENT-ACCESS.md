# Client access draft: design and validation

The optional policy is implemented by a required action and a token mapper
in the existing `ns8-authenticators` JAR. No browser flow is copied or
rewritten. A per-client browser-flow copy was rejected because realm changes
would not propagate and broker authentication bypasses that flow. A wrapper
that references the realm flow was rejected because Keycloak recursively
deletes referenced subflows. Realm-wide LDAP NO_CACHE was rejected because
it would affect unrelated clients.

This ports the reviewed Vaultwarden prototype to the regular ns8-idp layout.
Overlay images, separate grant scripts and first-prototype migration are
excluded. The general realm-lock fix is submitted separately in
[NethServer/ns8-idp#15](https://github.com/NethServer/ns8-idp/pull/15).
Until that lands, this draft also needs those same two critical sections;
merge #15 first. Fixed token claims in #4 remain an independent feature and
will need a registration/mapper compatibility check if combined.

## Reproduce

Use Python 3 with requests/jsonschema, Podman and a Linux host capable of
running its containers. Tests use ephemeral test networks, random credentials
and loopback ports; they do not access a production installation.

```sh
python3 -m unittest discover -s tests -p test_client_access.py -v
python3 -m unittest discover -s tests -p test_realm_lock.py -v
podman build -f tests/client-access/Samba.Containerfile -t localhost/ns8-vaultwarden-test-samba tests/client-access
podman build -f tests/client-access/Containerfile -t localhost/ns8-idp-client-access-test .
python3 tests/client-access/run.py
python3 tests/client-access/check_failures.py
```

`run.py` covers allowed/denied and unrestricted clients, cached membership
revocation/regrant, SSO-cookie reuse, code/refresh denial, LDAP failure,
restart, policy removal/reapplication, reconciliation and client
deletion/re-registration, real token lifespan, the removal of federated
IdPs of 0.1.0-rc.1 realms, SAML logins (SP- and IdP-initiated, with an SSO
cookie), and the device grant and standard token exchange switched on again
in the console. `check_failures.py` covers failures at each step of a policy
change (the client is never disabled), grant-flag diagnostics, token
default/reset, local-only accounts, direct/nested/deleted groups and the
live status check against real Keycloak and Samba AD.

The required action relies on Keycloak's trigger evaluation at completed
authentication, the LDAP failure check uses
`StorageUnavailableUserModelDelegate` (not a stable public API), and the
live user check uses the admin example-token endpoint. Revalidate these
paths on Keycloak updates. The security work branch uses 26.8.1 for both the provider compile target
and runtime. See [ADR 0002](decisions/0002-security-decisions.md).

Decisions: [ADR 0001](decisions/0001-client-access-hardening.md).

## Remaining before general release

- Decide whether client authorization belongs here or in applications, and
  review the LDAP workload caused by targeted eviction.
- Validate upgrade, backup/restore, complete existing NS8 realm/federation
  suites, alternative LDAP schemas and future MFA compatibility.
- The Access page was built and linted, not tried in a browser on NS8.

No production deployment, physical mobile app or complete feature/upgrade
compatibility is claimed.
