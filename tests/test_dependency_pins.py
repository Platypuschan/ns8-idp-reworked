"""Pins that Renovate updates in several files must stay coherent."""
from pathlib import Path
import json
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text()


class DependencyPinTests(unittest.TestCase):
    def test_postgres_pin_equal_in_label_and_build_script(self):
        pattern = r'docker\.io/library/postgres:([-0-9a-zA-Z_.]+)'
        a = re.findall(pattern, read('Containerfile'))
        b = re.findall(pattern, read('build-images.sh'))
        self.assertEqual(len(a), 1)
        self.assertEqual(a, b)

    def test_keycloak_version_equal_in_image_pom_and_tests(self):
        images = set(re.findall(r'keycloak/keycloak:(\d+\.\d+\.\d+)',
                                read('keycloak-providers/Containerfile') + read('tests/client-access/Containerfile')))
        pom = set(re.findall(r'<keycloak\.version>(\d+\.\d+\.\d+)</keycloak\.version>',
                             read('keycloak-providers/ns8-authenticators/pom.xml')))
        self.assertEqual(len(images), 1, images)
        self.assertEqual(images, pom)

    def test_yarn_equal_in_package_json_and_developer_image(self):
        version = json.loads(read('ui/package.json'))['packageManager'].removeprefix('yarn@')
        self.assertIn(f'@yarnpkg/cli-dist@{version}', read('ui/Containerfile'))

    def test_node_major_equal_in_production_and_developer_image(self):
        prod = re.search(r'node:(\d+)', read('Containerfile')).group(1)
        dev = re.search(r'node:(\d+)', read('ui/Containerfile')).group(1)
        self.assertEqual(prod, dev)

    def test_renovate_config_is_valid_json(self):
        json.loads(read('renovate.json'))


if __name__ == '__main__':
    unittest.main()
