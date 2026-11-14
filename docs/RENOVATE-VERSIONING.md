# Renovate and the module release version

`VERSION` on main is **0.1.0**, not 0.1.0-rc.5 (verified against main
34fd5e8 and the VERSION history). Backup PR #38 did not change it. This PR
does not retroactively release that work or change VERSION itself.

Release-effective inputs are `Containerfile`, `keycloak-providers/**`,
`imageroot/**`, `ui/**`, and `build-images.sh`. The production Containerfile
copies imageroot and the UI; the prerelease workflow also builds the Keycloak
providers. build-images.sh is the alternate module/runtime build recipe.
Documentation, tests and workflow-only edits do not require a version bump.

For these inputs, Renovate bumps an **already stable** VERSION by one patch
per update branch. This is a module packaging revision, not the upstream
Keycloak/PostgreSQL major/minor version. VERSION matching is whole-file and
stable-only. Native applyPackageRules tests cover all paths and keep the
existing Keycloak/PostgreSQL manual merge and major approval rules intact.

Do not use patch/minor/major bumpVersions to increment an RC: Renovate calls
semver.inc; 0.1.0-rc.5 + patch becomes 0.1.0, not 0.1.0-rc.6. An RC is left
untouched deliberately. Increment it manually in the dependency PR. The
release-version CI guard requires an increase for release-effective changes,
including manual RC changes, and rejects regressions or invalid syntax. It
uses the existing prerelease.yml grammar X.Y.Z[-rc.N]. Existing historical
changes on main are not audited retroactively by this guard.

Promotion remains a human decision: dispatch `prerelease.yml` on main with
`publish=true` only after explicit approval; `publish=false` tests candidates.
No workflow_run promotion, release dispatch, new automerge permissions, ruleset
changes or required-check renames are introduced. The new checks are additive;
they are not required by the unchanged ruleset (currently client-access).
A bot version bump is neither permission to publish nor proof of a live release.
