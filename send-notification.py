"""Send NodeSeek failure notifications through the existing QQ SMTP setup."""
import argparse
import json
import os
import smtplib
import ssl
import sys
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def authorization_code():
    value = os.environ.get('QQ_MAIL_SMTP', '').strip()
    if value:
        return value
    if os.name == 'nt':
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as key:
                value, _ = winreg.QueryValueEx(key, 'QQ_MAIL_SMTP')
                return str(value).strip()
        except FileNotFoundError:
            pass
    return ''


def send(test=False, exit_code=1, timed_out=False):
    settings = json.loads((ROOT / 'cookie' / 'notification.json').read_text(encoding='utf-8-sig'))
    code = authorization_code()
    if not code:
        raise RuntimeError('QQ_MAIL_SMTP is not configured')
    message = EmailMessage()
    message['From'] = settings['MailFrom']
    message['To'] = settings['MailTo']
    message['Subject'] = '[测试] NodeSeek 失败提醒' if test else 'NodeSeek 自动签到失败提醒'
    now = datetime.now().astimezone().isoformat(timespec='seconds')
    if test:
        content = (f'这是一封 NodeSeek 失败通知通道测试邮件，并非实际签到失败。\n测试时间：{now}\n'
                   '每日任务安排在北京时间 00:00，签到成功或今天已签到时不发邮件。')
    else:
        reason = '任务超过 10 分钟，已停止本次进程。' if timed_out else '签到程序返回失败，请查看本机日志中的具体原因。'
        content = (f'NodeSeek 自动签到未完成。\n运行时间：{now}\n退出码：{exit_code}\n{reason}\n'
                   '请求出错时最多尝试 3 次，间隔 60 秒、120 秒。\n'
                   '请在本机检查 cookie/logs/last-run.log 和 last-error.log，或双击 run-local.cmd 补签。')
    message.set_content(content)
    smtp = None
    stage = 'connect'
    try:
        smtp = smtplib.SMTP_SSL('smtp.qq.com', 465, timeout=30, context=ssl.create_default_context())
        stage = 'authenticate'
        smtp.ehlo()
        smtp.user = settings['MailFrom']
        smtp.password = code
        smtp.auth('LOGIN', smtp.auth_login, initial_response_ok=False)
        stage = 'send'
        if smtp.send_message(message):
            raise RuntimeError('SMTP recipient refused')
    except Exception as error:
        error.notification_stage = stage
        raise
    finally:
        if smtp is not None:
            # QUIT failure does not undo a message already accepted by the server.
            try:
                smtp.quit()
            except (smtplib.SMTPException, OSError):
                smtp.close()
    print('Notification accepted by QQ SMTP server', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true')
    parser.add_argument('--exit-code', type=int, default=1)
    parser.add_argument('--timed-out', action='store_true')
    args = parser.parse_args()
    try:
        send(args.test, args.exit_code, args.timed_out)
    except Exception as error:
        response = getattr(error, 'smtp_code', None)
        stage = getattr(error, 'notification_stage', 'configure')
        print(f'Notification failed at {stage}: {type(error).__name__}' + (f' ({response})' if response else ''), flush=True)
        sys.exit(1)
