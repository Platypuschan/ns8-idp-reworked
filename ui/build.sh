#!/bin/sh
# Node 26 no longer bundles Corepack. Bootstrap the exact declared Yarn CLI.
set -eu
version=$(node -p 'require("./package.json").packageManager.replace(/^yarn@/, "")')
case "$version" in
    ''|*[!0-9.]*) echo "Expected an exact yarn@ version in packageManager" >&2; exit 1 ;;
esac
node --version
npm exec --yes --package="@yarnpkg/cli-dist@$version" -- yarn --version
npm exec --yes --package="@yarnpkg/cli-dist@$version" -- yarn install --immutable
npm exec --yes --package="@yarnpkg/cli-dist@$version" -- yarn build
