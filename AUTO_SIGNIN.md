# 本地自动签到（当前方案）

当前 Windows 任务 `NodeSeek-AutoSignin` 已设为每天北京时间 00:00 运行。任务在当前 Windows 用户登录时执行；错过时间后会在条件允许时补跑。

每次先用 `cookie/NS_COOKIE.txt` 中的 Cookie 签到。Cookie 有效时不启动验证码服务；失效时启动本机 CloudFreed 和独立 Edge 浏览器，用 `cookie/login.env` 中的 `USER1`、`PASS1` 登录，取得新 Cookie 后验证签到并保存供下次使用。任务结束后关闭服务及其浏览器。

手动执行：`.venv\Scripts\python.exe auto_signin.py`。
强制验证登录更新：`.venv\Scripts\python.exe auto_signin.py --force-login`。
定时任务入口：`run-scheduled.ps1`。
任务可在 Windows 任务计划程序中按名称 `NodeSeek-AutoSignin` 查看、暂停或修改时间。

最近运行日志：`cookie/logs/last-run.log`；错误日志：`cookie/logs/last-error.log`。

依赖安装：Python 3.11 虚拟环境中安装 `requirements-auto.txt`，再执行 `npm ci --prefix services/cloudfreed --ignore-scripts --no-audit --no-fund`。本地使用已有 Node.js 与 Edge。

## GitHub Actions 验证结果

CloudFreed 已能在 Actions 的 Linux runner 上启动浏览器并取得验证码令牌。但本次 NodeSeek 密码登录被引导至 `/emailSignIn.html`，没有取得会话 Cookie，因此无人值守云端续期未跑通。云端工作流改为手动运行，当前定时由本机承担。

自动入口包含通过 GitHub 公钥加密更新 `NS_COOKIE` Secret 的代码；该加密逻辑的测试通过，但云端实际 Secret 更新因登录未完成而尚未验证。此模式需要 `USER1`、`PASS1` 和仅覆盖当前仓库、具有 Secrets Read and write 权限的 `GH_PAT`。

云端验证工作流：`probe` 模式只测试服务和验证码；`login` 模式测试账号登录、签到与 Secret 写入。

## 服务来源和配置文件

服务源码来自 https://github.com/zetxtech/cloudfreed 。来源版本和兼容改动见 `services/cloudfreed/UPSTREAM.md`。当前修改支持 Chromium Fetch 接口与 Linux 文件名大小写。

Cookie、账号密码、运行日志与浏览器数据不提交进 Git。现有本地 `.env` 不会被登录更新过程覆盖。

本地验证码服务的浏览器数据和诊断日志位于被 Git 忽略的 `cookie/cloudfreed-runtime/`。
