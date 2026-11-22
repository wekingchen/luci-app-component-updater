# MT3600BE · 标题栏 `null` 修复 IPK 测试候选（V0.5.6-4）

**性质：** V0.5.6 Stable 之后的 GL-MT3600BE / opkg 专项测试包，**不替换已发布 Stable，也不是 APK 固件通用包**。

## 根因与修复

实机 iPhone Safari 截图中，「组件更新」和「下载设置」之间出现了文本 `null`。修复来自已通过主分支 CI 的提交 `a4c24204bdb84dfa8b4704e5eb51300e0421af34`：在 LuCI 生成 DOM 前只放入实际存在的标题快捷链接，IPK 只有「下载设置」，已验证 AX6S APK 还有「管理器更新」。此修复的 PR 为 [#28](https://github.com/wekingchen/luci-app-component-updater/pull/28)。

## 测试候选

- IPK：`luci-app-component-updater_0.5.6-4_all.ipk`（版本 `0.5.6-4`）。
- SHA256：同候选 Release 的 `SHA256SUMS.txt`。
- 候选发布页：[MT3600BE V0.5.6-4 RC1](https://github.com/wekingchen/luci-app-component-updater/releases/tag/luci-app-component-updater-v0.5.6-4-mt3600be-null-fix-rc1)。
- 构建方式：仅使用已成功 CI 验证的 `a4c24204` 源码；在一次性 CI runner 中把 `package_ipk.VERSION` 改为 `0.5.6-4`，以及将 IPK 页面页脚显示版本改为 `v0.5.6-4`，不改变 APK 和稳定版版本/标签。

## MT3600BE 安装与验收

请保留 SSH 或另一种管理通道。通过页面下载新 IPK 后上传到路由器 `/tmp`，执行：

```sh
opkg install /tmp/luci-app-component-updater_0.5.6-4_all.ipk
opkg status luci-app-component-updater | grep -E '^Package:|^Version:|^Status:'
```

安装脚本会清除 LuCI 缓存并短暂重启 `rpcd`、`uhttpd`，网页会话可能断开片刻，但**不主动重启 PassWall**。重新打开/强制刷新「系统 → 组件更新」，检查标题右侧只剩「下载设置」、未显示 `null`，然后确认 NaiveProxy 当前版本、恢复按钮、下载设置仍正常。Safari 如仍显示旧界面，关闭旧标签后在新标签重新打开，避免缓存影响观察。

**未验收：** 此新包的 MT3600BE 真机安装与前端显示，必须以安装后的实机反馈为准。CI 通过不等于已经安装到真实硬件。已有 V0.5.6 Stable 原始包保持不变；需要降回正式版时可使用[稳定版下载页](https://github.com/wekingchen/luci-app-component-updater/releases/tag/luci-app-component-updater-v0.5.6)的 `0.5.6-3` IPK，执行 `opkg install --force-downgrade <旧包路径>`（前提是已留存旧包和独立恢复通道）。

**供应链说明：** SHA256 能核对文件下载完整性，不能代替独立数字签名。发布任务必须核实固定主分支 CI 记录、IPK 控制字段及 JS 修复载荷，不允许覆盖已存在 Release。
