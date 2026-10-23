import os
import tempfile
import unittest
from gitops_check import run_check, scan_file, detect_controller, check_config_separation


class TestGitOpsCheck(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write(self, relpath, content):
        full = os.path.join(self.tmpdir, relpath)
        os.makedirs(os.path.dirname(full), exist_ok=True) if os.path.dirname(relpath) else None
        with open(full, 'w', encoding='utf-8') as f:
            f.write(content)
        return full

    def test_detect_argocd(self):
        self._write('app.yaml', 'apiVersion: argoproj.io/v1alpha1\nkind: Application\n')
        controllers = detect_controller(self.tmpdir)
        self.assertIn('argocd', controllers)

    def test_detect_flux(self):
        self._write('ks.yaml', 'apiVersion: kustomize.toolkit.fluxcd.io/v1\nkind: Kustomization\n')
        controllers = detect_controller(self.tmpdir)
        self.assertIn('flux', controllers)

    def test_no_controller(self):
        self._write('readme.md', 'hello world')
        controllers = detect_controller(self.tmpdir)
        self.assertEqual(controllers, [])

    def test_plaintext_secret_detected(self):
        self._write('config.yaml', 'password: "supersecret123"\n')
        findings = scan_file(os.path.join(self.tmpdir, 'config.yaml'))
        self.assertTrue(len(findings) > 0)
        self.assertEqual(findings[0]['severity'], 'CRITICAL')

    def test_private_key_detected(self):
        self._write('key.txt', '-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n')
        findings = scan_file(os.path.join(self.tmpdir, 'key.txt'))
        self.assertTrue(len(findings) > 0)

    def test_aws_key_detected(self):
        self._write('creds.yaml', 'access_key: AKIAIOSFODNN7EXAMPLE\n')
        findings = scan_file(os.path.join(self.tmpdir, 'creds.yaml'))
        self.assertTrue(len(findings) > 0)

    def test_sealed_secret_not_flagged(self):
        self._write('secret.yaml', 'apiVersion: bitnami.com/v1alpha1\nkind: SealedSecret\nencrypted: "abc123"\n')
        has_sealed, has_plain, findings = __import__('gitops_check').check_secrets_externalized(self.tmpdir)
        self.assertTrue(has_sealed)

    def test_config_separation(self):
        self._write('kustomization.yaml', 'resources:\n- base\n')
        self._write('main.py', 'print("hello")')
        has_config, has_app = check_config_separation(self.tmpdir)
        self.assertTrue(has_config)
        self.assertTrue(has_app)

    def test_score_with_good_repo(self):
        self._write('app.yaml', 'apiVersion: argoproj.io/v1alpha1\nkind: Application\nsealed: true\n')
        self._write('kustomization.yaml', 'resources:\n- base\n')
        self._write('secret.yaml', 'kind: SealedSecret\n')
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_check(self.tmpdir, json_output=True)
        self.assertEqual(code, 0)

    def test_score_with_bad_repo(self):
        self._write('config.yaml', 'password: "supersecret123"\ntoken: "abcdefghij1234567890"\n')
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = run_check(self.tmpdir, json_output=True)
        self.assertEqual(code, 1)


if __name__ == '__main__':
    unittest.main()
