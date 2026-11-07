#!/usr/bin/env python3
"""Install five reviewed source files ONLY in the disposable QEMU test guest.

Run as the traefik module user through runagent, never against production.
The standard suite first checks rejection by the unmodified proxy.
"""
import os
from pathlib import Path
import shutil
import socket

if not socket.getfqdn().startswith('ns8-ci'):
    raise SystemExit('This fixture is restricted to the ns8-ci QEMU guest')
root = Path(os.environ['AGENT_INSTALL_DIR'])
files = {'writeconfig': 'actions/set-route/20writeconfig',
         'waitsync': 'actions/set-route/29waitsync',
         'getroute': 'pypkg/get_route.py',
         'input': 'actions/set-route/validate-input.json',
         'output': 'actions/get-route/validate-output.json'}
for name, target in files.items():
    if not (root / target).is_file():
        raise SystemExit('Unexpected module installation layout: ' + target)
for name, target in files.items():
    shutil.copyfile('/tmp/ns8-x509-proxy-' + name, root / target)
print('Disposable NS8 proxy capability fixture installed')
