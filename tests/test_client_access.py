"""Action ownership and input/output contract regression tests."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import runpy
import sys
import types
import unittest
from unittest.mock import Mock, patch

import jsonschema

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]


class ClientAccessTests(unittest.TestCase):
    def schema(self, action, direction='input'):
        return json.loads((ROOT / 'imageroot/actions' / action / f'validate-{direction}.json').read_text())

    def test_group_names_and_null(self):
        schema = self.schema('alter-realm-client')
        for group in ('services_vaultwarden', 'engineering', 'R&D', None):
            jsonschema.validate({'domain':'ad.test','client_id':'app1','access_group':group}, schema)
        for group in ('', 'a/b', 'a\nb', 'a\rb', 17):
            with self.subTest(group=group), self.assertRaises(jsonschema.ValidationError):
                jsonschema.validate({'domain':'ad.test','client_id':'app1','access_group':group}, schema)

    def test_token_lifespan_limits(self):
        schema = self.schema('register-client')
        for value in (None, 60, 600, 86400):
            jsonschema.validate({'domain':'ad.test','access_token_lifespan':value}, schema)
        jsonschema.validate({'domain':'ad.test'}, schema)
        for value in (True, '600', 59, 86401, 600.5):
            with self.subTest(value=value), self.assertRaises(jsonschema.ValidationError):
                jsonschema.validate({'domain':'ad.test','access_token_lifespan':value}, schema)

    def run_status(self, caller, request, live=None):
        realm = types.ModuleType('idprealm')
        realm.require_keycloak = Mock()
        def invalid(field, value, code):
            raise ValueError(code)
        realm.fail_validation = invalid
        realm.module_clients = Mock(return_value=[{'id':'a','clientId':'app1','enabled':False}, {'id':'b','clientId':'app2','enabled':True}])
        kcadmin = types.ModuleType('kcadmin')
        kcadmin.agent_client = Mock(return_value=object())
        kcadmin.managed_realms = Mock(return_value=['ad.test'])
        access = types.ModuleType('idpaccess')
        access.access_state = Mock(return_value={'enforced':True,'group':'engineering','group_path':'/engineering','issues':[]})
        access.live_state = Mock(return_value=live)
        agent = types.ModuleType('agent')
        ldapproxy = types.ModuleType('agent.ldapproxy')
        ldapproxy.Ldapproxy = Mock()
        ldapclient = types.ModuleType('agent.ldapclient')
        ldapclient.Ldapclient = Mock()
        ldapclient.LdapclientEntryNotFound = type('LdapclientEntryNotFound', (Exception,), {})
        output = io.StringIO()
        with patch.dict(sys.modules, {'idprealm':realm,'kcadmin':kcadmin,'idpaccess':access,
                    'agent':agent,'agent.ldapproxy':ldapproxy,'agent.ldapclient':ldapclient}), \
                patch.dict(os.environ, {'AGENT_TASK_USER':caller}), \
                patch.object(sys, 'stdin', io.StringIO(json.dumps(request))), contextlib.redirect_stdout(output):
            jsonschema.validate(request, self.schema('get-client-access'))
            runpy.run_path(str(ROOT / 'imageroot/actions/get-client-access/20read'), run_name='__main__')
        state = json.loads(output.getvalue())
        jsonschema.validate(state, self.schema('get-client-access','output'))
        self.live_call = access.live_state.call_args
        return state, access.access_state.call_args.args[2]

    def test_module_reads_only_own_client_and_reports_disabled_separately(self):
        state, client = self.run_status('module/app1', {'domain':'ad.test'})
        self.assertEqual(client['clientId'], 'app1')
        self.assertTrue(state['enforced'])
        self.assertFalse(state['enabled'])
        self.assertNotIn('live', state)

    def test_module_cannot_select_another_client(self):
        with self.assertRaisesRegex(ValueError, 'client_id_not_allowed'):
            self.run_status('module/app1', {'domain':'ad.test','client_id':'app2'})

    def test_module_cannot_check_users(self):
        with self.assertRaisesRegex(ValueError, 'user_not_allowed'):
            self.run_status('module/app1', {'domain':'ad.test','live':True,'user':'alice'})

    def test_administrator_selects_client(self):
        # api-cli tasks have no user, UI tasks have the user ID of the
        # administrator
        for caller in ('', 'admin'):
            with self.subTest(caller=caller):
                state, client = self.run_status(caller, {'domain':'ad.test','client_id':'app2'})
                self.assertEqual(client['clientId'], 'app2')
                self.assertTrue(state['enabled'])

    def test_administrator_must_select_client(self):
        for caller in ('', 'admin'):
            with self.subTest(caller=caller), self.assertRaisesRegex(ValueError, 'client_id_required'):
                self.run_status(caller, {'domain':'ad.test'})

    def test_live_state_is_added_on_request(self):
        live = {'ok':False,'ldap_connection':True,'group_in_ldap':False,'user_allowed':None,'issues':['group_not_in_ldap']}
        state, _ = self.run_status('module/app1', {'domain':'ad.test','live':True}, live=live)
        self.assertEqual(state['live'], live)
        live = dict(live, user_allowed=False)
        state, _ = self.run_status('admin', {'domain':'ad.test','client_id':'app2','live':True,'user':'alice'}, live=live)
        self.assertEqual(self.live_call.args[4], 'alice')
        self.assertFalse(state['live']['user_allowed'])

    def test_user_requires_live(self):
        with self.assertRaisesRegex(ValueError, 'user_requires_live'):
            self.run_status('admin', {'domain':'ad.test','client_id':'app2','user':'alice'})

    def test_unmanaged_realm_and_missing_client(self):
        with self.assertRaisesRegex(ValueError, 'realm_not_found'):
            self.run_status('module/app1', {'domain':'other.test'})
        with self.assertRaisesRegex(ValueError, 'client_not_found'):
            self.run_status('module/missing', {'domain':'ad.test'})


class HTTPError(Exception):
    def __init__(self, status, body=''):
        super().__init__(f'HTTP {status} {body}')
        self.status = status
        self.body = body


class FakeKeycloak:
    """Admin API of one realm with one restricted-to-be client, recording
    the client updates."""
    def __init__(self):
        self.client = {'id':'c1','clientId':'app1','enabled':True,'protocol':'openid-connect',
            'directAccessGrantsEnabled':True,'attributes':{'oauth2.device.authorization.grant.enabled':'true'}}
        self.mappers = []
        self.action = {'alias':'ns8-client-access','providerId':'ns8-client-access','enabled':False}
        self.client_puts = []
        self.fail_put = False
        self.ldap_ok = True
        self.denied_users = set()
        self.edit_mode = 'READ_ONLY'
    def get(self, path, params=None):
        if path.endswith('/unregistered-required-actions'):
            return []
        if path.endswith('/required-actions'):
            return [dict(self.action)]
        if path.endswith('/components'):
            if params.get('type') == 'org.keycloak.storage.UserStorageProvider':
                return [{'id':'ldap1','providerId':'ldap','config':{'connectionUrl':['ldap://x'],'bindDn':['cn=x'],
                    'editMode':[self.edit_mode]}}]
            return [{'id':'m1','providerId':'group-ldap-mapper','config':{'mode':['LDAP_ONLY'],
                'user.roles.retrieve.strategy':['LOAD_GROUPS_BY_MEMBER_ATTRIBUTE']}}]
        if '/group-by-path/' in path or '/groups/' in path:
            return {'id':'g1','name':'engineering','path':'/engineering'}
        if path.endswith('/protocol-mappers/models'):
            return list(self.mappers)
        if path.endswith('/clients/c1'):
            return json.loads(json.dumps(self.client))
        if path.endswith('/users'):
            return [{'id':'u-'+params['username'],'username':params['username']}] if params['username'] != 'nobody' else []
        if path.endswith('/generate-example-access-token'):
            if params['userId'] in self.denied_users:
                raise HTTPError(403, '{"error":"access_denied"}')
            return {}
        raise AssertionError(path)
    def post(self, path, data=None):
        if path.endswith('/protocol-mappers/models'):
            self.mappers.append(dict(data, id='gate1'))
        elif path.endswith('/testLDAPConnection'):
            self.ldap_request = data
            if not self.ldap_ok:
                raise HTTPError(400, '{"errorMessage":"LDAPConnectionFailed"}')
        return None
    def put(self, path, data=None):
        if '/required-actions/' in path:
            self.action = dict(data)
        elif path.endswith('/clients/c1'):
            self.client_puts.append(json.loads(json.dumps(data)))
            if self.fail_put:
                raise HTTPError(500)
            self.client = json.loads(json.dumps(data))
    def delete(self, path, data=None):
        self.mappers = [m for m in self.mappers if not path.endswith('/' + m['id'])]


class PolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for name in ('agent', 'agent.ldapproxy', 'agent.tasks', 'cluster', 'cluster.userdomains'):
            sys.modules.setdefault(name, types.ModuleType(name))
        sys.path.insert(0, str(ROOT / 'imageroot/pypkg'))
        import idpaccess
        cls.access = idpaccess

    def test_policy_is_set_by_one_update_after_its_checks(self):
        kc = FakeKeycloak()
        state = self.access.set_policy(kc, 'ad.test', kc.get('/ad.test/clients/c1'), 'engineering')
        self.assertTrue(state['enforced'], state)
        self.assertTrue(kc.action['enabled'])
        self.assertEqual(len(kc.mappers), 1)
        # One update, never with the client disabled
        self.assertEqual(len(kc.client_puts), 1)
        self.assertTrue(kc.client_puts[0]['enabled'])
        self.assertEqual(kc.client['attributes']['ns8.access_policy'], 'group')
        self.assertFalse(kc.client['directAccessGrantsEnabled'])
        self.assertEqual(kc.client['attributes']['oauth2.device.authorization.grant.enabled'], 'false')

    def test_failed_update_leaves_client_unchanged_and_enabled(self):
        kc = FakeKeycloak()
        kc.fail_put = True
        with self.assertRaises(HTTPError):
            self.access.set_policy(kc, 'ad.test', kc.get('/ad.test/clients/c1'), 'engineering')
        self.assertTrue(kc.client['enabled'])
        self.assertFalse(self.access.restricted(kc.client))

    def test_grants_switched_on_again_are_issues(self):
        kc = FakeKeycloak()
        self.access.set_policy(kc, 'ad.test', kc.get('/ad.test/clients/c1'), 'engineering')
        for attribute, issue in self.access.GRANT_ATTRIBUTES.items():
            with self.subTest(attribute=attribute):
                client = kc.get('/ad.test/clients/c1')
                client['attributes'][attribute] = 'true'
                state = self.access.access_state(kc, 'ad.test', client)
                self.assertFalse(state['enforced'])
                self.assertEqual(state['issues'], [issue])

    def test_writable_federation_is_refused(self):
        # LDAP_ONLY would write Keycloak membership changes to LDAP
        kc = FakeKeycloak()
        kc.edit_mode = 'WRITABLE'
        with self.assertRaises(self.access.PolicyError) as ctx:
            self.access.set_policy(kc, 'ad.test', kc.get('/ad.test/clients/c1'), 'engineering')
        self.assertEqual(ctx.exception.code, 'ldap_federation_not_found')
        self.assertEqual(kc.client_puts, [])

    def test_saml_clients_are_refused(self):
        kc = FakeKeycloak()
        client = dict(kc.get('/ad.test/clients/c1'), protocol='saml')
        with self.assertRaises(self.access.PolicyError) as ctx:
            self.access.set_policy(kc, 'ad.test', client, 'engineering')
        self.assertEqual(ctx.exception.code, 'protocol_not_supported')
        self.assertEqual(kc.client_puts, [])

    def test_live_state(self):
        kc = FakeKeycloak()
        self.access.set_policy(kc, 'ad.test', kc.get('/ad.test/clients/c1'), 'engineering')
        client = kc.get('/ad.test/clients/c1')
        state = self.access.live_state(kc, 'ad.test', client, lambda name: name == 'engineering', 'alice')
        self.assertEqual(state, {'ok':True,'ldap_connection':True,'group_in_ldap':True,'user_allowed':True,'issues':[]})
        # The stored bind password is used
        self.assertEqual(kc.ldap_request['bindCredential'], '**********')
        self.assertEqual(kc.ldap_request['componentId'], 'ldap1')
        kc.denied_users.add('u-bob')
        state = self.access.live_state(kc, 'ad.test', client, lambda name: False, 'bob')
        self.assertFalse(state['ok'])
        self.assertFalse(state['group_in_ldap'])
        self.assertFalse(state['user_allowed'])
        self.assertEqual(state['issues'], ['group_not_in_ldap'])
        kc.ldap_ok = False
        state = self.access.live_state(kc, 'ad.test', client, Mock(side_effect=AssertionError), 'nobody')
        self.assertEqual(state['issues'], ['ldap_connection_failed', 'user_not_found'])
        self.assertIsNone(state['group_in_ldap'])


if __name__ == '__main__':
    unittest.main(verbosity=2)

if __name__ == '__main__':
    unittest.main(verbosity=2)
