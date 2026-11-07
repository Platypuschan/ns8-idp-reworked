"""Replay the certificate Robot scenario with only its SSH/API seam stubbed.

Requires Robot Framework and SSHLibrary (the NS8 test runner dependencies).
No guest, certificate authenticator or Traefik behavior is simulated as verified.
"""
import io
import json
from pathlib import Path
import tempfile
import unittest

try:
    from robot.api import TestSuite
except ImportError:
    TestSuite = None


@unittest.skipIf(TestSuite is None, 'requires Robot Framework')
class CertificateReadinessTests(unittest.TestCase):
    def replay(self, responses):
        suite = TestSuite.from_file_system(str(Path(__file__).with_name('25__certificates.robot')))
        suite.setup = None
        suite.tests = [test for test in suite.tests if test.name == 'Revoke and disable certificate login']
        for name, value in {'module_id': 'idp1', 'DEVICE_FINGERPRINT': 'a' * 64}.items():
            suite.resource.variables.create('${' + name + '}', [value])
        suite.resource.variables.create('@{responses}', [json.dumps(response) for response in responses])
        run = suite.resource.keywords.create('Run task', args=['@{args}', '&{kwargs}'])
        run.body.create_keyword('Evaluate', args=["dict(enabled=False, certificates=[])"], assign=['${result}'])
        run.body.create_return(['${result}'])
        execute = suite.resource.keywords.create('Execute Command', args=['${command}', '&{kwargs}'])
        execute.body.create_keyword('Evaluate', args=["$responses.pop(0) if 'ns8-x509-check.py' in $command else ''"], assign=['${output}'])
        execute.body.create_return(['${output}', '${EMPTY}', '${0}'])
        # Keep the real bounded retry semantics, but shorten the regression's clock.
        retry = suite.resource.keywords.create('Retry test', args=['${keyword}', '@{args}'])
        retry.body.create_keyword('Wait Until Keyword Succeeds', args=['0.1 seconds', '0.01 seconds', '${keyword}', '@{args}'])
        with tempfile.TemporaryDirectory() as folder:
            result = suite.run(outputdir=folder, log=None, report=None, stdout=io.StringIO(), stderr=io.StringIO())
        return result.suite.tests[0]

    def test_transient_route_404_then_password_form_recovers(self):
        denied = dict(status=200, code=False, password_form=True)
        result = self.replay([denied, dict(status=404, code=False, password_form=False), denied])
        self.assertEqual(result.status, 'PASS', result.message)

    def test_persistent_route_404_is_not_accepted(self):
        result = self.replay([
            dict(status=200, code=False, password_form=True),
            *[dict(status=404, code=False, password_form=False) for _ in range(100)],
        ])
        self.assertEqual(result.status, 'FAIL')
        self.assertIn('404 != 200', result.message)

    def test_revoked_certificate_success_fails_immediately(self):
        result = self.replay([
            dict(status=302, code=True, password_form=False),
            dict(status=200, code=False, password_form=True),
        ])
        self.assertEqual(result.status, 'FAIL')
        self.assertIn('True != False', result.message)
        # A retry failure would wrap this in "Keyword ... failed after retrying".
        self.assertNotIn('retrying', result.message)

    def test_http_200_without_password_form_is_not_accepted(self):
        result = self.replay([
            dict(status=200, code=False, password_form=True),
            *[dict(status=200, code=False, password_form=False) for _ in range(100)],
        ])
        self.assertEqual(result.status, 'FAIL')
        self.assertIn("'False' should be true", result.message)


if __name__ == '__main__':
    unittest.main()
