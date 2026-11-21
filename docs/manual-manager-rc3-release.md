# V0.5.6 RC3 手动发布尝试 · 历史归档（已退役）

> **请勿按此文档操作发版。** V0.5.6 正式版本已于 2026-11-21 通过主分支 CI 的一次性自动发布流程创建，并将标题与发行说明修正为简体中文。

当时曾为 RC3 候选建立仅能手动触发的发布工作流，用于复用同一主分支 CI 的 IPK/APK 资产；随后改为限定 MT3600BE（IPK）和已适配 AX6S（APK）的 Stable 发布范围，**N1 不需要专门真机验收**。旧 RC3 工作流已从主分支删除，因此旧说明中的确认码、Run workflow 操作与“尚未发布”判定均已失效。

V0.5.6 Stable 初次手动发布失败的直接原因是确认字串大小写不一致；修复后采用固定版本、可信 main CI 成功自动触发、精确资产来源及摘要核验、已存在同名 Release 则安全跳过的方案。该一次性授权**不延伸至未来新版本**，`AX6S_APK_AUTO_PUBLISH` 仍关闭。

- [当前中文正式版 Release](https://github.com/wekingchen/luci-app-component-updater/releases/tag/luci-app-component-updater-v0.5.6)
- [正式版发布工作流与安全边界](manual-manager-v0.5.6-stable.md)
- [中文正式版发行说明](releases/v0.5.6-zh-CN.md)
- [版本及验证门禁](acceptance-gates.md)

此文件只保留版本发布决策的历史背景，**不再包含可执行的旧 RC3 发布步骤**。
