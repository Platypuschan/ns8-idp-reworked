# Certificate authentication validation, 2026-10-31

Task: `20261031-codex-x509-login`. [PR19](https://github.com/Platypuschan/ns8-idp-reworked/pull/19).
Tested production source: **6293ac8dec68686767035132ba95d03d6235770d**.
No production installation, main branch or release tag was changed.

## Review fixes, 2026-10-31

Task: `20261031-claude-x509-review-fixes`. Changes since the source above: parallel
route writes with rollback, stop on an unreadable route, re-authentication via
the password form, `operational` state, disable with a site flow, no-op
reconciliation. Evidence at 3dfe3cba7319dff10063b074630420c3329b1775:
[candidate 41209570588](https://github.com/Platypuschan/ns8-idp-reworked/actions/runs/41209570588)
Debian13 and Rocky9 39 passed / one expected skip each, with the companion proxy;
[protocol 41209569597](https://github.com/Platypuschan/ns8-idp-reworked/actions/runs/41209569597)
unit 38 passed / one skip, legacy suites 17+6+8, TLS suite 9 including `prompt=login`
and `max_age`. Not measured: the duration of the hostname outage while enabling.
`lets_encrypt=true` stays untested, and the Android evidence below predates these
changes. The Java change only adds a skip before certificate handling.

Directory account state, user decision 2026-10-31. Evidence at
44fa456cc8fe8116f584278791d6480a8f002744:
[candidate 41213934537](https://github.com/Platypuschan/ns8-idp-reworked/actions/runs/41213934537)
Debian13 and Rocky9 40 passed / one expected skip each, including lock and unlock
of an OpenLDAP account. TLS suite 11 of 11 with an expired Samba account and a
missing mapper. Negative control: with the check removed, the expired account
signs in, so the test fails.

## CI on real NS8

[Final candidate 41201701011](https://github.com/Platypuschan/ns8-idp-reworked/actions/runs/41201701011)
passed at the tested source above: build, Debian13 and Rocky9, **39 passed /
one existing expected skip per distribution**. Core 3.23.2, Keycloak 26.8.1,
actual NS8 Traefik runtime 3.7.15. Publication was explicitly disabled.

The standard suite first verifies the unmodified stock proxy refuses certificate
enablement while ordinary login keeps working. The dedicated companion suite
then installs the five checksum-verified, patched upstream source files only in
the disposable `ns8-ci` guest and verifies:

- public certificate enrollment for an existing OpenLDAP user, live app group
  policy and optional realm-flow activation;
- actual HTTPS certificate login through NS8 Traefik and the optimized Keycloak;
- missing/forged certificate headers cannot sign in;
- existing enrollment and login survive Keycloak restart and module reconfiguration;
- certificate revocation and feature disablement restore password-only fallback;
- realm/module removal and the existing installation/security checks.

The companion patch is a reviewed source change in `integrations/ns8-traefik`,
**not an installed replacement for stock NS8 Traefik**. Production enablement
requires deploying that capability separately.

Rocky's default NethServer BaseOS mirror returned HTTP404 for advertised metadata
in [initial candidate 41199046354](https://github.com/Platypuschan/ns8-idp-reworked/actions/runs/41199046354).
The final CI uses `tests/ns8/bootstrap-rocky.sh`: pinned/checksummed NS8 installer,
Core 3.23.2, official Rocky repositories with signature verification and a pinned,
checksummed shared module test runner. This affects only the disposable guest;
no installed module or production OS repository is changed.

## Protocol, unit and build evidence

[Protocol CI 41201704799](https://github.com/Platypuschan/ns8-idp-reworked/actions/runs/41201704799)
passed at the same tested commit:

- 33 unit/action cases: **32 passed, one existing expected skip**;
- existing real Keycloak/Samba suites: **17 client-access, 6 failure and 8 security
  decision cases**, all passed;
- **8 real TLS/Traefik 3.7.15/Keycloak/Samba cases**, all passed;
- local full UI/module/optimized runtime builds passed; UI formatting warnings
  corrected. Optimized configuration confirms the persisted Traefik lookup
  provider, PostgreSQL and scripts. Robot dryrun: 41/41.

TLS cases check key possession, unknown/expired/revoked credentials, forged
headers over TLS and directly on loopback, immutable directory identity,
disabled AD users, group removal, SSO-cookie invalidation, password fallback,
feature disablement and restart persistence. An unrestricted client also rejects
certificate authentication during LDAP outage after a previously cached login.

The full NS8 suite caught a real activation defect in
[candidate 41200177226](https://github.com/Platypuschan/ns8-idp-reworked/actions/runs/41200177226):
Traefik 3.7.15 removes both host routers from the effective API while their SNI
TLS options conflict. The initial code checked the host route before updating
`/admin`. The tested correction snapshots both complete routes before changing
anything, deep copies settings, applies both and only then confirms capability.
A real API disappearance/recovery regression and an action-boundary regression
now cover this behavior. The final NS8 suite above passes that corrected path.

## Physical Android L8

ADB shell and app installation verified on PRITOM L8 / L8_B02, Android 13.
Chrome **156.0.8078.73**, system WebView **156.0.8078.47**. A separate disposable
`org.nethserver.x509test` app exercised native OIDC/S256 PKCE without changing
existing applications' accounts or server settings.

The physical fixture used the same Java authenticator (source 72652cf), Samba
AD, real Traefik TLS (3.6.1 at that time) and a public native OIDC client with
live AD group policy. Follow-up server protocol and NS8 tests above use the
actual NS8 Traefik 3.7.15. Only loopback listeners were published; an explicit
ADB reverse mapping connected the tablet to that isolated fixture.

A test client identity was imported through Android's normal **VPN and apps**
installer. No global server CA was installed. Chrome's self-signed-server
exception was restricted to localhost; the native token request and WebView
independently pin the exact fixture server certificate.

| Physical flow | Observed result |
|---|---|
| Chrome → native custom-scheme callback → PKCE exchange | `OIDC PKCE TOKEN SUCCESS` |
| Chrome Custom Tab → native callback → PKCE exchange | `OIDC PKCE TOKEN SUCCESS` |
| WebView implementing Android KeyChain callback | System certificate picker, then `OIDC PKCE TOKEN SUCCESS` |
| Remove test user from app AD group, repeat Custom Tab login | `accessDenied`; no successful callback/token |
| Restore group, revoke device pin and IdP sessions, repeat | Password form; certificate alone no longer signs in |

These are native OIDC integration tests, **not a complete Bitwarden app login**
or vault-unlock/biometric test. WebViews without a ClientCertRequest/KeyChain
implementation are not assumed to work. Existing Bitwarden/Firefox accounts,
configuration and application data were preserved.

Cleanup completed: only the test client identity was removed from Android user
credentials (the existing WLAN identity was preserved), the separate app was
uninstalled and only the test ADB reverse mapping was removed. Temporary
containers/network, private keys, PKCS#12 files, APKs and fixture credentials were
removed. Reproduction helpers are in `tests/x509/android/README.md`; their native
client preparation and scoped local cleanup were also executed successfully.
Never publish fixture APKs/keys, token responses or raw UI dumps.

## Limits and rollout state

No main merge, RC/stable release or user-instance rollout. The companion proxy
capability is required; merely updating the IdP module cannot enable stock
Traefik's missing API feature. Certificate authentication replaces the
password/form-OTP branch rather than adding a second factor. Revocation ends
IdP sessions; existing app sessions/tokens and offline data keep their own rules.

A genuine update from an existing rc.4 installation and full NS8 backup/restore
were not executed in this task. The inherited install-scenario upgrade test is
the explicitly reported skip. Restart, reconfiguration, disablement, persistence
and removal were tested as described above. Final documentation/development
helper changes after the tested source do not change production code.
