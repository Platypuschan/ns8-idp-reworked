#!/usr/bin/env python3
"""Negative regressions for P6/P7 on a real disposable AD and Keycloak."""
import copy
import unittest
from urllib.parse import parse_qs, urlsplit
from run import LoginTests, idprealm, idpaccess, requests

class SecurityDecisions(LoginTests):
    def new_required(self):
        name = 'required-test'
        idprealm.ensure_client(self.kc, 'ad.test', name,
            redirect_uris=[self.vw_url + '/identity/connect/oidc-signin'], access_required=True)
        client = self.kc.find_client('ad.test', name)
        self.addCleanup(lambda: self.kc.delete('/ad.test/clients/' + client['id']))
        idpaccess.set_policy(self.kc, 'ad.test', client, 'services_vaultwarden')
        return self.kc.find_client('ad.test', name)

    def test_supported_policy_edit_cannot_move_the_consumer_pin(self):
        from run import cmd
        group = 'policy-other'
        cmd('podman', 'exec', self.samba, 'samba-tool', 'group', 'add', group)
        self.addCleanup(lambda: cmd('podman', 'exec', self.samba, 'samba-tool', 'group', 'delete', group, check=False))
        cmd('podman', 'exec', self.samba, 'samba-tool', 'group', 'addmembers', group, 'denied')
        client = self.new_required()
        try:
            idpaccess.set_policy(self.kc, 'ad.test', client, group)
        except idpaccess.PolicyError as error:
            self.assertEqual(error.code, 'policy_incomplete')
        after = self.kc.find_client('ad.test', 'required-test')
        self.assertEqual(after['attributes']['ns8.access_expected_group_id'], client['attributes']['ns8.access_expected_group_id'])
        _, response, target, _ = self.auth('denied', client='required-test')
        self.assertIsNone(target)
        self.assertEqual(response.status_code, 403)

    def test_explicit_consumer_binding_controls_policy_reconfiguration(self):
        from run import cmd
        group, name = 'consumer-other', 'consumer-bound'
        cmd('podman', 'exec', self.samba, 'samba-tool', 'group', 'add', group)
        self.addCleanup(lambda: cmd('podman', 'exec', self.samba, 'samba-tool', 'group', 'delete', group, check=False))
        cmd('podman', 'exec', self.samba, 'samba-tool', 'group', 'addmembers', group, 'denied')
        options = {'redirect_uris': [self.vw_url + '/identity/connect/oidc-signin'], 'access_required': True}
        idprealm.ensure_client(self.kc, 'ad.test', name,
            expected_access_group='services_vaultwarden', **options)
        client = self.kc.find_client('ad.test', name)
        self.addCleanup(lambda: self.kc.delete('/ad.test/clients/' + client['id']))
        self.assertEqual(client['attributes'][idpaccess.EXPECTED_SOURCE], 'consumer')
        state = idpaccess.set_policy(self.kc, 'ad.test', client, 'services_vaultwarden')
        self.assertTrue(state['enforced'])
        with self.assertRaises(idpaccess.PolicyError):
            idpaccess.set_policy(self.kc, 'ad.test', self.kc.find_client('ad.test', name), group)
        _, response, target, _ = self.auth('denied', client=name)
        self.assertIsNone(target)
        self.assertEqual(response.status_code, 403)
        # Only an explicit consumer registration for the newly configured
        # group may advance the independent expectation.
        idprealm.ensure_client(self.kc, 'ad.test', name, expected_access_group=group, **options)
        after = self.kc.find_client('ad.test', name)
        self.assertTrue(idpaccess.access_state(self.kc, 'ad.test', after)['enforced'])
        _, response, target, _ = self.auth('denied', client=name)
        self.assertIn('code=', target or '')
        _, response, target, _ = self.auth('allowed', client=name)
        self.assertIsNone(target)
        self.assertEqual(response.status_code, 403)

    def test_fresh_required_registration_is_closed_before_policy_assignment(self):
        name = 'fresh-required'
        idprealm.ensure_client(self.kc, 'ad.test', name,
            redirect_uris=[self.vw_url + '/identity/connect/oidc-signin'], access_required=True)
        client = self.kc.find_client('ad.test', name)
        self.addCleanup(lambda: self.kc.delete('/ad.test/clients/' + client['id']))
        _, response, target, _ = self.auth('allowed', client=name)
        self.assertIsNone(target)
        self.assertEqual(response.status_code, 403)
        mappers = self.kc.get('/ad.test/clients/' + client['id'] + '/protocol-mappers/models')
        self.assertTrue(any(m.get('protocolMapper') == idpaccess.TOKEN_GATE for m in mappers))

    def test_required_policy_removed_denies_cookie_and_code_redemption(self):
        client = self.new_required()
        secret = self.kc.get('/ad.test/clients/' + client['id'] + '/client-secret')['value']
        session, _, target, verifier = self.auth('allowed', client='required-test')
        self.assertIn('code=', target or '')
        idpaccess.clear_policy(self.kc, 'ad.test', client)
        after = self.kc.find_client('ad.test', 'required-test')
        self.assertEqual(after['attributes']['ns8.access_required'], 'true')
        self.assertFalse(idpaccess.access_state(self.kc, 'ad.test', after)['enforced'])
        _, response, target2, _ = self.auth('allowed', session=session, client='required-test', require_cookie=True)
        self.assertIsNone(target2)
        self.assertEqual(response.status_code, 403)
        token = requests.post(self.url + '/realms/ad.test/protocol/openid-connect/token', data={
            'grant_type': 'authorization_code', 'client_id': 'required-test', 'client_secret': secret,
            'code': parse_qs(urlsplit(target).query)['code'][0], 'code_verifier': verifier,
            'redirect_uri': self.vw_url + '/identity/connect/oidc-signin'}, timeout=20)
        self.assertEqual(token.status_code, 403, token.text)

    def test_changed_group_is_not_reapproved_by_registration(self):
        client = self.new_required()
        changed = copy.deepcopy(client)
        # A different existing group, not a nonexistent ID.
        groups = self.kc.get('/ad.test/groups')
        other = next(g for g in groups if g['id'] != client['attributes']['ns8.access_group_id'])
        changed['attributes']['ns8.access_group_id'] = other['id']
        self.kc.put('/ad.test/clients/' + client['id'], changed)
        idprealm.ensure_client(self.kc, 'ad.test', 'required-test', access_required=True)
        after = self.kc.find_client('ad.test', 'required-test')
        self.assertEqual(after['attributes']['ns8.access_expected_group_id'], client['attributes']['ns8.access_group_id'])
        self.assertIn('expected_group_mismatch', idpaccess.access_state(self.kc, 'ad.test', after)['issues'])
        # Restore callback registration without blessing the changed policy.
        idprealm.ensure_client(self.kc, 'ad.test', 'required-test',
            redirect_uris=[self.vw_url + '/identity/connect/oidc-signin'])
        _, response, target, _ = self.auth('allowed', client='required-test')
        self.assertIsNone(target)
        self.assertEqual(response.status_code, 403)

    def test_required_client_without_initial_policy_denies(self):
        client = self.new_required()
        for key in ('ns8.access_policy', 'ns8.access_group_id', 'ns8.access_expected_group_id'):
            client['attributes'][key] = ''
        self.kc.put('/ad.test/clients/' + client['id'], client)
        _, response, target, _ = self.auth('allowed', client='required-test')
        self.assertIsNone(target)
        self.assertEqual(response.status_code, 403)

    def test_local_membership_cannot_authorize_an_ldap_nonmember(self):
        # Import the LDAP nonmember through the unrestricted client first.
        self.auth('denied', client='other1')
        user = self.kc.get('/ad.test/users', params={'username': 'denied', 'exact': 'true'})[0]
        group = self.kc.get('/ad.test/group-by-path/services_vaultwarden')
        path = '/ad.test/users/' + user['id'] + '/groups/' + group['id']
        storage, mapper = idpaccess.group_mapper(self.kc, 'ad.test')
        mapper['config']['mode'] = ['READ_ONLY']
        self.kc.put('/ad.test/components/' + mapper['id'], mapper)
        try:
            self.kc.put(path)
        finally:
            mapper['config']['mode'] = ['LDAP_ONLY']
            self.kc.put('/ad.test/components/' + mapper['id'], mapper)
        from run import cmd
        members = cmd('podman', 'exec', self.samba, 'samba-tool', 'group', 'listmembers', 'services_vaultwarden').stdout.splitlines()
        self.assertNotIn('denied', members, 'test must inject a local membership, not an AD membership')
        _, response, target, _ = self.auth('denied')
        self.assertIsNone(target)
        self.assertEqual(response.status_code, 403)

    def test_token_request_reuses_one_membership_lookup(self):
        from run import cmd
        client = self.new_required()
        secret = self.kc.get('/ad.test/clients/' + client['id'] + '/client-secret')['value']
        _, _, target, verifier = self.auth('allowed', client='required-test')
        before = cmd('podman', 'logs', self.keycloak).stdout.count('NS8 membership lookup')
        response = requests.post(self.url + '/realms/ad.test/protocol/openid-connect/token', data={
            'grant_type': 'authorization_code', 'client_id': 'required-test', 'client_secret': secret,
            'code': parse_qs(urlsplit(target).query)['code'][0], 'code_verifier': verifier,
            'redirect_uri': self.vw_url + '/identity/connect/oidc-signin'}, timeout=20)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn('access_token', response.json())
        self.assertIn('id_token', response.json())
        after = cmd('podman', 'logs', self.keycloak).stdout.count('NS8 membership lookup')
        self.assertEqual(after - before, 1, 'access and ID token must share a single membership query')
        print('Access + ID token: one live membership lookup in the token request', flush=True)

if __name__ == '__main__':
    suite = unittest.TestSuite(SecurityDecisions(name) for name in SecurityDecisions.__dict__ if name.startswith('test_'))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(not result.wasSuccessful())
