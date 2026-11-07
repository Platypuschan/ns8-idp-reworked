"""Client URI compatibility and trust-boundary regression checks."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

class RegistrationValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        names = ('agent', 'agent.ldapproxy', 'agent.tasks', 'kcadmin', 'cluster', 'cluster.userdomains')
        with patch.dict(sys.modules, {name: types.ModuleType(name) for name in names}):
            spec = importlib.util.spec_from_file_location('registration_policy', ROOT / 'imageroot/pypkg/idprealm.py')
            cls.realm = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.realm)

    def validate(self, redirects=(), logout=(), origins=(), audience=()):
        self.realm.validate_client_endpoints(redirects, logout, origins, audience)

    def test_exact_web_and_native_callbacks_and_logout_fallback_remain_usable(self):
        self.validate(['https://vault.example.test/identity/connect/oidc-signin',
            'bitwarden://sso-callback', 'com.example.client:/oauth2redirect',
            'http://127.0.0.1:49321/callback', 'http://localhost:5000/callback'],
            ['https://vault.example.test/*'], ['https://vault.example.test', '+'], ['dovecot'])

    def test_remote_plaintext_wildcards_credentials_and_fragments_are_rejected(self):
        for uri in ('http://vault.example.test/callback', 'https://*.example.test/callback',
                'https://vault.example.test/*', 'https://user:pass@vault.example.test/callback',
                'https://vault.example.test/callback#fragment', 'javascript:alert(1)',
                'data:text/html,test', 'file:///tmp/secret', 'https://vault.example.test/\ncallback'):
            with self.subTest(uri=uri), self.assertRaises(ValueError):
                self.validate([uri])

    def test_origins_and_privileged_audiences_cannot_be_broadened(self):
        for origin in ('*', 'https://*.example.test', 'https://example.test/path', 'bitwarden://sso-callback'):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                self.validate(origins=[origin])
        for audience in ('realm-management', 'admin-cli', 'account', 'other/client'):
            with self.subTest(audience=audience), self.assertRaises(ValueError):
                self.validate(audience=[audience])
