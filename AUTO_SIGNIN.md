# 本地自动签到（当前方案）

当前 Windows 任务 `NodeSeek-AutoSignin` 已设为每天北京时间 00:00 运行。任务在当前 Windows 用户登录时执行；错过时间后会在条件允许时补跑。

每次先用 `cookie/NS_COOKIE.txt` 中的 Cookie 签到。Cookie 有效时不启动验证码服务；失效时启动本机 CloudFreed 和独立 Edge 浏览器，用 `cookie/login.env` 中的 `USER1`、`PASS1` 登录，取得新 Cookie 后验证签到并保存供下次使用。任务结束后关闭服务及其浏览器。

手动补签：双击 `run-local.cmd`，与定时任务共用重试、日志和失败通知。
强制重新登录：双击 `login-with-cloudfreed.cmd`，取得新 Cookie 后签到，也会在失败时通知。
直接执行 Python 自动入口：`.venv\Scripts\python.exe auto_signin.py`，带请求重试，但不调用调度入口的邮件通知。
定时任务入口：`run-scheduled.ps1`。
任务可在 Windows 任务计划程序中按名称 `NodeSeek-AutoSignin` 查看、暂停或修改时间。

最近运行日志：`cookie/logs/last-run.log`；错误日志：`cookie/logs/last-error.log`。

## 网络重试与 QQ 邮箱失败通知

请求出错时最多尝试 3 次，两次重试分别等待 60 秒、120 秒。Cookie 无效或接口明确返回失败时不反复重试；网络请求出错不会触发账号密码重新登录。

仿照 sehuatang 的通知方式，只有最终失败、启动异常或运行超过 10 分钟时才发送一封失败提醒；成功或今天已签到时不发邮件。Windows 任务的总时限为 12 分钟，为发送通知预留时间。

QQ 邮箱使用 `smtp.qq.com`、SSL 465 端口和 LOGIN 认证。把 `notification.example.json` 复制到 `cookie/notification.json`，填写 `MailFrom`、`MailTo`。授权码读取 `QQ_MAIL_SMTP` 环境变量；Windows 下也会读取当前用户保存的环境变量，以适配任务计划程序。

本机已经沿用 sehuatang 的发件/收件配置。授权码不复制到配置文件，私有邮箱地址、Cookie 和日志均留在被 Git 忽略的 `cookie/` 目录。

状态文件：`cookie/logs/last-result.json`，记录开始/结束时间、退出码、是否超时和邮件发送状态。通知日志：`cookie/logs/last-notification.log`。

测试通知：`powershell.exe -NoProfile -File .\run-scheduled.ps1 -TestFailureNotification`。只发送标题带“测试”的邮件，不执行签到；测试记录单独保存到 `test-result.json` 和 `test-notification.log`，不覆盖正常运行记录。测试入口返回模拟失败码 2 是预期行为。

依赖安装：Python 3.11 虚拟环境中安装 `requirements-auto.txt`，再执行 `npm ci --prefix services/cloudfreed --ignore-scripts --no-audit --no-fund`。本地使用已有 Node.js 与 Edge。

## GitHub Actions 验证结果

CloudFreed 已能在 Actions 的 Linux runner 上启动浏览器并取得验证码令牌。但本次 NodeSeek 密码登录被引导至 `/emailSignIn.html`，没有取得会话 Cookie，因此无人值守云端续期未跑通。云端工作流改为手动运行，当前定时由本机承担。

自动入口包含通过 GitHub 公钥加密更新 `NS_COOKIE` Secret 的代码；该加密逻辑的测试通过，但云端实际 Secret 更新因登录未完成而尚未验证。此模式需要 `USER1`、`PASS1` 和仅覆盖当前仓库、具有 Secrets Read and write 权限的 `GH_PAT`。

云端验证工作流：`probe` 模式只测试服务和验证码；`login` 模式测试账号登录、签到与 Secret 写入。

## 服务来源和配置文件

服务源码来自 https://github.com/zetxtech/cloudfreed 。来源版本和兼容改动见 `services/cloudfreed/UPSTREAM.md`。当前修改支持 Chromium Fetch 接口与 Linux 文件名大小写。

Cookie、账号密码、运行日志与浏览器数据不提交进 Git。现有本地 `.env` 不会被登录更新过程覆盖。

本地验证码服务的浏览器数据和诊断日志位于被 Git 忽略的 `cookie/cloudfreed-runtime/`。
