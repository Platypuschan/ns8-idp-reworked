#!/usr/bin/env python3
"""Remove only a marked fixture's containers and private local material.
Remove its Android certificate/app/reverse mapping separately as documented.
"""
import json
from pathlib import Path
import re
import subprocess
import sys

folder = Path(sys.argv[1]).resolve()
meta = json.loads((folder / 'android-fixture.json').read_text())
if not folder.name.startswith('ns8-x509-') or meta.get('fixture_kind') != 'ns8-x509':
    raise SystemExit('Expected a marked disposable NS8 X509 fixture')
match = re.fullmatch('vw-sso-([a-f0-9]{8})', meta['network'])
if not match:
    raise SystemExit('Unexpected fixture network')
suffix = match.group(1)
for field, prefix in [('proxy','x509-proxy-'), ('keycloak','vw-kc-'), ('samba','vw-ad-')]:
    if meta[field] != prefix + suffix:
        raise SystemExit('Unexpected fixture container')
for field in ('proxy', 'keycloak', 'samba'):
    subprocess.run(['podman', 'stop', '--time', '10', meta[field]], check=True)
    subprocess.run(['podman', 'rm', meta[field]], check=True)
subprocess.run(['podman', 'network', 'rm', meta['network']], check=True)
for path in folder.rglob('*'):
    if path.is_file() and (path.suffix in ('.key', '.p12', '.apk', '.keystore')
                           or path.name == 'android-fixture.json'
                           or path.parent == folder / 'configs'):
        path.unlink()
print('Fixture stopped; local private material removed')
