import importlib.machinery
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / '.github/scripts/check-release-version'

class ReleaseVersionTests(unittest.TestCase):
    def test_release_input_requires_increase(self):
        self.assertTrue(SCRIPT.is_file(), 'release version guard missing')
        loader = importlib.machinery.SourceFileLoader('version_guard', str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        module = importlib.util.module_from_spec(spec)
        loader.exec_module(module)
        for path in ['Containerfile', 'keycloak-providers/pom.xml', 'imageroot/etc/keycloak.env', 'ui/yarn.lock', 'build-images.sh']:
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    module.check('0.1.0', '0.1.0', [path])
                module.check('0.1.0', '0.1.1', [path])
                module.check('0.1.0-rc.5', '0.1.0-rc.6', [path])
        module.check('0.1.0', '0.1.0', ['docs/PRERELEASE.md'])
        module.check('0.1.0', '0.1.0', ['.github/workflows/prerelease.yml'])
        for old, new in [('0.1.0', '0.1.0-rc.6'), ('0.1.0-rc.6', '0.1.0-rc.5'), ('0.1.0', 'invalid')]:
            with self.assertRaises(ValueError):
                module.check(old, new, ['VERSION'])
        module.check('0.1.0-rc.6', '0.1.0', ['VERSION'])
