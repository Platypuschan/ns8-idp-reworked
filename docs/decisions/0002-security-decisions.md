# 0002: Security decisions of 27 October 2026

Status: implemented on the security work branch; not released or deployed.
Source: user decisions P1–P21 in agent-exchange task
`20261027-codex-security-implementation`.

- P1: Keycloak runtime and provider compile target move together to 26.8.1.
  [Upstream release](https://www.keycloak.org/2026/10/keycloak-2681-released).
- P4: the NS8 UI/actions cover configuration, realms, clients and group policy.
  The browser Keycloak admin console is not needed for these supported flows.
  An additional Traefik /admin route allows only loopback source addresses;
  direct loopback API calls by the module keep working. Public OIDC, account,
  login, resources and /realms/master/ns8-home are preserved. Removal deletes
  the additional route. Updating a configured module installs the restriction.
- P6: the group mapper uses LDAP_ONLY at the top-level group path. Keycloak
  then returns only LDAP memberships, including for users who have local
  memberships left over from the previous READ_ONLY mapper. The gate and
  structural validation require this mode. Reconciliation updates existing
  federations; local records need not be deleted.
- P7: register-client accepts a sticky access_required flag. First activation
  pins the currently approved group ID unless the consumer supplies its own
  expected_access_group. The consumer expectation is resolved to a stable group
  ID independently of the administrator policy. Registrations without an explicit
  expectation never repin an altered policy. Missing policy or a group-ID mismatch is denied by both
  the required action and token gate. Normal NS8 administrator policy edits
  cannot move this independent pin either. A mismatched policy stays closed
  (policy_incomplete) until explicitly matching module reconfiguration registers
  the new expected group, or the original policy is restored. Removing a required
  policy retains the marker and token gate and denies access. get-client-access exposes
  policy_required, policy_group_pinned and policy_consumer_bound so consumers
  reject older IdPs and incomplete bindings.
- P12: a KeycloakSession-local decision avoids duplicate LDAP membership
  reads for access and ID token creation within one HTTP request. No decision
  survives the request. A debug-only, identifier-free lookup message permits
  counting live lookups in integration tests; revocation across requests is
  retained.
- P15: redirect callbacks are exact HTTPS or loopback HTTP endpoints, or
  native application callbacks. Credentials, fragments, dangerous schemes and
  callback/host wildcards are rejected. Logout retains only the established
  terminal path wildcard fallback; web origins are exact (or Keycloak '+',
  derived from validated callbacks). Administrative/account audience names are
  rejected. Mail-style service audiences remain supported. An audience claim
  grants no authorization by itself: a receiving application must validate
  issuer/audience and apply its own access rules. No cross-service permission
  bypass was demonstrated by the original review.
- P16: destructive client cleanup reads current bindings from the leader,
  not a replica. A read error aborts without interpreting it as an unbind.

## Follow-up of the security recheck, 29 October 2026

Source: user decisions R0/R1/R8 and fixes R2–R7 in agent-exchange task
`20261029-claude-recheck-implementation`.

- R2: keycloak.service allows 600 s to start: the health check (150 s),
  keycloak-post-start waiting for the model bootstrap (300 s) and its
  reconciliation. Before, the 180 s limit could stop Keycloak during a slow
  upgrade although the error of the post-start step itself is ignored.
- R6: without exactly one enabled user domain realm, the host root shows a
  neutral page instead of redirecting to /admin/, which P4 restricts to the
  node.
- R7: the gate and the policy validation also require a READ_ONLY federation.
  With LDAP_ONLY, a writable federation would write Keycloak membership
  changes to LDAP, so Keycloak administrators could grant access.
- R8: LDAP_ONLY applies to all clients of the realm: local Keycloak group
  memberships of LDAP users are ignored everywhere. The user grants access to
  applications with AD groups only (decision of 29 October 2026).

P3 stays open: anti-brute-force work is being planned separately. No limits
are selected here. P13 full restore testing is deferred by the user. P19 was
withdrawn; P21 direct membership remains the existing agreed semantics.
