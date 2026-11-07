#!/usr/bin/env python3
"""Prepare the narrowly scoped upstream patch in a disposable source tree.

Never modifies installed NS8 services. Output can be inspected/built using
the normal ns8-traefik workflow. Refuse to patch a different upstream base.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import urllib.request

def prepare(destination):
    here = Path(__file__).resolve().parent
    base = json.loads((here / 'base.json').read_text())
    destination = Path(destination)
    for file, expected in base['files'].items():
        target = destination / file
        if target.exists():
            content = target.read_bytes()
        else:
            url = f"https://raw.githubusercontent.com/{base['repository']}/{base['commit']}/{file}"
            with urllib.request.urlopen(url, timeout=30) as response:
                content = response.read()
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError('Upstream base mismatch: ' + file)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    subprocess.run(['patch', '-p1', '--batch', '-i', str(here / 'client-certificates.patch')],
                   cwd=destination, check=True, capture_output=True)
    return destination

if __name__ == '__main__':
    prepare(sys.argv[1])
