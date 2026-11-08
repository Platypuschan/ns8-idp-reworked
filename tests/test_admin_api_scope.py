"""kc-admin-api scope of the ns8-agent client (Keycloak 26.8.2 admin API audience)."""
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / 'imageroot/pypkg'))
sys.modules.setdefault('agent', types.ModuleType('agent'))
import kcadmin  # noqa: E402


class FakeKc:
    def __init__(self, scopes):
        self.scopes, self.puts = scopes, []

    def get(self, path, params=None):
        assert path == '/master/client-scopes'
        return self.scopes

    def put(self, path, data=None):
        self.puts.append(path)


class AdminApiScope(unittest.TestCase):
    def test_scope_is_assigned_as_default(self):
        kc = FakeKc([{'name': 'profile', 'id': 'p'}, {'name': 'kc-admin-api', 'id': 's1'}])
        self.assertTrue(kcadmin.ensure_admin_api_scope(kc, 'c1'))
        self.assertEqual(kc.puts, ['/master/clients/c1/default-client-scopes/s1'])

    def test_older_keycloak_has_no_scope(self):
        kc = FakeKc([{'name': 'profile', 'id': 'p'}])
        self.assertFalse(kcadmin.ensure_admin_api_scope(kc, 'c1'))
        self.assertEqual(kc.puts, [])

    def test_credentials_file_state(self):
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                self.assertFalse(kcadmin.agent_secret_current())
                Path(kcadmin.AGENT_SECRET_FILE).write_text(json.dumps({'client_id': 'ns8-agent', 'client_secret': 'x'}))
                self.assertFalse(kcadmin.agent_secret_current())
                Path(kcadmin.AGENT_SECRET_FILE).write_text(json.dumps({'client_id': 'ns8-agent', 'client_secret': 'x', 'admin_api_scope': True}))
                self.assertTrue(kcadmin.agent_secret_current())
                Path(kcadmin.AGENT_SECRET_FILE).write_text('not json')
                self.assertFalse(kcadmin.agent_secret_current())
            finally:
                os.chdir(cwd)


if __name__ == '__main__':
    unittest.main()
