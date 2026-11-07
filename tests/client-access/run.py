#!/usr/bin/env python3
"""Disposable Samba AD + ns8-idp OIDC client access protocol tests.
Requires Podman. Only loopback ports are published; no production resources.
"""
import base64
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import unittest
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit

import requests
import types

ROOT = Path(__file__).resolve().parents[2]
# The NS8 agent libraries are not needed by the Keycloak functions used
# here: stub them to load the module code unchanged.
for name in ('agent', 'agent.ldapproxy', 'agent.tasks', 'cluster', 'cluster.userdomains', 'kcadmin'):
    sys.modules.setdefault(name, types.ModuleType(name))
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / 'imageroot/pypkg'))
import idpaccess
import idplegacy
import idprealm


class Form(HTMLParser):
    """Forms, with their hidden and prefilled inputs, and links of a page."""
    def __init__(self, html):
        super().__init__()
        self.action = None
        self.forms = {}
        self.links = []
        self._form = None
        self.feed(html)
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'form':
            self._form = {'action': attrs.get('action'), 'inputs': {}}
            self.forms[attrs.get('id') or ''] = self._form
            if attrs.get('id') == 'kc-form-login':
                self.action = attrs['action']
        elif tag == 'input' and self._form is not None and attrs.get('name'):
            self._form['inputs'][attrs['name']] = attrs.get('value') or ''
        elif tag == 'a' and attrs.get('href'):
            self.links.append(attrs['href'])
    def handle_endtag(self, tag):
        if tag == 'form':
            self._form = None


def cmd(*args, check=True, **kwargs):
    return subprocess.run(args, check=check, capture_output=True, text=True, **kwargs)


def port():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


class HTTPError(RuntimeError):
    """An admin API error, with the status and body like kcadmin.KeycloakError."""
    def __init__(self, method, path, status, body):
        super().__init__(f'{method} {path}: {status} {body[:400]}')
        self.status = status
        self.body = body


class Admin:
    def __init__(self, url, password):
        self.url = url
        self.password = password
        self.token = None
    def request(self, method, path, data=None, params=None):
        if self.token is None:
            response = requests.post(self.url + '/realms/master/protocol/openid-connect/token', data={
                'grant_type': 'password', 'client_id': 'admin-cli', 'username': 'admin', 'password': self.password}, timeout=20)
            response.raise_for_status()
            self.token = response.json()['access_token']
        response = requests.request(method, self.url + '/admin/realms' + path, json=data,
            params=params, headers={'Authorization': 'Bearer ' + self.token}, timeout=25)
        if response.status_code == 401:
            self.token = None
            return self.request(method, path, data, params)
        if response.status_code >= 400:
            raise HTTPError(method, path, response.status_code, response.text)
        return response.json() if response.content else response.headers.get('Location')
    def get(self, p, params=None): return self.request('GET', p, params=params)
    def post(self, p, data=None): return self.request('POST', p, data)
    def put(self, p, data=None): return self.request('PUT', p, data)
    def delete(self, p, data=None): return self.request('DELETE', p, data)
    def find_client(self, realm, cid):
        return next((c for c in self.get('/' + realm + '/clients', params={'clientId': cid}) if c['clientId'] == cid), None)


def wait_http(url, containers, seconds=180):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            if requests.get(url, timeout=2).status_code == 200:
                return
        except requests.RequestException:
            pass
        for name in containers:
            state = cmd('podman', 'inspect', '-f', '{{.State.Running}}', name)
            if state.stdout.strip() != 'true':
                logs = cmd('podman', 'logs', name).stdout + cmd('podman', 'logs', name).stderr
                raise RuntimeError(f'{name} exited: {logs[-5000:]}')
        time.sleep(2)
    raise TimeoutError(url)


class LoginTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.suffix = secrets.token_hex(4)
        cls.network = 'vw-sso-' + cls.suffix
        cls.samba = 'vw-ad-' + cls.suffix
        cls.keycloak = 'vw-kc-' + cls.suffix
        cls.names = []
        # samba-tool parses a positional password beginning with '-' as an
        # option. Keep random credentials but always start with a safe prefix.
        cls.password = 'Aa1!' + secrets.token_urlsafe(24)
        cls.kc_port, cls.vw_port = port(), port()
        cls.url = f'http://127.0.0.1:{cls.kc_port}'
        cls.vw_url = f'http://127.0.0.1:{cls.vw_port}'
        cls.addClassCleanup(cls.cleanup)
        cmd('podman', 'network', 'create', cls.network)
        env = dict(os.environ, AD_PASSWORD=cls.password)
        cmd('podman', 'run', '-d', '--name', cls.samba, '--hostname', 'dc.ad.test',
            '--network', cls.network, '--network-alias', 'samba', '--env', 'AD_PASSWORD',
            'localhost/ns8-vaultwarden-test-samba', env=env)
        cls.names.append(cls.samba)
        env = dict(os.environ, KC_BOOTSTRAP_ADMIN_USERNAME='admin', KC_BOOTSTRAP_ADMIN_PASSWORD=cls.password)
        cmd('podman', 'run', '-d', '--name', cls.keycloak, '--network', cls.network,
            '-p', f'127.0.0.1:{cls.kc_port}:8080', '--env', 'KC_BOOTSTRAP_ADMIN_USERNAME',
            '--env', 'KC_BOOTSTRAP_ADMIN_PASSWORD', os.environ.get('IDP_RUNTIME_IMAGE', 'localhost/ns8-idp-client-access-test'),
            'start-dev', '--db=dev-file', '--features=scripts', '--log-level=INFO,org.nethserver.keycloak.access:DEBUG', '--hostname=' + getattr(cls, 'frontend_url', cls.url),
            '--spi-theme--welcome-theme=ns8',
            *getattr(cls, 'keycloak_args', []),
            env=env)
        cls.names.append(cls.keycloak)
        wait_http(cls.url + '/realms/master/.well-known/openid-configuration', cls.names)
        cls.kc = Admin(cls.url, cls.password)
        cls.realm = 'ad.test'
        cls.kc.post('', {'realm': cls.realm, 'enabled': True, 'sslRequired': 'none',
            'registrationAllowed': False})
        rid = cls.kc.get('/ad.test')['id']
        # Same read-only AD LDAP schema and group mapper as ns8-idp, using the
        # private test network in place of the NS8 ldapproxy.
        conf = {k: [v] for k,v in {
            'enabled':'true', 'editMode':'READ_ONLY', 'connectionUrl':'ldap://samba:389',
            'authType':'simple', 'bindDn':'CN=Administrator,CN=Users,DC=ad,DC=test',
            'bindCredential':cls.password, 'importEnabled':'true', 'syncRegistrations':'false',
            'trustEmail':'true', 'vendor':'ad', 'usersDn':'DC=ad,DC=test',
            'searchScope':'2', 'usernameLDAPAttribute':'sAMAccountName', 'rdnLDAPAttribute':'cn',
            'uuidLDAPAttribute':'objectGUID', 'userObjectClasses':'person, organizationalPerson, user',
            'customUserSearchFilter':'(&(objectCategory=person)(!(sAMAccountName=Administrator)))',
            'pagination':'true', 'cachePolicy':'DEFAULT', 'connectionTimeout':'3000', 'readTimeout':'3000'
        }.items()}
        cls.kc.post('/ad.test/components', {'name':'ns8-ldap','providerId':'ldap',
            'providerType':'org.keycloak.storage.UserStorageProvider','parentId':rid,'config':conf})
        cls.component = cls.kc.get('/ad.test/components',params={'type':'org.keycloak.storage.UserStorageProvider'})[0]
        cls.kc.post('/ad.test/components', {'name':'groups','providerId':'group-ldap-mapper',
            'providerType':'org.keycloak.storage.ldap.mappers.LDAPStorageMapper',
            'parentId':cls.component['id'], 'config':{k:[v] for k,v in {
                'group.name.ldap.attribute':'cn', 'groups.dn':'DC=ad,DC=test',
                'group.object.classes':'group', 'preserve.group.inheritance':'false',
                'membership.ldap.attribute':'member', 'membership.attribute.type':'DN',
                'membership.user.ldap.attribute':'cn', 'mode':'LDAP_ONLY',
                'user.roles.retrieve.strategy':'LOAD_GROUPS_BY_MEMBER_ATTRIBUTE',
                'drop.non.existing.groups.during.sync':'false'
            }.items()}})
        mapper = next(c for c in cls.kc.get('/ad.test/components',params={'parent':cls.component['id']}) if c['name']=='groups')
        # Wait for domain provisioning, then import group objects once. Membership
        # itself is looked up on authentication, never maintained in this runner.
        end = time.monotonic()+90
        while True:
            try:
                cls.kc.post('/ad.test/user-storage/' + cls.component['id'] + '/mappers/' + mapper['id'] + '/sync?direction=fedToKeycloak')
                break
            except RuntimeError:
                if time.monotonic()>end: raise
                time.sleep(2)
        # Registration as by the register-client action, with the access token
        # lifespan requested by the Vaultwarden module
        redirect=[cls.vw_url+'/identity/connect/oidc-signin']
        cls.secret = idprealm.ensure_client(cls.kc, 'ad.test', 'vaultwarden1', redirect_uris=redirect,
            access_token_lifespan=600)
        idprealm.ensure_client(cls.kc, 'ad.test', 'other1', redirect_uris=redirect)
        cls.policy = idpaccess.set_policy(cls.kc, 'ad.test', cls.kc.find_client('ad.test','vaultwarden1'),
            'services_vaultwarden')
    @classmethod
    def cleanup(cls):
        out=ROOT/'tests/outputs/integration'
        out.mkdir(parents=True,exist_ok=True)
        for name in reversed(cls.names):
            logs=cmd('podman','logs',name,check=False)
            # Never retain passwords, authorization URLs/codes or tokens.
            lines=[l for l in (logs.stdout+logs.stderr).splitlines()
                if not any(v in l.lower() for v in ('password','token','code=','state=','bindcredential','secret'))]
            (out/(name.split('-')[1]+'.log')).write_text('\n'.join(lines))
            cmd('podman','rm','-f',name,check=False)
        cmd('podman','network','rm',cls.network,check=False)

    def auth(self, username, session=None, client='vaultwarden1', mobile=False, require_cookie=False):
        s=session or requests.Session()
        verifier=secrets.token_urlsafe(48)
        challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        url=self.url+'/realms/ad.test/protocol/openid-connect/auth?'+urlencode({
            'client_id':client,'redirect_uri':self.vw_url+'/identity/connect/oidc-signin',
            'response_type':'code','scope':'openid profile email','state':secrets.token_urlsafe(24),
            'code_challenge':challenge,'code_challenge_method':'S256'})
        r=s.get(url,allow_redirects=False,timeout=20)
        for _ in range(20):
            # Keycloak treats loopback as a secure browser context and sets
            # Secure cookies even on HTTP. requests lacks that browser exception.
            # Only our ephemeral loopback fixture is allowed to relax this flag.
            for cookie in s.cookies:
                if cookie.domain == '127.0.0.1': cookie.secure = False
            if r.is_redirect:
                target=urljoin(r.url,r.headers['Location'])
                if target.startswith('bitwarden:') or (not mobile and target.startswith(self.vw_url)):
                    return s,r,target,verifier
                r=s.get(target,allow_redirects=False,timeout=20)
                continue
            form=Form(r.text)
            if form.action:
                if require_cookie:
                    self.fail('Expected reuse of the existing SSO cookie; password fallback would invalidate this test')
                r=s.post(form.action,data={'username':username,'password':self.password},allow_redirects=False,timeout=20)
                continue
            return s,r,None,verifier
        self.fail('Redirect loop')

    def test_01_allowed_and_denied(self):
        self.assertTrue(self.policy['enforced'], self.policy)
        # No private flow, no realm flow change, no cache change
        client=self.kc.find_client('ad.test','vaultwarden1')
        self.assertFalse(any((client.get('authenticationFlowBindingOverrides') or {}).values()))
        self.assertEqual(self.kc.get('/ad.test')['browserFlow'],'browser')
        comp=self.kc.get('/ad.test/components/'+self.component['id'])
        self.assertEqual(comp['config']['cachePolicy'],['DEFAULT'])
        for username,expected in [('allowed',True),('denied',False)]:
            with self.subTest(username=username):
                _,r,target,_=self.auth(username)
                self.assertEqual(bool(target and 'code=' in target),expected,
                    f'{username}: HTTP {r.status_code}, page {r.text[-1000:]}')

    def test_02_other_client_unrestricted(self):
        _,_,target,_=self.auth('denied',client='other1')
        self.assertIn('code=',target or '')


    def test_04_revocation_with_cookie_and_new_device(self):
        session,_,target,_=self.auth('allowed',client='other1')
        self.assertIn('code=',target or '')
        cmd('podman','exec',self.samba,'samba-tool','group','removemembers','services_vaultwarden','allowed')
        try:
            for label,s,mobile in [('existing cookie',session,False),('new browser',None,False)]:
                with self.subTest(label=label):
                    _,r,target,_=self.auth('allowed',session=s,mobile=mobile,require_cookie=s is not None)
                    self.assertIsNone(target,f'{label}: got a callback after revocation')
                    self.assertEqual(r.status_code,403)
            # Login to other applications still succeeds after removal.
            _,_,target,_=self.auth('allowed',session=session,client='other1',require_cookie=True)
            self.assertIn('code=',target or '')
        finally:
            cmd('podman','exec',self.samba,'samba-tool','group','addmembers','services_vaultwarden','allowed')
        _,_,target,_=self.auth('allowed')
        self.assertIn('code=',target or '')

    def test_05_missing_policy_denies(self):
        client=self.kc.find_client('ad.test','vaultwarden1')
        attrs=dict(client['attributes'])
        client['attributes'][idpaccess.GROUP_ID] = 'missing-group'
        self.kc.put('/ad.test/clients/'+client['id'],client)
        try:
            _,r,target,_=self.auth('allowed')
            self.assertIsNone(target)
            self.assertEqual(r.status_code,403)
        finally:
            client['attributes']=attrs
            self.kc.put('/ad.test/clients/'+client['id'],client)

    def test_06_policy_idempotent_and_restart_persistent(self):
        state=idpaccess.set_policy(self.kc,'ad.test',self.kc.find_client('ad.test','vaultwarden1'),'services_vaultwarden')
        self.assertTrue(state['enforced'])
        cmd('podman','restart',self.keycloak)
        wait_http(self.url+'/realms/ad.test/.well-known/openid-configuration',self.names)
        self.kc.token=None
        _,_,target,_=self.auth('allowed')
        self.assertIn('code=',target or '')
        _,r,target,_=self.auth('denied')
        self.assertIsNone(target)
        self.assertEqual(r.status_code,403)
    def test_07_directory_unavailable_denies(self):
        session,_,target,_=self.auth('allowed',client='other1')
        self.assertIn('code=',target or '')
        # With LDAP unavailable, Keycloak may invalidate cookie authentication
        # and show a fresh login form. That is safe; completing it must still
        # produce neither an authorization code nor a token.
        cmd('podman','pause',self.samba)
        try:
            _,r,target,_=self.auth('allowed',session=session)
            self.assertIsNone(target)
            self.assertGreaterEqual(r.status_code,400)
        finally:
            cmd('podman','unpause',self.samba)

    def test_08_code_and_refresh_cannot_bypass_revocation(self):
        _,_,target,verifier=self.auth('allowed')
        self.assertIn('code=',target or '')
        # Issue one live refresh token before removing group membership.
        _,_,second,second_verifier=self.auth('allowed')
        token_url=self.url+'/realms/ad.test/protocol/openid-connect/token'
        def redeem(callback, pkce):
            return requests.post(token_url,data={
                'grant_type':'authorization_code','client_id':'vaultwarden1',
                'client_secret':self.secret,'code':parse_qs(urlsplit(callback).query)['code'][0],
                'redirect_uri':self.vw_url+'/identity/connect/oidc-signin','code_verifier':pkce},timeout=20)
        live=redeem(second,second_verifier)
        self.assertEqual(live.status_code,200)
        refresh=live.json()['refresh_token']
        cmd('podman','exec',self.samba,'samba-tool','group','removemembers','services_vaultwarden','allowed')
        try:
            stale=redeem(target,verifier)
            self.assertEqual(stale.status_code,403)
            self.assertNotIn('access_token',stale.json())
            refreshed=requests.post(token_url,data={
                'grant_type':'refresh_token','client_id':'vaultwarden1',
                'client_secret':self.secret,'refresh_token':refresh},timeout=20)
            self.assertEqual(refreshed.status_code,403)
            self.assertNotIn('access_token',refreshed.json())
        finally:
            cmd('podman','exec',self.samba,'samba-tool','group','addmembers','services_vaultwarden','allowed')

    def test_09_cached_user_revocation_and_regrant(self):
        # The LDAP cache stays enabled: warm it with a login to another client,
        # then check that membership changes apply to the next login at once.
        comp=self.kc.get('/ad.test/components/'+self.component['id'])
        self.assertEqual(comp['config']['cachePolicy'],['DEFAULT'])
        session,_,target,_=self.auth('allowed',client='other1')
        self.assertIn('code=',target or '')
        cmd('podman','exec',self.samba,'samba-tool','group','removemembers','services_vaultwarden','allowed')
        try:
            _,r,target,_=self.auth('allowed',session=session,require_cookie=True)
            self.assertIsNone(target)
            self.assertEqual(r.status_code,403)
        finally:
            cmd('podman','exec',self.samba,'samba-tool','group','addmembers','services_vaultwarden','allowed')
        _,_,target,_=self.auth('allowed',session=session,require_cookie=True)
        self.assertIn('code=',target or '')
        cmd('podman','exec',self.samba,'samba-tool','group','addmembers','services_vaultwarden','denied')
        try:
            _,_,target,_=self.auth('denied')
            self.assertIn('code=',target or '')
        finally:
            cmd('podman','exec',self.samba,'samba-tool','group','removemembers','services_vaultwarden','denied')
        _,r,target,_=self.auth('denied')
        self.assertIsNone(target)


    def test_12_access_token_lifespan_is_optional(self):
        kc=self.kc
        lifespan=lambda cid: (kc.find_client('ad.test',cid).get('attributes') or {}).get('access.token.lifespan') or None
        self.assertEqual(lifespan('vaultwarden1'),'600')
        self.assertIsNone(lifespan('other1'))
        redirect=[self.vw_url+'/identity/connect/oidc-signin']
        # A registration without the setting keeps it
        idprealm.ensure_client(kc,'ad.test','vaultwarden1',redirect_uris=redirect)
        self.assertEqual(lifespan('vaultwarden1'),'600')
        _,_,target,verifier=self.auth('allowed')
        token=requests.post(self.url+'/realms/ad.test/protocol/openid-connect/token',data={
            'grant_type':'authorization_code','client_id':'vaultwarden1','client_secret':self.secret,
            'code':parse_qs(urlsplit(target).query)['code'][0],
            'redirect_uri':self.vw_url+'/identity/connect/oidc-signin','code_verifier':verifier},timeout=20).json()
        self.assertGreaterEqual(token['expires_in'],595)
        self.assertLessEqual(token['expires_in'],600)
        # None restores the realm default
        idprealm.ensure_client(kc,'ad.test','vaultwarden1',redirect_uris=redirect,access_token_lifespan=None)
        self.assertIsNone(lifespan('vaultwarden1'))
        idprealm.ensure_client(kc,'ad.test','vaultwarden1',redirect_uris=redirect,access_token_lifespan=600)
        self.assertEqual(lifespan('vaultwarden1'),'600')
        # Registrations keep the policy
        self.assertTrue(idpaccess.access_state(kc,'ad.test',kc.find_client('ad.test','vaultwarden1'))['enforced'])

    def test_13_policy_removal_and_new_policy(self):
        kc=self.kc
        idpaccess.clear_policy(kc,'ad.test',kc.find_client('ad.test','vaultwarden1'))
        try:
            client=kc.find_client('ad.test','vaultwarden1')
            self.assertFalse(idpaccess.restricted(client))
            self.assertFalse(any(m.get('protocolMapper')==idpaccess.TOKEN_GATE
                for m in kc.get('/ad.test/clients/'+client['id']+'/protocol-mappers/models')))
            self.assertFalse(any(k.startswith('ns8.access') for k in client.get('attributes',{})))
            _,_,target,_=self.auth('denied')
            self.assertIn('code=',target or '')
        finally:
            state=idpaccess.set_policy(kc,'ad.test',kc.find_client('ad.test','vaultwarden1'),'services_vaultwarden')
        self.assertTrue(state['enforced'])
        _,r,target,_=self.auth('denied')
        self.assertIsNone(target)
        with self.assertRaises(idpaccess.PolicyError) as ctx:
            idpaccess.set_policy(kc,'ad.test',kc.find_client('ad.test','other1'),'no_such_group')
        self.assertEqual(ctx.exception.code,'group_not_found')
        self.assertFalse(idpaccess.restricted(kc.find_client('ad.test','other1')))
        self.assertTrue(kc.find_client('ad.test','other1')['enabled'])


    def test_15_reconcile_restores_missing_parts(self):
        kc=self.kc
        client=kc.find_client('ad.test','vaultwarden1')
        for mapper in idpaccess._token_gates(kc,'ad.test',client):
            kc.delete('/ad.test/clients/'+client['id']+'/protocol-mappers/models/'+mapper['id'])
        action=next(a for a in kc.get('/ad.test/authentication/required-actions') if a['providerId']==idpaccess.ACTION)
        action['enabled']=False
        kc.put('/ad.test/authentication/required-actions/'+action['alias'],action)
        state=idpaccess.access_state(kc,'ad.test',kc.find_client('ad.test','vaultwarden1'))
        self.assertFalse(state['enforced'])
        self.assertEqual(set(state['issues']),{'token_gate_missing','required_action_disabled'})
        idpaccess.reconcile(kc,'ad.test',idprealm.module_clients(kc,'ad.test'))
        self.assertTrue(idpaccess.access_state(kc,'ad.test',kc.find_client('ad.test','vaultwarden1'))['enforced'])
        _,r,target,_=self.auth('denied')
        self.assertIsNone(target)

    def test_16_client_removed_and_registered_again(self):
        """Module removal deletes its client; a new module instance with the
        same ID registers a new client, without policy until set again."""
        kc=self.kc
        kc.delete('/ad.test/clients/'+kc.find_client('ad.test','vaultwarden1')['id'])
        redirect=[self.vw_url+'/identity/connect/oidc-signin']
        idprealm.ensure_client(kc,'ad.test','vaultwarden1',redirect_uris=redirect,access_token_lifespan=600)
        client=kc.find_client('ad.test','vaultwarden1')
        client['secret']=self.secret
        kc.put('/ad.test/clients/'+client['id'],client)
        self.assertFalse(idpaccess.access_state(kc,'ad.test',kc.find_client('ad.test','vaultwarden1'))['enforced'])
        state=idpaccess.set_policy(kc,'ad.test',kc.find_client('ad.test','vaultwarden1'),'services_vaultwarden')
        self.assertTrue(state['enforced'])
        _,r,target,_=self.auth('denied')
        self.assertIsNone(target)
        _,_,target,_=self.auth('allowed')
        self.assertIn('code=',target or '')


    def test_30_federated_idps_of_earlier_versions_are_removed(self):
        """A realm configured by 0.1.0-rc.1 with a federated IdP: NS8 flow
        copies bound to the realm, a writable LDAP federation with its
        mappers, and an IdP using the NS8 first broker login flow."""
        kc=self.kc
        comp=kc.get('/ad.test/components/'+self.component['id'])
        original=json.loads(json.dumps(comp['config']))
        comp['config'].update({'editMode':['WRITABLE'],'syncRegistrations':['true']})
        kc.put('/ad.test/components/'+comp['id'],comp)
        for name in ('cn','ns8_idp'):
            kc.post('/ad.test/components',{'name':name,'providerId':'user-attribute-ldap-mapper',
                'providerType':idplegacy.MAPPER_TYPE,'parentId':comp['id'],'config':{
                    'ldap.attribute':[name if name=='cn' else 'employeeType'],
                    'user.model.attribute':['username' if name=='cn' else name],'read.only':['false'],
                    'always.read.value.from.ldap':['false'],'is.mandatory.in.ldap':['false']}})
        for builtin,copy in (('browser','ns8 browser'),('direct grant','ns8 direct grant'),
                ('first broker login','ns8 first broker login')):
            kc.post('/ad.test/authentication/flows/'+builtin.replace(' ','%20')+'/copy',{'newName':copy})
        kc.put('/ad.test',{'browserFlow':'ns8 browser','directGrantFlow':'ns8 direct grant'})
        kc.post('/ad.test/identity-provider/instances',{'alias':'entra','providerId':'oidc','enabled':True,
            'firstBrokerLoginFlowAlias':'ns8 first broker login','config':{'clientId':'x','clientSecret':'y',
            'authorizationUrl':'https://login.example.test/auth','tokenUrl':'https://login.example.test/token'}})
        # An IdP added with the Keycloak console is left alone
        kc.post('/ad.test/identity-provider/instances',{'alias':'manual','providerId':'oidc','enabled':False,
            'config':{'clientId':'x','clientSecret':'y','authorizationUrl':'https://login.example.test/auth',
            'tokenUrl':'https://login.example.test/token'}})
        self.addCleanup(lambda:kc.delete('/ad.test/identity-provider/instances/manual'))
        self.assertTrue(idplegacy.needs_cleanup(kc,'ad.test','ns8-ldap'))
        def ensure_federation(kc_, realm):
            # Stands in for idprealm.ensure_federation, which reads the NS8
            # user domain: apply the read-only settings of this runner
            c=kc_.get('/ad.test/components/'+comp['id'])
            c['config'].update({'editMode':original['editMode'],'syncRegistrations':original['syncRegistrations']})
            kc_.put('/ad.test/components/'+comp['id'],c)
        idplegacy.remove_federated_idps(kc,'ad.test','ns8-ldap',ensure_federation)
        self.assertEqual([i['alias'] for i in kc.get('/ad.test/identity-provider/instances')],['manual'])
        realm=kc.get('/ad.test')
        self.assertEqual((realm['browserFlow'],realm['directGrantFlow']),('browser','direct grant'))
        self.assertFalse([f for f in kc.get('/ad.test/authentication/flows') if f['alias'].startswith('ns8 ')])
        comp=kc.get('/ad.test/components/'+comp['id'])
        self.assertEqual(comp['config']['editMode'],['READ_ONLY'])
        mappers=kc.get('/ad.test/components',params={'parent':comp['id'],'type':idplegacy.MAPPER_TYPE})
        self.assertFalse({'cn','ns8_idp'} & {m['name'] for m in mappers})
        self.assertFalse([m for m in mappers if m['config'].get('read.only')==['false']])
        self.assertFalse(idplegacy.needs_cleanup(kc,'ad.test','ns8-ldap'))
        # Idempotent, and the policy works as before
        idplegacy.remove_federated_idps(kc,'ad.test','ns8-ldap',ensure_federation)
        self.assertTrue(idpaccess.access_state(kc,'ad.test',kc.find_client('ad.test','vaultwarden1'))['enforced'])
        _,_,target,_=self.auth('allowed')
        self.assertIn('code=',target or '')
        _,r,target,_=self.auth('denied')
        self.assertIsNone(target)
        self.assertEqual(r.status_code,403)

    def saml_client(self, name, group_client='vaultwarden1'):
        """A SAML client, created as with the Keycloak console, with the
        policy attributes of another client copied: the module API sets
        policies on its OIDC clients only."""
        acs=self.vw_url+'/saml/acs'
        policy={k:v for k,v in self.kc.find_client('ad.test',group_client)['attributes'].items() if k.startswith('ns8.access')}
        self.kc.post('/ad.test/clients',{'clientId':name,'protocol':'saml','enabled':True,
            'redirectUris':[acs],'frontchannelLogout':False,'attributes':dict(policy,**{
                'saml.client.signature':'false','saml.force.post.binding':'true',
                'saml_assertion_consumer_url_post':acs,'saml_idp_initiated_sso_url_name':name})})
        client=self.kc.find_client('ad.test',name)
        self.addCleanup(lambda:self.kc.delete('/ad.test/clients/'+client['id']))
        return client,acs

    def saml_login(self, username, url, session=None, require_cookie=False):
        """Follow a SAML login. Return (last response, SAMLResponse or None)."""
        s=session or requests.Session()
        r=s.get(url,allow_redirects=False,timeout=20)
        for _ in range(20):
            for cookie in s.cookies:
                if cookie.domain == '127.0.0.1': cookie.secure = False
            if r.is_redirect:
                r=s.get(urljoin(r.url,r.headers['Location']),allow_redirects=False,timeout=20)
                continue
            page=Form(r.text)
            for form in page.forms.values():
                if 'SAMLResponse' in form['inputs']:
                    return r,form['inputs']['SAMLResponse']
            if page.action:
                if require_cookie:
                    self.fail('Expected reuse of the existing SSO cookie')
                r=s.post(page.action,data={'username':username,'password':self.password},allow_redirects=False,timeout=20)
                continue
            return r,None
        self.fail('Redirect loop')

    def test_31_saml_logins_run_the_required_action(self):
        """Hypothesis: the required action does not depend on the protocol,
        so it also restricts SAML logins, SP- and IdP-initiated, with and
        without an SSO cookie."""
        import zlib
        client,acs=self.saml_client('saml-review')
        def sp_initiated():
            request=(f'<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" '
                f'xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" ID="_{secrets.token_hex(16)}" Version="2.0" '
                f'IssueInstant="{time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}" '
                f'Destination="{self.url}/realms/ad.test/protocol/saml" AssertionConsumerServiceURL="{acs}" '
                f'ProtocolBinding="urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST">'
                f'<saml:Issuer>saml-review</saml:Issuer></samlp:AuthnRequest>')
            deflate=zlib.compressobj(9,zlib.DEFLATED,-15)
            data=deflate.compress(request.encode())+deflate.flush()
            return self.url+'/realms/ad.test/protocol/saml?'+urlencode({'SAMLRequest':base64.b64encode(data).decode()})
        idp_initiated=self.url+'/realms/ad.test/protocol/saml/clients/saml-review'
        for label,url in (('SP-initiated',sp_initiated),('IdP-initiated',lambda:idp_initiated)):
            with self.subTest(label):
                r,response=self.saml_login('allowed',url())
                self.assertTrue(response,f'{label}: member got no SAMLResponse: {r.status_code} {r.text[-500:]}')
                self.assertIn('allowed',base64.b64decode(response).decode())
                r,response=self.saml_login('denied',url())
                self.assertIsNone(response)
                self.assertEqual(r.status_code,403)
                # SSO cookie of an unrestricted client
                session,_,target,_=self.auth('denied',client='other1')
                self.assertIn('code=',target or '')
                r,response=self.saml_login('denied',url(),session=session,require_cookie=True)
                self.assertIsNone(response)
                self.assertEqual(r.status_code,403)

    def device_login(self, client, secret, username):
        """Run the device authorization grant. Return the token response."""
        base=self.url+'/realms/ad.test/protocol/openid-connect'
        device=requests.post(base+'/auth/device',data={'client_id':client,'client_secret':secret,
            'scope':'openid'},timeout=20)
        self.assertEqual(device.status_code,200,device.text)
        device=device.json()
        s=requests.Session()
        r=s.get(device['verification_uri_complete'],allow_redirects=False,timeout=20)
        for _ in range(20):
            for cookie in s.cookies:
                if cookie.domain == '127.0.0.1': cookie.secure = False
            if r.is_redirect:
                r=s.get(urljoin(r.url,r.headers['Location']),allow_redirects=False,timeout=20)
                continue
            page=Form(r.text)
            if page.action:
                r=s.post(page.action,data={'username':username,'password':self.password},allow_redirects=False,timeout=20)
                continue
            # The consent page of the device grant: its buttons are not inputs
            consent=next((f for f in page.forms.values() if f['action']),None) if 'name="accept"' in r.text else None
            if consent:
                r=s.post(urljoin(r.url,consent['action']),data=dict(consent['inputs'],accept='Yes'),
                    allow_redirects=False,timeout=20)
                continue
            break
        self.device_page=r
        return requests.post(base+'/token',data={'grant_type':'urn:ietf:params:oauth:grant-type:device_code',
            'device_code':device['device_code'],'client_id':client,'client_secret':secret},timeout=20)

    def test_32_device_grant_switched_on_again(self):
        """An administrator switches the device grant on again in the
        Keycloak console: it is reported, and still denied to non-members."""
        kc=self.kc
        client=kc.find_client('ad.test','vaultwarden1')
        client['attributes']['oauth2.device.authorization.grant.enabled']='true'
        kc.put('/ad.test/clients/'+client['id'],client)
        try:
            state=idpaccess.access_state(kc,'ad.test',kc.find_client('ad.test','vaultwarden1'))
            self.assertEqual(state['issues'],['device_grant_set'])
            token=self.device_login('vaultwarden1',self.secret,'denied')
            self.assertEqual(self.device_page.status_code,403,self.device_page.text[-500:])
            self.assertNotIn('access_token',token.json())
            token=self.device_login('vaultwarden1',self.secret,'allowed')
            self.assertEqual(token.status_code,200,token.text)
            self.assertIn('access_token',token.json())
        finally:
            state=idpaccess.set_policy(kc,'ad.test',kc.find_client('ad.test','vaultwarden1'),'services_vaultwarden')
        self.assertTrue(state['enforced'],state)
        self.assertEqual(kc.find_client('ad.test','vaultwarden1')['attributes']['oauth2.device.authorization.grant.enabled'],'false')

    def test_33_token_exchange_switched_on_again(self):
        """Standard token exchange of a token of an unrestricted client,
        switched on in the Keycloak console: the token gate denies it to
        non-members."""
        kc=self.kc
        redirect=[self.vw_url+'/identity/connect/oidc-signin']
        # Tokens of other1 must have vaultwarden1 in their audience
        other_secret=idprealm.ensure_client(kc,'ad.test','other1',redirect_uris=redirect,audience=['vaultwarden1'])
        client=kc.find_client('ad.test','vaultwarden1')
        client['attributes']['standard.token.exchange.enabled']='true'
        kc.put('/ad.test/clients/'+client['id'],client)
        token_url=self.url+'/realms/ad.test/protocol/openid-connect/token'
        try:
            self.assertEqual(idpaccess.access_state(kc,'ad.test',kc.find_client('ad.test','vaultwarden1'))['issues'],
                ['token_exchange_set'])
            for username,allowed in (('allowed',True),('denied',False)):
                with self.subTest(username):
                    _,_,target,verifier=self.auth(username,client='other1')
                    subject=requests.post(token_url,data={'grant_type':'authorization_code','client_id':'other1',
                        'client_secret':other_secret,'code':parse_qs(urlsplit(target).query)['code'][0],
                        'redirect_uri':redirect[0],'code_verifier':verifier},timeout=20).json()['access_token']
                    exchanged=requests.post(token_url,data={
                        'grant_type':'urn:ietf:params:oauth:grant-type:token-exchange',
                        'client_id':'vaultwarden1','client_secret':self.secret,'subject_token':subject,
                        'subject_token_type':'urn:ietf:params:oauth:token-type:access_token'},timeout=20)
                    self.assertEqual('access_token' in exchanged.json(),allowed,exchanged.text)
                    if not allowed:
                        self.assertEqual(exchanged.status_code,403,exchanged.text)
        finally:
            idprealm.ensure_client(kc,'ad.test','other1',redirect_uris=redirect)
            state=idpaccess.set_policy(kc,'ad.test',kc.find_client('ad.test','vaultwarden1'),'services_vaultwarden')
        self.assertTrue(state['enforced'],state)


    def test_34_host_root(self):
        """The host root leads to the account console of the only enabled
        user domain realm, otherwise to a neutral page."""
        home=self.url+'/realms/master/ns8-home'
        page=requests.get(self.url+'/',timeout=20)
        self.assertEqual(page.status_code,200,page.text[-500:])
        self.assertIn('url='+home,page.text)
        def target():
            response=requests.get(home,allow_redirects=False,timeout=20)
            self.assertEqual(response.status_code,302,response.text[-500:])
            self.assertIn('no-store',response.headers.get('Cache-Control',''))
            return response.headers['Location']
        account=self.url+'/realms/ad.test/account/'
        self.assertEqual(target(),account)
        login=requests.get(account,timeout=20)
        self.assertEqual(login.status_code,200,login.text[-500:])
        self.assertIn('/realms/ad.test/',login.url)
        self.kc.post('',{'realm':'second.test','enabled':True})
        try:
            # Two realms: a neutral page names no user domain, and the
            # Administration Console stays reachable only from the node
            neutral=requests.get(home,allow_redirects=False,timeout=20)
            self.assertEqual(neutral.status_code,200,neutral.text[-500:])
            self.assertIn('no-store',neutral.headers.get('Cache-Control',''))
            self.assertIn('id="ns8-home"',neutral.text)
            self.assertNotIn('ad.test',neutral.text)
            self.assertNotIn('second.test',neutral.text)
            realm=self.kc.get('/second.test')
            realm['enabled']=False
            self.kc.put('/second.test',realm)
            self.assertEqual(target(),account)
        finally:
            self.kc.delete('/second.test')
        self.assertEqual(target(),account)

if __name__=='__main__':
    unittest.main(verbosity=2)
