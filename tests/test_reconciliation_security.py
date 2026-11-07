"""A stale replica or failed authoritative read must not delete a client."""
import contextlib
import runpy
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / 'imageroot/pypkg'))

class CleanupAuthority(unittest.TestCase):
    def run_cleanup(self, bound='ad.test', failure=False):
        agent = types.ModuleType('agent')
        ldap = types.ModuleType('agent.ldapproxy')
        agent.ldapproxy = ldap
        agent.SD_WARNING = ''
        agent.exclusive_file_lock = lambda name: contextlib.nullcontext()
        leader = Mock()
        leader.hget.side_effect = ConnectionError('leader unavailable') if failure else None
        leader.hget.return_value = bound
        replica = Mock()
        replica.hget.return_value = ''
        agent.redis_connect = Mock(side_effect=lambda **kw: replica if kw.get('use_replica') else leader)
        agent.get_smarthost_settings = lambda rdb: {'enabled': False}
        ldap.Ldapproxy = lambda: types.SimpleNamespace(get_domains_list=lambda: [])
        realm = types.ModuleType('idprealm')
        realm.realms_lock = contextlib.nullcontext
        realm.MODULE_ATTRIBUTE = 'ns8.module_id'
        realm.module_clients = lambda kc, name: [{'id': 'client', 'clientId': 'app1', 'attributes': {'ns8.module_id': 'app1'}}]
        kc = Mock()
        admin = types.ModuleType('kcadmin')
        ready = False
        def wait_ready():
            nonlocal ready
            ready = True
        def managed_realms(client):
            if not ready:
                raise RuntimeError('HTTP 503: Bootstrap in progress')
            return ['ad.test']
        admin.wait_ready = wait_ready
        admin.agent_client = lambda: kc
        admin.managed_realms = managed_realms
        access = types.ModuleType('idpaccess')
        access.reconcile = Mock()
        legacy = types.ModuleType('idplegacy')
        with patch.dict(sys.modules, {'agent': agent, 'agent.ldapproxy': ldap, 'idprealm': realm,
                'kcadmin': admin, 'idpaccess': access, 'idplegacy': legacy}):
            if failure:
                with self.assertRaises(ConnectionError):
                    runpy.run_path(str(ROOT / 'imageroot/bin/keycloak-post-start'))
            else:
                runpy.run_path(str(ROOT / 'imageroot/bin/keycloak-post-start'))
        return kc

    def test_stale_replica_cannot_delete_a_current_binding(self):
        self.run_cleanup().delete.assert_not_called()

    def test_authoritative_failure_never_means_unbound(self):
        self.run_cleanup(failure=True).delete.assert_not_called()

    def test_authoritative_unbind_still_cleans_up(self):
        self.run_cleanup(bound='').delete.assert_called_once_with('/ad.test/clients/client')
