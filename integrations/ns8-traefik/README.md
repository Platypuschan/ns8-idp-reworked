# NS8 Traefik client-certificate capability

The module [`traefik-reworked`](https://github.com/Platypuschan/ns8-traefik-reworked) ships this change. These files stay as the test fixture of this repository.

Stock `NethServer/ns8-traefik` at commit
`21fa9f2e0b14ac84caed6fb4b68bb962d364a5b7` does not expose client certificate
request/forwarding through `set-route`. Merely adding a Keycloak authenticator
cannot enable mTLS on that deployment.

`client-certificates.patch` adds a boolean `client_certificates` to the existing
route API, its readback schema and implementation, and skips the `29waitsync`
wait for such writes, which would only prolong the outage between two routes. It requests an optional TLS
client certificate, removes attacker-controlled certificate headers, then sets
the PEM header from the TLS connection. `RequestClientCert` proves key possession
but intentionally does not authorize any issuer: the IdP checks exact certificate
pins. It is not equivalent to a CA verification policy for arbitrary backends.

All routers for one hostname, including the higher-priority `/admin` route,
must select the same TLS option. Every enabled route selects the identical
`ns8-client-certificates@file` option. HTTP must redirect to HTTPS. The IdP
also overwrites a private proof header to protect its local HTTP listener.

## Review/build

On a development workstation, clone the upstream repository at the pinned
commit into a new directory. Read its development instructions, then run:

```sh
python3 integrations/ns8-traefik/prepare.py /absolute/path/to/ns8-traefik-checkout
```

The helper verifies SHA-256 hashes of all affected upstream files before applying
the patch. Without a full checkout it prepares just the five changed files for
tests. It never edits an installed NS8 Traefik. Build/test the full checkout using
the upstream workflow; deploying that proxy change is a separate operation.

IdP enablement writes both routes in sequence, without waiting between them, and verifies both readbacks
acknowledge the capability; an unmodified proxy cannot silently enable the feature. Disablement removes the
certificate TLS options and forwarding middlewares through the ordinary API.
Deleting the routes removes their configuration and TLS options with them.

`tests/x509/run.py` executes the **patched upstream route writer**, then loads
its generated routes into real Traefik with TLS, Keycloak and Samba AD. It checks
coexisting root/admin routes, key possession, forged headers, certificate/user
revocation, immutable directory identity, password fallback and restart.
