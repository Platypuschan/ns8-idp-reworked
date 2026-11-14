// Run in the digest-pinned official Renovate image from renovate-policy.yml.
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import { createRequire } from 'node:module';
const require = createRequire('/usr/local/renovate/package.json');
const { inc } = require('semver');
const { applyPackageRules } = await import('/usr/local/renovate/dist/util/package-rules/index.js');
const { regEx } = await import('/usr/local/renovate/dist/util/regex.js');
const raw = JSON.parse(await fs.readFile('renovate.json', 'utf8'));
for (const file of ['Containerfile', 'keycloak-providers/pom.xml', 'keycloak-providers/Containerfile', 'imageroot/etc/keycloak.env', 'ui/package.json', 'build-images.sh']) {
  const result = await applyPackageRules({ ...raw, packageFile: file, depName: 'fixture', updateType: 'patch' });
  const bump = result.bumpVersions?.find(b => b.name === 'Stable module version');
  assert.ok(bump, `missing release bump for ${file}`);
  assert.deepEqual(bump.filePatterns, ['VERSION']);
  assert.equal(bump.bumpType, 'patch');
  assert.equal(regEx(bump.matchStrings[0]).exec('0.1.0\n')?.groups.version, '0.1.0');
  assert.equal(regEx(bump.matchStrings[0]).exec('0.1.0-rc.5\n'), null, 'must not graduate an RC');
}
for (const file of ['.github/workflows/test-module.yml', 'docs/PRERELEASE.md', 'prototype/Containerfile']) {
  const result = await applyPackageRules({ ...raw, packageFile: file, depName: 'fixture', updateType: 'patch' });
  assert.equal(result.bumpVersions?.length ?? 0, 0, `unexpected release bump for ${file}`);
}
for (const name of ['quay.io/keycloak/keycloak', 'org.keycloak:keycloak-core', 'postgres', 'docker.io/library/postgres']) {
  for (const type of ['patch', 'minor', 'major']) {
    const result = await applyPackageRules({ ...raw, packageFile: 'Containerfile', depName: name, packageName: name, updateType: type });
    assert.equal(result.automerge, false, `${name}/${type} must remain manual`);
    if (type === 'major') assert.equal(result.dependencyDashboardApproval, true);
  }
}
assert.equal(inc('0.1.0', 'patch'), '0.1.1');
assert.equal(inc('0.1.0-rc.5', 'patch'), '0.1.0', 'patch is not rc.6');
assert.equal(raw.bumpVersions?.length ?? 0, 0, 'no unscoped bump');
console.log('PASS native applyPackageRules: six release paths, three exclusions, twelve runtime approval cases; stable-only semver bump');
