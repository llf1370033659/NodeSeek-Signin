"""Cookie-first sign-in with an on-demand, local CloudFreed service."""
from pathlib import Path
import argparse
import base64
import json
import os
import secrets
import shutil
import socket
import subprocess
import time
import urllib.request

from dotenv import load_dotenv
from curl_cffi import requests
from nodeseek_sign import session_login, sign
from turnstile_solver import TurnstileSolver

ROOT = Path(__file__).resolve().parent
COOKIE_FILE = ROOT / 'cookie' / 'NS_COOKIE.txt'


class LocalCloudFreed:
    def __enter__(self):
        self.process = None
        self.log = None
        service_dir = ROOT / 'services' / 'cloudfreed'
        runtime = Path(os.environ.get('RUNNER_TEMP', str(ROOT.parents[1] / 'work'))) / 'cloudfreed-runtime'
        runtime.mkdir(parents=True, exist_ok=True)
        node = shutil.which('node')
        browser = os.environ.get('CLOUDFREED_BROWSER_PATH')
        if not browser and os.name == 'nt':
            browser = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
        if not browser:
            browser = shutil.which('chrome') or shutil.which('google-chrome')
        if not node or not browser or not Path(browser).is_file():
            raise RuntimeError('Node.js or a compatible browser is missing')
        with socket.socket() as check:
            check.bind(('127.0.0.1', 3000))
        self.client_key = secrets.token_urlsafe(24)
        env = dict(os.environ)
        env.update(CLOUDFREED_CLIENT_KEY=self.client_key, CLOUDFREED_DATA_DIR=str(runtime), CLOUDFREED_BROWSER_PATH=browser)
        self.log = (runtime / 'service.log').open('w', encoding='utf-8')
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        self.process = subprocess.Popen([node, str(service_dir / 'local-service.mjs')], cwd=service_dir, env=env,
                                        stdin=subprocess.PIPE, stdout=self.log, stderr=self.log, text=True, creationflags=flags)
        local_http = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        deadline = time.monotonic() + 45
        try:
            while True:
                if self.process.poll() is not None:
                    raise RuntimeError('CloudFreed exited before its API was ready')
                try:
                    with local_http.open('http://127.0.0.1:3000/health', timeout=1) as response:
                        if json.load(response).get('ready'):
                            print('CloudFreed API ready', flush=True)
                            return self
                except OSError:
                    pass
                if time.monotonic() >= deadline:
                    raise RuntimeError('CloudFreed API startup timed out')
                time.sleep(0.2)
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *_args):
        if self.process is not None and self.process.poll() is None:
            try:
                self.process.stdin.write('stop\n')
                self.process.stdin.flush()
                self.process.wait(timeout=15)
            except (OSError, subprocess.TimeoutExpired):
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.process.pid)], capture_output=True)
                else:
                    self.process.terminate()
                    self.process.wait(timeout=5)
        if self.log is not None:
            self.log.close()
        print('CloudFreed stopped', flush=True)


def github_output(needs_login):
    target = os.environ.get('GITHUB_OUTPUT')
    if target:
        with open(target, 'a', encoding='utf-8') as output:
            output.write(f'needs_login={str(needs_login).lower()}\n')


def read_cookie():
    if os.environ.get('GITHUB_ACTIONS') != 'true' and COOKIE_FILE.is_file():
        return COOKIE_FILE.read_text(encoding='utf-8').strip()
    return os.environ.get('NS_COOKIE', '')


def check_cookie():
    status, message = sign(read_cookie(), os.environ.get('NS_RANDOM', 'true'))
    if status in ('success', 'already'):
        print(f'Cookie sign-in OK: {message}')
        github_output(False)
        return True
    if status != 'invalid':
        raise RuntimeError(f'Sign-in failed ({status}): {message}')
    print('Cookie missing or expired; login required')
    github_output(True)
    return False


def update_cookie_secret(cookie):
    from nacl import encoding, public
    token = os.environ.get('GH_PAT')
    repository = os.environ.get('GITHUB_REPOSITORY')
    if not token or not repository:
        raise RuntimeError('GH_PAT and GITHUB_REPOSITORY are required to update NS_COOKIE Secret')
    api = f'https://api.github.com/repos/{repository}/actions/secrets'
    headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/vnd.github+json',
               'X-GitHub-Api-Version': '2022-11-28'}
    key_response = requests.get(f'{api}/public-key', headers=headers, timeout=30)
    if key_response.status_code != 200:
        raise RuntimeError(f'Cannot read repository public key: HTTP {key_response.status_code}')
    key = key_response.json()
    box = public.SealedBox(public.PublicKey(key['key'].encode('ascii'), encoding.Base64Encoder()))
    encrypted = base64.b64encode(box.encrypt(cookie.encode('utf-8'))).decode('ascii')
    response = requests.put(f'{api}/NS_COOKIE', headers=headers,
                            json={'encrypted_value': encrypted, 'key_id': key['key_id']}, timeout=30)
    if response.status_code not in (201, 204):
        raise RuntimeError(f'Cannot update NS_COOKIE Secret: HTTP {response.status_code}')
    print('NS_COOKIE Secret updated successfully')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--probe', action='store_true', help='Test cloud browser and CAPTCHA without account credentials')
    parser.add_argument('--check-cookie', action='store_true')
    parser.add_argument('--force-login', action='store_true')
    args = parser.parse_args()
    load_dotenv(ROOT / '.env')
    load_dotenv(ROOT / 'cookie' / 'login.env')
    if not args.probe and not args.force_login:
        if check_cookie() or args.check_cookie:
            return 0
    if not args.probe and (not os.environ.get('USER1') or not os.environ.get('PASS1')):
        raise RuntimeError('USER1 and PASS1 are required for automatic login')
    with LocalCloudFreed() as solver:
        if args.probe:
            token = TurnstileSolver('http://127.0.0.1:3000', solver.client_key).solve(
                url='https://www.nodeseek.com/signIn.html', sitekey='0x4AAAAAAAaNy7leGjewpVyR', verbose=False)
            if not token:
                raise RuntimeError('CAPTCHA service returned no token')
            print('Cloud CAPTCHA token obtained successfully')
            return 0
        cookie = session_login(os.environ['USER1'], os.environ['PASS1'], 'turnstile',
                               'http://127.0.0.1:3000', solver.client_key)
        if not cookie:
            raise RuntimeError('NodeSeek login failed')
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            print(f'::add-mask::{cookie}')
        status, message = sign(cookie, os.environ.get('NS_RANDOM', 'true'))
        if status not in ('success', 'already'):
            raise RuntimeError(f'New Cookie sign-in failed ({status}): {message}')
        COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
        COOKIE_FILE.write_text(cookie, encoding='utf-8')
        print(f'Fresh Cookie sign-in OK: {message}')
        if os.environ.get('GITHUB_ACTIONS') == 'true':
            update_cookie_secret(cookie)
        else:
            print('Fresh Cookie saved locally for the next run')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f'ERROR: {error}', flush=True)
        raise SystemExit(1)