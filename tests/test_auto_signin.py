import base64
import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from nacl import encoding, public
import auto_signin


class AutomaticSignInTests(unittest.TestCase):
    def test_secret_is_encrypted_for_repository_key_and_not_printed(self):
        private = public.PrivateKey.generate()
        key = private.public_key.encode(encoding.Base64Encoder()).decode('ascii')
        get = Mock(status_code=200)
        get.json.return_value = {'key_id': 'test-key', 'key': key}
        put = Mock(status_code=204)
        stdout = io.StringIO()
        with patch.dict(os.environ, {'GH_PAT': 'test-token', 'GITHUB_REPOSITORY': 'owner/repo'}, clear=True), \
             patch.object(auto_signin.requests, 'get', return_value=get), \
             patch.object(auto_signin.requests, 'put', return_value=put) as writer, contextlib.redirect_stdout(stdout):
            auto_signin.update_cookie_secret('private-test-cookie')
        payload = writer.call_args.kwargs['json']
        plaintext = public.SealedBox(private).decrypt(base64.b64decode(payload['encrypted_value']))
        self.assertEqual(plaintext, b'private-test-cookie')
        self.assertNotIn('private-test-cookie', str(payload))
        self.assertNotIn('private-test-cookie', stdout.getvalue())
        self.assertEqual(writer.call_args.args[0], 'https://api.github.com/repos/owner/repo/actions/secrets/NS_COOKIE')

    def test_secret_write_permission_failure_is_reported(self):
        private = public.PrivateKey.generate()
        get = Mock(status_code=200)
        get.json.return_value = {'key_id': 'test-key', 'key': private.public_key.encode(encoding.Base64Encoder()).decode('ascii')}
        with patch.dict(os.environ, {'GH_PAT': 'test-token', 'GITHUB_REPOSITORY': 'owner/repo'}, clear=True), \
             patch.object(auto_signin.requests, 'get', return_value=get), \
             patch.object(auto_signin.requests, 'put', return_value=Mock(status_code=403)):
            with self.assertRaisesRegex(RuntimeError, 'HTTP 403'):
                auto_signin.update_cookie_secret('private-test-cookie')

    def test_expired_cookie_requests_login(self):
        with patch.object(auto_signin, 'read_cookie', return_value='expired'), \
             patch.object(auto_signin, 'sign', return_value=('invalid', 'login required')), \
             patch.object(auto_signin, 'github_output') as output:
            self.assertFalse(auto_signin.check_cookie())
            output.assert_called_once_with(True)

    def test_valid_cookie_does_not_request_login(self):
        with patch.object(auto_signin, 'read_cookie', return_value='valid'), \
             patch.object(auto_signin, 'sign', return_value=('already', 'already signed')), \
             patch.object(auto_signin, 'github_output') as output:
            self.assertTrue(auto_signin.check_cookie())
            output.assert_called_once_with(False)

    def test_network_error_does_not_trigger_password_login(self):
        with patch.object(auto_signin, 'read_cookie', return_value='valid'), \
             patch.object(auto_signin, 'sign', return_value=('error', 'network failure')), \
             patch.object(auto_signin, 'github_output') as output:
            with self.assertRaisesRegex(RuntimeError, 'network failure'):
                auto_signin.check_cookie()
            output.assert_not_called()

    def test_cloud_reads_secret_while_local_reuses_saved_cookie(self):
        with tempfile.TemporaryDirectory() as temp:
            cookie = Path(temp) / 'cookie.txt'
            cookie.write_text('saved-cookie', encoding='utf-8')
            with patch.object(auto_signin, 'COOKIE_FILE', cookie), \
                 patch.dict(os.environ, {'NS_COOKIE': 'secret-cookie', 'GITHUB_ACTIONS': 'true'}, clear=True):
                self.assertEqual(auto_signin.read_cookie(), 'secret-cookie')
            with patch.object(auto_signin, 'COOKIE_FILE', cookie), \
                 patch.dict(os.environ, {'NS_COOKIE': 'old-cookie'}, clear=True):
                self.assertEqual(auto_signin.read_cookie(), 'saved-cookie')


if __name__ == '__main__':
    unittest.main()