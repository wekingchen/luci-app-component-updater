# LuCI 组件更新器 · 项目知识库

**面向 OpenWrt 的中文组件更新平台**。在路由器 LuCI 中检查组件官方稳定版、下载预先构建并校验的软件包、执行本机原生软件包更新，以及在失败时恢复旧版本。

> **当前实机进展（2026-11-21）**：AX6S 的 V0.5.6-r3 管理器网页自升级与手动回滚、NaiveProxy 原生 APK 从 `154.0.8037.49.5-r1 → r3 → r1` 的正常升级与手动回滚均已通过实体设备分项验收。NaiveProxy 配置及 `/etc/apk/world` 的 SHA256 在升级/回滚前后一致，原厂程序哈希已恢复。**此次设备未运行 PassWall，异常恢复与断电恢复仍未验证；完整稳定版门禁未解除。**管理器已公开 Release 版本与资产以 GitHub Releases 为准。

> **历史回顾**：V0.5.2/0.5.3 的 MT3600BE UI、反代状态文字候选，以及 AX6S 早期 LuCI 菜单、页头和低空间预检问题，已由后续 0.5.5/0.5.6 迭代分别处理；这些历史记录不能取代以下最新验收事实。

> **此前问题的状态**：AX6S 早期存在安装后 LuCI 菜单缺失、组件标题竖排和 Overlay 空间不足导致拒装。2026-11-21 用户解决空间后，当前 LuCI 已可检查并实际执行 NaiveProxy 正常升级与手动回滚；但桌面固件抽屉及其它极端/故障场景仍待复核。

## 从哪里开始？

- [项目总体架构](System-Architecture.md)：理解 LuCI、rpcd、构建器、IPK 与 APK 双体系。
- [支持设备与兼容边界](Compatibility-and-Devices.md)：先确认你的设备是否真的属于已适配环境。
- [下载、验证与回滚](Security-and-Recovery.md)：更新前的校验、备份、代理风险。
- [日常操作与排障](Operations-and-Troubleshooting.md)：检查和验证、需要什么恢复准备。
- [版本发布与验收门禁](Release-and-Verification.md)：为什么 RC 不等于稳定版。
- [开发人员与 AI 协作](Developer-Guide.md)：如何遵守项目规范和维持文档更新。

当前 UI 验收基准见 [V0.5.5 视觉与功能验收清单](https://github.com/wekingchen/luci-app-component-updater/blob/main/docs/product-ui-acceptance.md)。

> **回滚后的最新状态**：AX6S 当前由用户确认停留原厂 `naiveproxy 154.0.8037.49.5-r1`，`job_state=rolled_back`、`rollback_available=false` 正常；`runtime_processes=0` 因为没有运行 PassWall。存在非阻断性旧检查信息残留 `check_state=ready` / `ready=false`，留待后续修复。

## 最新产物

- [组件更新器 V0.5.0 RC1：同一 Release 下的 IPK / APK](https://github.com/wekingchen/luci-app-component-updater/releases/tag/luci-app-component-updater-v0.5.0-rc1)
- [AX6S NaiveProxy APKv3 候选：升级包和原固件恢复包](https://github.com/wekingchen/luci-app-component-updater/releases/tag/component-naiveproxy-v154.0.8037.49-5-upx521-r3-ax6s-apk1)

本知识库的页面由主仓库 `wiki-src/` 版本化维护，并经 GitHub Actions 校验后同步。实际技术约束以 [项目开发规则](https://github.com/wekingchen/luci-app-component-updater/blob/main/AGENTS.md)、[项目治理](https://github.com/wekingchen/luci-app-component-updater/blob/main/docs/project-governance.md)及可运行的代码/测试为准，Wiki 页面不替代设备验收。

> **候选包版本区分**：V0.5.5-r1 是页头布局修复候选，V0.5.5-r2 增加了更新检查状态/错误诊断的修复。r3 已完成移动端和空间保护的实机验证；r4 修复警告颜色与精确管理器版本，仍是待验收候选。

> **V0.5.6-r3 / 2026-11-21 管理器真机验收进展**：实体 AX6S 已经通过网页执行 `r3 → r4（仅供回归测试）→ r3`，升级后任务 `completed`、`busy=false`、回滚可用；回滚后 APK 数据库回到 r3、任务 `rolled_back`、`busy=false`，原 UCI 组件配置保留。r2 首次跳转 r3 时仍运行 r2 旧 worker，不保证无感刷新；从 r3 启动的升级/回滚闭环已实测通过。r3 是建议保留的交付候选版本，r4 不是正式新功能版。

> **发布边界**：V0.5.6 Stable 目标仅为 MT3600BE（IPK）与指定固件 AX6S（APK）。**N1 不需要真机测试，也不构成发布门槛**。MT3600BE 的 IPK 完整更新/回滚为用户确认，未归档三阶段 Shell 原始日志；AX6S 的正常更新与回滚已有实际版本/哈希记录。PassWall 实时流量、异常及断电恢复仍未实机验证。完整设备验收前，只允许 RC/prerelease，不得解除 `AX6S_APK_AUTO_PUBLISH` 安全门禁；是否已公开发布以 [GitHub Releases](https://github.com/wekingchen/luci-app-component-updater/releases) 实际资产为准。早期 r1/r2 启用网页自升级的试验与故障修复记录保留在版本历史。
