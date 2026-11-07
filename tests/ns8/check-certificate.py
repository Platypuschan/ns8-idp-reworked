#!/usr/bin/env python3
"""Real NS8 HTTPS auth check; output summaries, never codes or cookies."""
import base64
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import sys
from urllib.parse import urlencode, quote

host, realm, client, redirect, mode = sys.argv[1:]
verifier = secrets.token_urlsafe(48)
challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
url = 'https://' + host + '/realms/' + quote(realm, safe='') + '/protocol/openid-connect/auth?' + urlencode({
    'client_id':client, 'redirect_uri':redirect, 'response_type':'code', 'scope':'openid',
    'state':secrets.token_urlsafe(24), 'code_challenge_method':'S256', 'code_challenge':challenge})
args = ['curl', '-sSki', '--max-time', '30', '--resolve', host + ':443:127.0.0.1']
if mode == 'certificate':
    args += ['--cert', '/tmp/ns8-x509-native.crt', '--key', '/tmp/ns8-x509-native.key']
elif mode == 'forged':
    args += ['-H', 'X-Forwarded-Tls-Client-Cert: ' + quote(Path('/tmp/ns8-x509-native.crt').read_text()),
             '-H', 'X-NS8-X509-Proxy: forged']
elif mode != 'none':
    raise SystemExit('Unknown check mode')
response = subprocess.run([*args, url], check=True, capture_output=True, text=True).stdout
headers, _, body = response.partition('\n\n')
locations = [line for line in headers.splitlines() if line.lower().startswith('location:')]
print(json.dumps({'status':int(headers.splitlines()[0].split()[1]),
    'code':any('code=' in line for line in locations), 'password_form':'kc-form-login' in body}))
