#!/usr/bin/env python3
"""Prepare the public native OIDC client in an X509_KEEP test fixture only."""
import importlib.util
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

folder = Path(sys.argv[1]).resolve()
meta = json.loads((folder / 'android-fixture.json').read_text())
if meta.get('fixture_kind') != 'ns8-x509' or urlsplit(meta['admin_url']).hostname != '127.0.0.1':
    raise SystemExit('Expected an isolated loopback NS8 X509 fixture')
root = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location('fixture', root / 'tests/client-access/run.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)
kc = fixture.Admin(meta['admin_url'], meta['password'])
client = {'clientId':'android-x509-test', 'enabled':True, 'protocol':'openid-connect',
    'publicClient':True, 'standardFlowEnabled':True, 'directAccessGrantsEnabled':False,
    'redirectUris':['org.nethserver.x509test:/callback'],
    'attributes':{'pkce.code.challenge.method':'S256'}}
existing = kc.find_client('ad.test', client['clientId'])
if existing is None:
    kc.post('/ad.test/clients', client)
else:
    kc.put('/ad.test/clients/' + existing['id'], {**existing, **client})
client = kc.find_client('ad.test', client['clientId'])
fixture.idpaccess.set_policy(kc, 'ad.test', client, 'services_vaultwarden')
(folder / 'android-config.json').write_text(json.dumps({'issuer': meta['url'] + '/realms/ad.test'}))
print('Isolated native S256 PKCE client ready; adb reverse port:', meta['port'])
