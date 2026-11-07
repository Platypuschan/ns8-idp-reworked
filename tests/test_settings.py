"""Site policies: defaults, persistence semantics and their effects."""
import importlib.util
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / 'imageroot/pypkg'))
import idpsettings


class Settings(unittest.TestCase):
    def test_unset_means_the_module_default(self):
        with patch.dict(os.environ, clear=True):
            self.assertEqual(idpsettings.current(), idpsettings.DEFAULTS)

    def test_stored_values_win_over_defaults(self):
        with patch.dict(os.environ, {'IDP_STRICT_CLIENT_URIS': '0', 'IDP_RESTRICT_ADMIN_CONSOLE': '1'}):
            self.assertFalse(idpsettings.get('strict_client_uris'))
            self.assertTrue(idpsettings.get('restrict_admin_console'))

    def test_an_omitted_request_field_keeps_the_stored_value(self):
        with patch.dict(os.environ, {'IDP_STRICT_CLIENT_URIS': '0'}):
            self.assertFalse(idpsettings.get('strict_client_uris', {'host': 'x'}))
            self.assertTrue(idpsettings.get('strict_client_uris', {'strict_client_uris': True}))


class Effects(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        agent = types.ModuleType('agent')
        agent.__path__ = []
        ldapproxy = types.ModuleType('agent.ldapproxy')
        domain = {'schema': 'ad', 'base_dn': 'dc=ad,dc=test'}
        ldapproxy.Ldapproxy = lambda: types.SimpleNamespace(
            get_domain=lambda name: domain, get_ldap_groups_search_filter_clause=lambda name: '')
        agent.ldapproxy = ldapproxy
        kcadmin = types.ModuleType('kcadmin')
        spec = importlib.util.spec_from_file_location('idprealm_settings', ROOT / 'imageroot/pypkg/idprealm.py')
        cls.realm = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'agent': agent, 'agent.ldapproxy': ldapproxy, 'kcadmin': kcadmin}):
            spec.loader.exec_module(cls.realm)

    def test_group_mapper_mode_follows_the_setting(self):
        with patch.dict(os.environ, {'IDP_DIRECTORY_GROUPS_ONLY': '1'}):
            self.assertEqual(self.realm.group_mapper_config('ad.test')['mode'], ['LDAP_ONLY'])
        with patch.dict(os.environ, {'IDP_DIRECTORY_GROUPS_ONLY': '0'}):
            self.assertEqual(self.realm.group_mapper_config('ad.test')['mode'], ['READ_ONLY'])

    def registered(self, setting):
        kc = types.SimpleNamespace(get=lambda *a, **k: [], post=lambda *a, **k: None)
        with patch.dict(os.environ, {'IDP_STRICT_CLIENT_URIS': setting}), \
                patch.object(self.realm, 'validate_client_endpoints') as validate:
            try:
                self.realm.ensure_client(kc, 'ad.test', 'app1', ['http://app.test/cb'])
            except Exception:
                pass  # The fake Keycloak stops the rest of the registration.
        return validate.called

    def test_strict_uris_switch_controls_the_validation(self):
        self.assertTrue(self.registered('1'))
        self.assertFalse(self.registered('0'))
