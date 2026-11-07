#!/usr/bin/env python3
"""Real TLS/Traefik + Keycloak + AD tests using the patched NS8 route writer.

Only disposable loopback listeners. Set X509_KEEP=1 for a physical Android
test through adb reverse after successful assertions (credentials stay local).
"""
import base64
import contextlib
import datetime
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import runpy
import secrets
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

import requests
import yaml
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('access_fixture', ROOT / 'tests/client-access/run.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
import idpcert
cmd, port = fixture.cmd, fixture.port


def certificate(folder, name, *, expired=False, server=False):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    now = datetime.datetime.now(datetime.timezone.utc)
    builder = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
        .public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(days=2))
        .not_valid_after(now + datetime.timedelta(days=-1 if expired else 30))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH if server else ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False))
    if server:
        import ipaddress
        builder = builder.add_extension(x509.SubjectAlternativeName([
            x509.DNSName('localhost'), x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]), critical=False)
    cert = builder.sign(key, hashes.SHA256())
    pem = cert.public_bytes(serialization.Encoding.PEM)
    certpath, keypath = folder / (name + '.crt'), folder / (name + '.key')
    certpath.write_bytes(pem)
    keypath.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    keypath.chmod(0o600)
    return (str(certpath), str(keypath))


def route(source, folder, instance, backend, proof, admin=False):
    agent = types.ModuleType('agent')
    helpers = types.ModuleType('cert_helpers')
    helpers.update_redis_hosts_key_and_notify_event = lambda: None
    reader = types.ModuleType('get_route')
    reader.get_route = lambda request: {}
    data = {'instance': instance, 'url': backend, 'host': 'localhost', 'http2https': True,
            'client_certificates': True, 'headers': {'request': {idpcert.PROOF_HEADER: proof}}}
    if admin:
        data.update(path='/admin', ip_allowlist=['127.0.0.1/32'])
    with patch.dict(sys.modules, {'agent': agent, 'cert_helpers': helpers, 'get_route': reader}), \
            patch.dict(os.environ, {'AGENT_ID': 'module/traefik-test'}), \
            patch.object(sys, 'stdin', io.StringIO(json.dumps(data))), contextlib.chdir(folder):
        runpy.run_path(str(source / 'imageroot/actions/set-route/20writeconfig'), run_name='__main__')
    # NS8 replaces env templates before giving the YAML to Traefik.
    target = folder / 'configs' / (instance + '.yml')
    target.write_text(target.read_text().replace("'{{ env \"PROXIES_DEPTH\" | default \"0\"}}'", '0'))


class CertificateLogin(fixture.LoginTests):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='ns8-x509-')
        cls.folder = Path(cls.temp.name)
        cls.folder.chmod(0o700)
        cls.tls_port, cls.http_port, cls.api_port = port(), port(), port()
        cls.frontend_url = f'https://localhost:{cls.tls_port}'
        cls.keycloak_args = ['--spi-x509cert-lookup--provider=traefik']
        cls.proof = secrets.token_hex(32)
        super().setUpClass()
        cls.server = certificate(cls.folder, 'server', server=True)
        cls.allowed = certificate(cls.folder, 'allowed')
        cls.denied = certificate(cls.folder, 'denied')
        cls.unknown = certificate(cls.folder, 'unknown')
        cls.expired = certificate(cls.folder, 'expired', expired=True)
        spec = importlib.util.spec_from_file_location('prepare_proxy', ROOT / 'integrations/ns8-traefik/prepare.py')
        prepare = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(prepare)
        source = prepare.prepare(cls.folder / 'source')
        (cls.folder / 'configs').mkdir()
        route(source, cls.folder, 'idp', cls.url, cls.proof)
        route(source, cls.folder, 'idp-admin', cls.url, cls.proof, admin=True)
        (cls.folder / 'configs/certificate.yml').write_text(yaml.safe_dump({'tls': {'certificates': [
            {'certFile': '/fixture/server.crt', 'keyFile': '/fixture/server.key'}]}}))
        cls.proxy = 'x509-proxy-' + cls.suffix
        cmd('podman', 'run', '-d', '--name', cls.proxy, '--network', 'host',
            '-v', str(cls.folder) + ':/fixture:ro,Z',
            os.environ.get('TRAEFIK_TEST_IMAGE', 'docker.io/library/traefik:v3.7.15@sha256:10cc4f33663c9d71049b71775d0b2ac67c18f7ade489ce9d826acc292d7eb82a'),
            '--entrypoints.http.address=127.0.0.1:' + str(cls.http_port),
            '--entrypoints.https.address=127.0.0.1:' + str(cls.tls_port),
            '--entrypoints.traefik.address=127.0.0.1:' + str(cls.api_port), '--api.insecure=true',
            '--providers.file.directory=/fixture/configs', '--providers.file.watch=true', '--log.level=INFO')
        cls.names.append(cls.proxy)
        # Requests must verify the actual server cert, never verify=False.
        for _ in range(40):
            try:
                r = requests.get(cls.frontend_url + '/realms/ad.test/.well-known/openid-configuration', verify=cls.server[0], timeout=2)
                if r.status_code == 200: break
            except requests.RequestException: pass
            time.sleep(.5)
        else: raise RuntimeError('TLS route did not become ready')
        cls.create_account_mapper()
        cls.pins = {}
        for username in ('allowed', 'denied'):
            cls.pins[username] = idpcert.enroll(cls.kc, 'ad.test', username, username,
                                               Path(getattr(cls, username)[0]).read_text())
        idpcert.set_enabled(cls.kc, 'ad.test', True, cls.proof)

    @classmethod
    def create_account_mapper(cls):
        cls.kc.post('/ad.test/components', {'name': idpcert.ACCOUNT_MAPPER,
            'providerId': 'user-attribute-ldap-mapper', 'parentId': cls.component['id'],
            'providerType': 'org.keycloak.storage.ldap.mappers.LDAPStorageMapper',
            'config': idpcert.account_state_mapper_config(True)})

    @classmethod
    def cleanup(cls):
        if os.environ.get('X509_KEEP'):
            # A private local fixture for Android; never send these credentials
            # to test logs or GitHub artifacts.
            private = cls.folder / 'android-fixture.json'
            private.write_text(json.dumps({'fixture_kind': 'ns8-x509', 'url': cls.frontend_url, 'port': cls.tls_port,
                'keycloak': cls.keycloak, 'samba': cls.samba, 'proxy': cls.proxy,
                'admin_url': cls.url, 'password': cls.password, 'network': cls.network}))
            private.chmod(0o600)
            print('Android fixture directory:', cls.folder)
            # TemporaryDirectory would otherwise erase the mounted fixture.
            cls.temp._finalizer.detach()
            return
        super().cleanup()
        cls.temp.cleanup()

    def cert_auth(self, cert=None, headers=None, session=None, username=None, client='vaultwarden1', **params):
        s = session or requests.Session()
        s.verify = self.server[0]
        if cert: s.cert = cert
        verifier = secrets.token_urlsafe(48)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        url = self.frontend_url + '/realms/ad.test/protocol/openid-connect/auth?' + urlencode({
            'client_id': client, 'redirect_uri': self.vw_url + '/identity/connect/oidc-signin',
            'response_type': 'code', 'scope': 'openid', 'state': secrets.token_urlsafe(20),
            'code_challenge': challenge, 'code_challenge_method': 'S256', **params})
        r = s.get(url, headers=headers, allow_redirects=False, timeout=20)
        for _ in range(15):
            if r.is_redirect:
                target = fixture.urljoin(r.url, r.headers['Location'])
                if target.startswith(self.vw_url): return s, r, target, verifier
                r = s.get(target, allow_redirects=False, timeout=20)
            elif username and fixture.Form(r.text).action:
                r = s.post(fixture.Form(r.text).action, data={'username': username, 'password': self.password}, allow_redirects=False, timeout=20)
                username = None
            else:
                return s, r, None, verifier
        raise AssertionError('Redirect loop')

    def test_x509_valid_cert_and_password_fallback(self):
        _, r, target, _ = self.cert_auth(self.allowed)
        self.assertIn('code=', target or '', 'HTTP ' + str(r.status_code) + r.text[-400:])
        _, _, target, _ = self.cert_auth(username='allowed')
        self.assertIn('code=', target or '')

    def test_x509_new_authentication_requests_need_the_password_form(self):
        # Without an SSO session: prompt=login leaves the account choice open.
        _, r, target, _ = self.cert_auth(self.allowed, prompt='login')
        self.assertIsNone(target)
        self.assertTrue(fixture.Form(r.text).action, 'password form expected')
        # With one: a certificate does not answer forced re-authentication.
        session, _, target, _ = self.cert_auth(self.allowed)
        self.assertIn('code=', target or '')
        time.sleep(2)  # max_age compares whole seconds since the login
        for params in ({'prompt':'login'}, {'max_age':'1'}):
            with self.subTest(params=params):
                _, r, target, _ = self.cert_auth(self.allowed, session=session, **params)
                self.assertIsNone(target)
                self.assertTrue(fixture.Form(r.text).action, 'password form expected')
        # The ordinary SSO cookie keeps working.
        _, _, target, _ = self.cert_auth(self.allowed, session=session)
        self.assertIn('code=', target or '')

    def test_x509_no_unknown_expired_or_forged_certificate(self):
        for cert in (None, self.unknown, self.expired):
            with self.subTest(cert=cert):
                _, _, target, _ = self.cert_auth(cert)
                self.assertIsNone(target)
        forged = Path(self.allowed[0]).read_text()
        from urllib.parse import quote
        _, _, target, _ = self.cert_auth(headers={'X-Forwarded-Tls-Client-Cert': quote(forged),
            'X-Forwarded-Tls-Client-Cert-Info': 'Subject=CN=allowed'})
        self.assertIsNone(target)
        # An attacker with their own TLS key cannot replace it with a victim PEM.
        _, _, target, _ = self.cert_auth(self.unknown, headers={'X-Forwarded-Tls-Client-Cert': quote(forged)})
        self.assertIsNone(target)

    def test_x509_proxy_api_roundtrip_after_sni_conflict(self):
        # Traefik 3.7 removes conflicting host routers from its effective API.
        # A sequential NS8 update must configure BOTH before checking either.
        base = f'http://127.0.0.1:{self.api_port}/api/http/routers/'
        for name in ('idp-https', 'idp-admin-https'):
            r = requests.get(base + name + '@file', timeout=5)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.json()['tls']['options'], 'ns8-client-certificates@file')
        file = self.folder / 'configs/idp-admin.yml'
        saved = file.read_text()
        data = yaml.safe_load(saved)
        data['http']['routers']['idp-admin-https']['tls'].pop('options')
        try:
            file.write_text(yaml.safe_dump(data))
            for _ in range(40):
                if requests.get(base + 'idp-https@file', timeout=5).status_code == 404:
                    break
                time.sleep(.2)
            else:
                self.fail('Expected effective router removal during conflicting SNI options')
        finally:
            file.write_text(saved)
            for _ in range(40):
                if all(requests.get(base + name + '@file', timeout=5).status_code == 200
                       for name in ('idp-https', 'idp-admin-https')):
                    break
                time.sleep(.2)
            else:
                self.fail('Both host routes must recover after matching TLS options')

    def test_x509_group_and_disabled_user(self):
        _, r, target, _ = self.cert_auth(self.denied)
        self.assertIsNone(target)
        self.assertEqual(r.status_code, 403)
        cmd('podman', 'exec', self.samba, 'samba-tool', 'group', 'removemembers', 'services_vaultwarden', 'allowed')
        try:
            _, r, target, _ = self.cert_auth(self.allowed)
            self.assertIsNone(target)
            self.assertEqual(r.status_code, 403)
        finally:
            cmd('podman', 'exec', self.samba, 'samba-tool', 'group', 'addmembers', 'services_vaultwarden', 'allowed')
        cmd('podman', 'exec', self.samba, 'samba-tool', 'user', 'disable', 'allowed')
        try:
            _, _, target, _ = self.cert_auth(self.allowed)
            self.assertIsNone(target)
        finally:
            cmd('podman', 'exec', self.samba, 'samba-tool', 'user', 'enable', 'allowed')

    def test_x509_expired_directory_account(self):
        def expiry(*args):
            cmd('podman', 'exec', self.samba, 'samba-tool', 'user', 'setexpiry', 'allowed', *args)
        try:
            expiry('--days=30')
            _, _, target, _ = self.cert_auth(self.allowed)
            self.assertIn('code=', target or '', 'a future expiry is still valid')
            expiry('--days=0')
            time.sleep(1)
            _, r, target, _ = self.cert_auth(self.allowed)
            self.assertIsNone(target)
            self.assertTrue(fixture.Form(r.text).action, 'password form expected')
        finally:
            expiry('--noexpiry')
        _, _, target, _ = self.cert_auth(self.allowed)
        self.assertIn('code=', target or '')

    def test_x509_unknown_account_state_denies_certificate_login(self):
        mapper = next(m for m in self.kc.get('/ad.test/components', params={'parent': self.component['id']})
                      if m['name'] == idpcert.ACCOUNT_MAPPER)
        self.kc.delete('/ad.test/components/' + mapper['id'])
        try:
            _, r, target, _ = self.cert_auth(self.allowed)
            self.assertIsNone(target)
            self.assertTrue(fixture.Form(r.text).action, 'password form expected')
        finally:
            self.create_account_mapper()
        _, _, target, _ = self.cert_auth(self.allowed)
        self.assertIn('code=', target or '')

    def test_x509_direct_backend_header_and_identity_rebinding(self):
        # Even another local application knowing a public certificate must not
        # impersonate Traefik by calling the loopback HTTP listener directly.
        from urllib.parse import quote
        verifier = secrets.token_urlsafe(48)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        response = requests.get(self.url + '/realms/ad.test/protocol/openid-connect/auth', params={
            'client_id':'vaultwarden1', 'redirect_uri':self.vw_url+'/identity/connect/oidc-signin',
            'response_type':'code', 'scope':'openid', 'code_challenge':challenge, 'code_challenge_method':'S256'},
            headers={idpcert.HEADER:quote(Path(self.allowed[0]).read_text()), idpcert.PROOF_HEADER:'forged'},
            allow_redirects=False, timeout=20)
        self.assertNotIn('code=', response.headers.get('Location', ''))
        rep = self.kc.get('/ad.test')
        attrs = dict(rep['attributes'])
        key = idpcert.PREFIX + self.pins['allowed']['fingerprint']
        altered = json.loads(attrs[key])
        altered['ldap_id'] = 'different-directory-object'
        self.kc.put('/ad.test', {'attributes':{**attrs, key:json.dumps(altered)}})
        try:
            _, _, target, _ = self.cert_auth(self.allowed)
            self.assertIsNone(target)
        finally:
            self.kc.put('/ad.test', {'attributes':attrs})

    def test_x509_directory_outage_cannot_use_a_cached_user(self):
        # Check an unrestricted client as well: rejection must not rely only
        # on the separately tested application group gate.
        _, _, target, _ = self.cert_auth(self.allowed, client='other1')
        self.assertIn('code=', target or '')
        cmd('podman', 'pause', self.samba)
        try:
            _, _, target, _ = self.cert_auth(self.allowed, client='other1')
            self.assertIsNone(target)
        finally:
            cmd('podman', 'unpause', self.samba)

    def test_x509_revoked_pin_and_cookie(self):
        session, _, target, _ = self.cert_auth(self.allowed)
        self.assertIn('code=', target or '')
        idpcert.revoke(self.kc, 'ad.test', self.pins['allowed']['fingerprint'])
        try:
            for s in (None, session):
                _, _, target, _ = self.cert_auth(self.allowed, session=s)
                self.assertIsNone(target)
        finally:
            self.pins['allowed'] = idpcert.enroll(self.kc, 'ad.test', 'allowed', 'allowed', Path(self.allowed[0]).read_text())

    def test_x509_disable_and_restart(self):
        idpcert.set_enabled(self.kc, 'ad.test', False)
        _, _, target, _ = self.cert_auth(self.allowed)
        self.assertIsNone(target)
        idpcert.set_enabled(self.kc, 'ad.test', True, self.proof)
        cmd('podman', 'restart', self.keycloak)
        fixture.wait_http(self.url + '/realms/ad.test/.well-known/openid-configuration', self.names)
        self.kc.token = None
        _, _, target, _ = self.cert_auth(self.allowed)
        self.assertIn('code=', target or '')


if __name__ == '__main__':
    # Run inherited password regressions separately with their original fixture.
    suite = unittest.TestSuite(CertificateLogin(name) for name in sorted(dir(CertificateLogin)) if name.startswith('test_x509_'))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(not result.wasSuccessful())
