"""Bounded, offline guards for the production UI build contract."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class UIBuildTests(unittest.TestCase):
    def test_production_build_uses_pinned_yarn_without_corepack(self):
        self.assertEqual(json.loads((ROOT / 'ui/package.json').read_text())['packageManager'], 'yarn@4.18.1')
        recipe = (ROOT / 'Containerfile').read_text()
        self.assertIn('RUN sh ./build.sh', recipe)
        bootstrap = (ROOT / 'ui/build.sh').read_text()
        self.assertIn('@yarnpkg/cli-dist@', bootstrap)
        self.assertIn('packageManager', bootstrap)
        self.assertIn('install --immutable', bootstrap)
        self.assertIn('yarn build', bootstrap)
        self.assertNotIn('corepack enable', recipe + bootstrap + (ROOT / 'build-images.sh').read_text())

    def test_developer_image_provides_project_pinned_yarn_without_corepack(self):
        version = json.loads((ROOT / 'ui/package.json').read_text())['packageManager'].removeprefix('yarn@')
        recipe = (ROOT / 'ui/Containerfile').read_text()
        self.assertIn(f'npm install --global --force @yarnpkg/cli-dist@{version}', recipe)
        self.assertNotIn('corepack', recipe)
        self.assertNotIn('yarn set version stable', recipe)
        self.assertIn('WORKDIR /app', recipe)
        self.assertIn('ENV NODE_OPTIONS=--openssl-legacy-provider', recipe)
        self.assertIn('EXPOSE 8080', recipe)
        self.assertIn('ENTRYPOINT ["./container-entrypoint.sh"]', recipe)

    def test_alternate_builder_uses_production_image(self):
        script = (ROOT / 'build-images.sh').read_text()
        self.assertIn('Containerfile', script)
        self.assertIn('sh ./build.sh', script)
        self.assertNotIn('node:24.', script)

    def test_ci_builds_actual_production_stage(self):
        workflow = (ROOT / '.github/workflows/test-ui-build-renovate.yml').read_text()
        self.assertIn('docker build --target ui --file Containerfile', workflow)
        self.assertIn('timeout-minutes:', workflow)
        self.assertNotIn('setup-node', workflow)
        self.assertNotIn('corepack enable', workflow)


if __name__ == '__main__':
    unittest.main()
