# Device certificate sign-in

Optional certificate authentication for existing LDAP/AD users. Browser-based
OIDC applications continue using their existing issuer and redirects. Native
apps must support OIDC through a browser/Custom Tab with access to the device's
client certificates. An embedded WebView must explicitly handle certificate
requests. This does not replace the Vaultwarden master password or vault unlock.

## Prerequisite

The module [`traefik-reworked`](https://github.com/Platypuschan/ns8-traefik-reworked)
is required, because the stock route API cannot request or forward client
certificates. Replace the Traefik instance of the node first:

```sh
api-cli run cluster/update-module --data '{"module_url":"ghcr.io/platypuschan/traefik-reworked:4.2.5-reworked.1","instances":["traefik1"]}'
```

The instance then follows that repository, and core updates skip it. This module
refuses to enable certificate sign-in without an acknowledged capability.
Do not enable on installations requiring form-based OTP as a second factor
without reviewing the certificate flow; this method is an alternative to that
form branch. See [the trust model and limitations](decisions/0003-device-certificates.md).

## Create a device identity

Run on the **workstation**, in a new private directory; example label `tablet`:

```sh
umask 077
openssl req -x509 -newkey rsa:3072 -sha256 -nodes \
  -keyout tablet.key -out tablet.crt -days 365 -subj '/CN=tablet' \
  -addext 'basicConstraints=critical,CA:FALSE' \
  -addext 'keyUsage=critical,digitalSignature' \
  -addext 'extendedKeyUsage=clientAuth'
openssl pkcs12 -export -inkey tablet.key -in tablet.crt \
  -name tablet -out tablet.p12
```

Choose an export password when prompted. Import `tablet.p12` into the PC's
personal certificate store/browser, or Android Settings → Security → Encryption
and credentials → Install certificate → **VPN and apps**. Menu names vary.
Keep the key/PKCS#12 file private; a separate key/certificate per device permits
independent revocation. The certificate's CN is just a label, not the login name.

In Cluster Manager → IdP → **Certificates**, choose the realm, enter the existing
domain username and a device label, select only **tablet.crt**, and enroll it.
Then enable certificate sign-in for that realm. The certificate is not trusted
until an administrator enrolls it. No external CA/Let's Encrypt client certificate
is required; the existing website server certificate is independent.

When opening an application, select the client certificate in the browser's
system dialog if requested. Browsers may remember the selection. Because TLS
happens before HTTP, certificate selection can also appear on other requests to
the IdP hostname, including account pages and discovery. The certificate is not
sent to unrelated application hostnames.

## Manage and revoke

The Certificates page lists the label, user, validity end and SHA-256 fingerprint.
Renew by creating/enrolling a new device certificate, importing it and revoking
the old one. Revoke also ends **all IdP sessions of that user**, including other
devices, so an existing SSO cookie cannot immediately bypass revocation. If
logout fails, the denied record remains and revoke can be retried. Existing
application sessions/tokens and offline vaults retain their established rules.
Disabling certificate sign-in returns the realm to its standard browser flow
without deleting enrollments. It prevents new certificate logins, not every
existing application/IdP session. Password login remains available.

Certificate login respects the directory: a disabled, expired (AD) or locked
(OpenLDAP) account cannot use it, and the sign-in falls back to the password form.

A realm holds at most 128 certificates. Enabling or disabling makes the IdP address
unreachable for a few seconds, because the proxy reloads both routes. Applications
which request `prompt=login` always show the password form; use it to sign in with
another account on an enrolled device.

If the page reports that sign-in is enabled but not effective, the proxy lost the
capability (`traefik-reworked` was replaced) or the realm's browser flow was
changed. Password sign-in keeps working. Reinstall the module and restart this
one, or restore the flow.

The actions are `get-certificates` (`domain`) and `alter-certificates`
(`domain`, `operation`: `enable`, `disable`, `enroll`, `revoke`). Enrollment adds
`username`, `label`, `certificate` (public PEM); revoke adds `fingerprint`.
`alter-certificates` needs the module owner role; `get-certificates` also matches
the `reader` role and shows users, labels and fingerprints, no secrets. Neither is
granted to application `clientadm` accounts.

## Reproducible development tests

On a development host with Podman, Python requests/jsonschema/cryptography/PyYAML:

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
podman build -f tests/client-access/Containerfile -t localhost/ns8-idp-client-access-test .
podman build -f tests/client-access/Samba.Containerfile -t localhost/ns8-vaultwarden-test-samba tests/client-access
python3 tests/x509/run.py
```

The suite downloads checksum-verified pinned upstream route sources, applies the
patch and runs the real route writer. Listeners bind to loopback. It tests the
TLS/Keycloak/AD boundary; it does not substitute for a full NS8 update/restore
or for each Android application's browser integration.
