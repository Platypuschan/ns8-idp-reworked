"""Administrator-managed device certificates; no private keys enter NS8 tasks.

Trust is an exact SHA-256 certificate pin, as with LXD, rather than a name
asserted by an arbitrary certificate. Records live in realm attributes, not
user-editable profile attributes, and bind the LDAP object and Keycloak ID.
Call mutations while holding idprealm.realms_lock().
"""
import datetime
import hashlib
import json
import os
import re
import secrets
import ssl
import subprocess
import urllib.parse

PREFIX = 'ns8.x509.device.'
ENABLED = 'ns8.x509.enabled'
FLOW = 'ns8 certificate browser'
PROVIDER = 'ns8-device-certificate'
HEADER = 'X-Forwarded-Tls-Client-Cert'
PROOF_HEADER = 'X-NS8-X509-Proxy'
PROOF_ATTRIBUTE = 'ns8.x509.proxy_secret'
ACCOUNT_MAPPER = 'ns8-account-state'
ACCOUNT_ATTRIBUTE = 'ns8.account_state'


def account_state_mapper_config(active_directory):
    """Certificate sign-in has no LDAP bind, which is what enforces these
    states for passwords: read them live. isEnabled() covers ACCOUNTDISABLE."""
    return {
        'ldap.attribute': ['accountExpires' if active_directory else 'pwdAccountLockedTime'],
        'user.model.attribute': [ACCOUNT_ATTRIBUTE],
        'read.only': ['true'],
        'always.read.value.from.ldap': ['true'],
        'is.mandatory.in.ldap': ['false'],
    }


def proxy_secret():
    """A private state file, shared by host routes and managed realm settings.
    Local applications cannot impersonate the proxy by sending public PEMs.
    The proxy's administrative route API is an explicit trust boundary.
    """
    filename = 'x509-proxy-secret'
    try:
        with open(filename) as stream:
            value = stream.read().strip()
    except FileNotFoundError:
        value = secrets.token_hex(32)
        try:
            fd = os.open(filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            return proxy_secret()
        with os.fdopen(fd, 'w') as stream:
            stream.write(value + '\n')
    if not re.fullmatch('[a-f0-9]{64}', value):
        raise CertificateError('invalid_proxy_secret')
    return value


class CertificateError(ValueError):
    pass


def path(value):
    return urllib.parse.quote(value, safe='')


def records(rep):
    return {k[len(PREFIX):]: json.loads(v) for k, v in rep.get('attributes', {}).items()
            if k.startswith(PREFIX)}


def enabled(rep):
    return rep.get('attributes', {}).get(ENABLED) == 'true'


def operational_flow(rep):
    """The realm has certificates enabled and its browser flow accepts them."""
    return enabled(rep) and rep.get('browserFlow') == FLOW


def inspect(pem):
    # Reject bundles/private keys instead of silently enrolling their first cert.
    if not re.fullmatch(r'\s*-----BEGIN CERTIFICATE-----\s+[A-Za-z0-9+/=\s]+-----END CERTIFICATE-----\s*', pem):
        raise CertificateError('invalid_certificate')
    result = subprocess.run(['openssl', 'x509', '-noout', '-enddate', '-startdate', '-purpose',
                             '-ext', 'basicConstraints,extendedKeyUsage,keyUsage'],
                            input=pem, text=True, capture_output=True, timeout=10)
    if (result.returncode or 'SSL client : Yes' not in result.stdout
            or 'CA:TRUE' in result.stdout or 'TLS Web Client Authentication' not in result.stdout):
        raise CertificateError('invalid_client_certificate')
    try:
        dates = dict(line.split('=', 1) for line in result.stdout.splitlines() if '=' in line)
        start = datetime.datetime.strptime(dates['notBefore'], '%b %d %H:%M:%S %Y %Z').replace(tzinfo=datetime.timezone.utc)
        end = datetime.datetime.strptime(dates['notAfter'], '%b %d %H:%M:%S %Y %Z').replace(tzinfo=datetime.timezone.utc)
        if not start <= datetime.datetime.now(datetime.timezone.utc) < end:
            raise CertificateError('certificate_not_current')
        digest = hashlib.sha256(ssl.PEM_cert_to_DER_cert(pem.strip())).hexdigest()
    except (ValueError, KeyError) as exc:
        if isinstance(exc, CertificateError):
            raise
        raise CertificateError('invalid_certificate') from exc
    return digest, end.isoformat()


def enroll(kc, realm, username, label, pem):
    fingerprint, end = inspect(pem)
    base = '/' + path(realm)
    users = kc.get(base + '/users', params={'username': username, 'exact': 'true'})
    if len(users) != 1 or not users[0].get('enabled') or not users[0].get('federationLink'):
        raise CertificateError('domain_user_not_found')
    user = kc.get(base + '/users/' + path(users[0]['id']))
    ldap_id = (user.get('attributes', {}).get('LDAP_ID') or [None])[0]
    if not ldap_id:
        raise CertificateError('ldap_identity_missing')
    rep = kc.get(base)
    current = records(rep)
    if fingerprint in current:
        raise CertificateError('certificate_already_registered')
    if len(current) >= 128:
        raise CertificateError('certificate_limit')
    record = {'user_id': user['id'], 'ldap_id': ldap_id, 'username': user['username'],
              'label': label, 'not_after': end}
    attrs = dict(rep.get('attributes', {}))
    attrs[PREFIX + fingerprint] = json.dumps(record)
    kc.put(base, {'attributes': attrs})
    return {'fingerprint': fingerprint, **record}


def revoke(kc, realm, fingerprint):
    base = '/' + path(realm)
    rep = kc.get(base)
    record = records(rep).get(fingerprint)
    if record is None:
        raise CertificateError('certificate_not_found')
    attrs = dict(rep.get('attributes', {}))
    record['revoked'] = True
    attrs[PREFIX + fingerprint] = json.dumps(record)
    # Retain a denied tombstone until logout succeeds, so a failed logout is
    # visible and retryable without ever restoring the credential.
    kc.put(base, {'attributes': attrs})
    try:
        kc.post(base + '/users/' + path(record['user_id']) + '/logout')
    except Exception as exc:
        # A deleted directory/Keycloak user has no session to terminate.
        if getattr(exc, 'status', None) != 404:
            raise
    del attrs[PREFIX + fingerprint]
    kc.put(base, {'attributes': attrs})


def set_enabled(kc, realm, value, proof=None):
    base = '/' + path(realm)
    rep = kc.get(base)
    if value:
        if not proof or not re.fullmatch('[a-f0-9]{64}', proof):
            raise CertificateError('invalid_proxy_secret')
        if operational_flow(rep) and rep['attributes'].get(PROOF_ATTRIBUTE) == proof:
            return
        if rep.get('browserFlow') not in ('browser', FLOW):
            raise CertificateError('custom_browser_flow')
        flows = kc.get(base + '/authentication/flows')
        if not any(f['alias'] == FLOW for f in flows):
            kc.post(base + '/authentication/flows/browser/copy', {'newName': FLOW})
        endpoint = base + '/authentication/flows/' + path(FLOW) + '/executions'
        executions = kc.get(endpoint)
        if not any(e.get('providerId') == PROVIDER for e in executions):
            kc.post(endpoint + '/execution', {'provider': PROVIDER})
        executions = kc.get(endpoint)
        cert = next(e for e in executions if e.get('providerId') == PROVIDER)
        kc.put(endpoint, {**cert, 'requirement': 'ALTERNATIVE'})
        # Ahead of forms but after the existing SSO cookie; copied subflows,
        # OTP and all required actions retain their original configuration.
        executions = kc.get(endpoint)
        while next(i for i, e in enumerate(executions) if e['id'] == cert['id']) > 1:
            kc.post(base + '/authentication/executions/' + cert['id'] + '/raise-priority')
            executions = kc.get(endpoint)
        flow = FLOW
    else:
        # Leave a browser flow bound by an administrator in place: disabling
        # must always work and only undoes the binding made by this module.
        flow = 'browser' if rep.get('browserFlow') == FLOW else rep.get('browserFlow')
    attrs = dict(rep.get('attributes', {}))
    attrs[ENABLED] = str(value).lower()
    if value:
        attrs[PROOF_ATTRIBUTE] = proof
    else:
        attrs.pop(PROOF_ATTRIBUTE, None)
    kc.put(base, {'attributes': attrs, 'browserFlow': flow})
