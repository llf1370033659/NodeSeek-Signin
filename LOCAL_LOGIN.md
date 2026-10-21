# 本地账号密码登录测试

1. 在 `cookie/login.env` 中填写 NodeSeek 用户名 `USER1` 和密码 `PASS1`。
2. 双击 `login-with-cloudfreed.cmd`。
3. 脚本启动仅监听本机的 CloudFreed API 和独立 Edge 浏览器，然后用账号密码登录 NodeSeek。
4. 登录成功后，新 Cookie 保存到 `cookie/NS_COOKIE.txt`，脚本立即用它验证签到。
5. 测试结束后关闭本次服务和浏览器。现有 `.env` 和 GitHub Actions 的 Cookie 不会自动替换。

如需将新 Cookie 用于 GitHub Actions，把 `cookie/NS_COOKIE.txt` 的完整内容更新到仓库的 `NS_COOKIE` Secret。

`login-with-cloudfreed.cmd` 通过 `run-scheduled.ps1 -ForceLogin` 调用自动入口。它始终尝试重新登录；普通手动补签使用 `run-local.cmd`，Cookie 有效时直接签到。

CloudFreed 的 Node.js 服务及兼容修改位于 `services/cloudfreed`。服务日志位于 `cookie/cloudfreed-runtime/service.log`，签到记录和 QQ 邮箱通知状态位于 `cookie/logs`。

已验证：本地服务启动、验证码令牌获取、账号密码登录、新 Cookie 保存、用新 Cookie 签到、服务和浏览器关闭，完整流程通过。

`nodeseek_sign.py` 已按当前网站前端更新登录参数：验证码通过 x-captcha-token 和 x-captcha-source 请求头发送，JSON 只包含用户名和密码。详细配置与失败通知说明见 `AUTO_SIGNIN.md`。
