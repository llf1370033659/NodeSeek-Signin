import contextlib
import importlib.util
import io
import json
from pathlib import Path
import smtplib
import tempfile
import unittest
from unittest.mock import Mock, patch

spec = importlib.util.spec_from_file_location('nodeseek_mail', Path(__file__).resolve().parents[1] / 'send-notification.py')
mail = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mail)


class NotificationTests(unittest.TestCase):
    def settings(self, root):
        directory = root / 'cookie'
        directory.mkdir()
        (directory / 'notification.json').write_text(json.dumps({
            'MailFrom': 'sender@example.com', 'MailTo': 'recipient@example.com'
        }), encoding='utf-8')

    def test_failure_mail_uses_qq_ssl_login_without_printing_auth_code(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.settings(root)
            smtp = Mock()
            smtp.send_message.return_value = {}
            stdout = io.StringIO()
            with patch.object(mail, 'ROOT', root), patch.object(mail, 'authorization_code', return_value='private-test-authorization'), \
                 patch.object(mail.smtplib, 'SMTP_SSL', return_value=smtp) as connect, contextlib.redirect_stdout(stdout):
                mail.send(exit_code=1)
            self.assertEqual(connect.call_args.args, ('smtp.qq.com', 465))
            smtp.auth.assert_called_once_with('LOGIN', smtp.auth_login, initial_response_ok=False)
            message = smtp.send_message.call_args.args[0]
            self.assertIn('NodeSeek', message['Subject'])
            self.assertIn('退出码：1', message.get_content())
            self.assertNotIn('private-test-authorization', stdout.getvalue())
            self.assertNotIn('private-test-authorization', message.as_string())

    def test_quit_disconnect_does_not_duplicate_accepted_mail(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.settings(root)
            smtp = Mock()
            smtp.send_message.return_value = {}
            smtp.quit.side_effect = smtplib.SMTPServerDisconnected('disconnected')
            with patch.object(mail, 'ROOT', root), patch.object(mail, 'authorization_code', return_value='test-auth'), \
                 patch.object(mail.smtplib, 'SMTP_SSL', return_value=smtp):
                mail.send(test=True)
            smtp.send_message.assert_called_once()
            smtp.close.assert_called_once()
            self.assertTrue(smtp.send_message.call_args.args[0]['Subject'].startswith('[测试]'))

    def test_authentication_failure_is_reported_without_sending(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.settings(root)
            smtp = Mock()
            smtp.auth.side_effect = smtplib.SMTPAuthenticationError(535, b'authentication failed')
            with patch.object(mail, 'ROOT', root), patch.object(mail, 'authorization_code', return_value='test-auth'), \
                 patch.object(mail.smtplib, 'SMTP_SSL', return_value=smtp):
                with self.assertRaises(smtplib.SMTPAuthenticationError) as caught:
                    mail.send()
            self.assertEqual(caught.exception.notification_stage, 'authenticate')
            smtp.send_message.assert_not_called()


if __name__ == '__main__':
    unittest.main()
