"""Credential input, immutable identity and transport capability boundaries."""
import copy
import contextlib
import importlib.util
import json
import os
import io
from pathlib import Path
import ssl
import runpy
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from unittest.mock import Mock
import jsonschema

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('cert_module', ROOT / 'imageroot/pypkg/idpcert.py')
cert = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cert)


class FakeKC:
    def __init__(self):
        self.rep = {'attributes': {'unrelated': 'keep'}, 'browserFlow': 'browser'}
        self.user = {'id': 'fixed-id', 'username': 'alice', 'enabled': True,
                     'federationLink': 'ldap', 'attributes': {'LDAP_ID': ['fixed-object-guid']}}
        self.fail_logout = False
    def get(self, path, params=None):
        if path.endswith('/users'): return [copy.deepcopy(self.user)]
        if '/users/' in path: return copy.deepcopy(self.user)
        return copy.deepcopy(self.rep)
    def put(self, path, data): self.rep.update(copy.deepcopy(data))
    def post(self, path, data=None):
        if self.fail_logout: raise RuntimeError('directory unavailable')


class CertificateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        folder = Path(cls.temp.name)
        subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
            '-keyout', str(folder/'device.key'), '-out', str(folder/'device.crt'),
            '-days', '2', '-subj', '/CN=device', '-addext', 'basicConstraints=critical,CA:FALSE',
            '-addext', 'extendedKeyUsage=clientAuth', '-addext', 'keyUsage=critical,digitalSignature'],
            check=True, capture_output=True)
        cls.pem = (folder/'device.crt').read_text()
        cls.private = (folder/'device.key').read_text()
    @classmethod
    def tearDownClass(cls): cls.temp.cleanup()

    def test_public_certificate_binds_both_immutable_identifiers(self):
        kc = FakeKC()
        record = cert.enroll(kc, 'ad.test', 'alice', 'tablet', self.pem)
        self.assertEqual(record['user_id'], 'fixed-id')
        self.assertEqual(record['ldap_id'], 'fixed-object-guid')
        self.assertEqual(len(record['fingerprint']), 64)
        self.assertEqual(kc.rep['attributes']['unrelated'], 'keep')
        self.assertNotIn('PRIVATE', json.dumps(kc.rep))
        with self.assertRaisesRegex(cert.CertificateError, 'already_registered'):
            cert.enroll(kc, 'ad.test', 'alice', 'other owner', self.pem)

    def test_bundles_private_keys_and_server_certificates_rejected(self):
        for value in (self.private, self.pem + self.private, self.pem + self.pem, 'not a certificate'):
            with self.subTest(value=value[:30]), self.assertRaises(cert.CertificateError): cert.inspect(value)
        # Syntactically encoded garbage must not become a credential.
        with self.assertRaises(cert.CertificateError): cert.inspect('-----BEGIN CERTIFICATE-----\nYWJj\n-----END CERTIFICATE-----')

    def test_local_disabled_and_unbound_accounts_cannot_enroll(self):
        for field, value in [('federationLink', None), ('enabled', False), ('attributes', {})]:
            kc = FakeKC()
            kc.user[field] = value
            with self.subTest(field=field), self.assertRaises(cert.CertificateError):
                cert.enroll(kc, 'ad.test', 'alice', 'tablet', self.pem)
            self.assertEqual(kc.rep['attributes'], {'unrelated': 'keep'})

    def test_revoke_failure_stays_denied_and_can_be_retried(self):
        kc = FakeKC()
        record = cert.enroll(kc, 'ad.test', 'alice', 'tablet', self.pem)
        kc.fail_logout = True
        with self.assertRaises(RuntimeError): cert.revoke(kc, 'ad.test', record['fingerprint'])
        self.assertTrue(cert.records(kc.rep)[record['fingerprint']]['revoked'])
        kc.fail_logout = False
        cert.revoke(kc, 'ad.test', record['fingerprint'])
        self.assertFalse(cert.records(kc.rep))
        self.assertEqual(kc.rep['attributes'], {'unrelated': 'keep'})

    def test_deleted_user_does_not_prevent_certificate_removal(self):
        kc = FakeKC()
        record = cert.enroll(kc, 'ad.test', 'alice', 'tablet', self.pem)
        missing = RuntimeError('user removed')
        missing.status = 404
        kc.post = Mock(side_effect=missing)
        cert.revoke(kc, 'ad.test', record['fingerprint'])
        self.assertFalse(cert.records(kc.rep))

    def test_custom_flow_rejection_rolls_back_new_transport(self):
        kc = FakeKC()
        kc.rep['browserFlow'] = 'site-specific-mfa'
        realm = types.ModuleType('idprealm')
        realm.require_keycloak = lambda: None
        realm.realms_lock = contextlib.nullcontext
        realm.fail_validation = Mock(side_effect=SystemExit(2))
        admin = types.ModuleType('kcadmin')
        admin.agent_client = lambda: kc
        admin.managed_realms = lambda client: ['ad.test']
        routes = types.ModuleType('idp_routes')
        routes.certificate_transport = Mock()
        request = io.StringIO(json.dumps({'domain':'ad.test', 'operation':'enable'}))
        with patch.dict(sys.modules, {'idpcert':cert, 'idprealm':realm, 'kcadmin':admin, 'idp_routes':routes}), \
                patch.object(cert, 'proxy_secret', return_value='a'*64), patch.object(sys, 'stdin', request), \
                self.assertRaises(SystemExit):
            runpy.run_path(str(ROOT/'imageroot/actions/alter-certificates/20alter'), run_name='__main__')
        self.assertEqual([call.args for call in routes.certificate_transport.call_args_list], [(True,), (False,)])
        self.assertFalse(cert.enabled(kc.rep))
        realm.fail_validation.assert_called_once_with('operation', 'enable', 'custom_browser_flow')

    def test_actions_reject_incomplete_operations_and_bad_fingerprints(self):
        schema = json.loads((ROOT/'imageroot/actions/alter-certificates/validate-input.json').read_text())
        for request in ({'domain':'ad.test','operation':'enroll'},
                        {'domain':'ad.test','operation':'revoke','fingerprint':'../x'},
                        {'domain':'ad.test','operation':'surprise'}):
            with self.assertRaises(jsonschema.ValidationError): jsonschema.validate(request, schema)
        jsonschema.validate({'domain':'ad.test','operation':'enable'}, schema)

    def route_module(self, routes, supported=True, failing=()):
        """idp_routes with a fake proxy."""
        agent = types.ModuleType('agent')
        calls = []
        def get_route(instance):
            result = copy.deepcopy(routes.get(instance, {}))
            if result and supported and not all(r.get('client_certificates') for r in routes.values()):
                result['client_certificates'] = False
            return result
        def set_route(data, error_passthrough=True):
            self.assertFalse(error_passthrough, 'set_route exits on errors, skipping the rollback')
            self.assertFalse(data['lets_encrypt_check'] or data['lets_encrypt_cleanup'])
            data = copy.deepcopy(data)
            calls.append(data)
            if data['instance'] in failing and len(calls) <= 2:
                return {'exit_code': 3, 'error': 'failed', 'output': ''}
            routes.setdefault(data['instance'], {}).update(data)
            if not supported: routes[data['instance']].pop('client_certificates', None)
            if not routes[data['instance']].get('headers'):
                routes[data['instance']].pop('headers', None)
            return {'exit_code': 0, 'error': '', 'output': ''}
        agent.get_route = get_route
        agent.set_route = set_route
        spec = importlib.util.spec_from_file_location('cert_routes', ROOT/'imageroot/pypkg/idp_routes.py')
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'agent':agent, 'idpcert':cert}):
            spec.loader.exec_module(module)
        module.time = types.SimpleNamespace(monotonic=Mock(side_effect=[0, 21]), sleep=lambda _:None)
        return module, calls

    def transport(self, module, *args):
        with patch.object(cert, 'proxy_secret', return_value='a'*64), patch.dict(os.environ,
                {'MODULE_ID':'idp1','IDP_HOSTNAME':'sso.test','TCP_PORT':'1234'}):
            module.certificate_transport(*args)

    ORIGINAL = {'idp1': {'instance':'idp1','host':'sso.test','url':'http://127.0.0.1:1234','http2https':True,
                         'lets_encrypt':True},
                'idp1-admin': {'instance':'idp1-admin','host':'sso.test','url':'http://127.0.0.1:1234','path':'/admin',
                               'http2https':True,'lets_encrypt':True,'ip_allowlist':['127.0.0.1/32','::1/128']}}

    def test_stock_traefik_cannot_silently_enable_certificate_login(self):
        routes = copy.deepcopy(self.ORIGINAL)
        module, _ = self.route_module(routes, supported=False)
        with self.assertRaisesRegex(cert.CertificateError, 'traefik_certificate_support_required'):
            self.transport(module, True)
        for instance, route in self.ORIGINAL.items():
            for key, value in route.items():
                self.assertEqual(routes[instance][key], value)
            self.assertNotIn(cert.PROOF_HEADER, routes[instance].get('headers', {}).get('request', {}))

    def test_both_routes_are_written_together_and_keep_their_settings(self):
        routes = copy.deepcopy(self.ORIGINAL)
        module, calls = self.route_module(routes)
        self.transport(module, True)
        self.assertEqual([call['instance'] for call in calls], ['idp1', 'idp1-admin'])
        self.assertTrue(all(r['client_certificates'] and r['lets_encrypt'] for r in routes.values()))
        self.assertTrue(all(r['headers']['request'][cert.HEADER] == '' for r in routes.values()))
        self.assertEqual(routes['idp1-admin']['ip_allowlist'], ['127.0.0.1/32','::1/128'])

    def test_failed_route_write_restores_both_routes(self):
        for failing in ('idp1', 'idp1-admin'):
            routes = copy.deepcopy(self.ORIGINAL)
            module, calls = self.route_module(routes, failing=(failing,))
            with self.assertRaisesRegex(cert.CertificateError, 'traefik_route_failed'):
                self.transport(module, True)
            self.assertEqual({d['instance'] for d in calls[2:]}, set(self.ORIGINAL))
            self.assertFalse(any(r.get('client_certificates') for r in routes.values()))

    def test_unreadable_route_stops_before_losing_lets_encrypt(self):
        routes = {'idp1-admin': copy.deepcopy(self.ORIGINAL['idp1-admin'])}
        module, calls = self.route_module(routes)
        with self.assertRaisesRegex(cert.CertificateError, 'idp_route_missing'):
            self.transport(module, True)
        self.assertEqual(calls, [])
        # configure-module knows the choice from its request.
        self.transport(module, True, 'sso.test', True)
        self.assertTrue(routes['idp1']['lets_encrypt'])

    def test_matching_transport_is_not_rewritten(self):
        routes = copy.deepcopy(self.ORIGINAL)
        module, calls = self.route_module(routes)
        self.transport(module, True)
        self.transport(module, True)
        self.assertEqual(len(calls), 2)
        module.time = types.SimpleNamespace(monotonic=Mock(side_effect=[0, 21]), sleep=lambda _:None)
        self.transport(module, True, 'other.test', True)
        self.assertEqual(len(calls), 4)

    def test_account_state_is_read_live_for_each_directory_schema(self):
        for active_directory, attribute in ((True, 'accountExpires'), (False, 'pwdAccountLockedTime')):
            config = cert.account_state_mapper_config(active_directory)
            self.assertEqual(config['ldap.attribute'], [attribute])
            self.assertEqual(config['always.read.value.from.ldap'], ['true'])
            self.assertEqual(config['read.only'], ['true'])

    def test_disable_keeps_a_flow_bound_by_an_administrator(self):
        kc = Mock()
        kc.get.return_value = {'browserFlow':'site flow', 'attributes':{cert.ENABLED:'true', cert.PROOF_ATTRIBUTE:'a'*64}}
        cert.set_enabled(kc, 'ad.test', False)
        self.assertEqual(kc.put.call_args.args[1], {'attributes':{cert.ENABLED:'false'}, 'browserFlow':'site flow'})

    def test_reconcile_skips_a_realm_already_in_place(self):
        kc = Mock()
        kc.get.return_value = {'browserFlow':cert.FLOW, 'attributes':{cert.ENABLED:'true', cert.PROOF_ATTRIBUTE:'a'*64}}
        cert.set_enabled(kc, 'ad.test', True, 'a'*64)
        kc.put.assert_not_called()
