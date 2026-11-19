# LuCI 组件更新器 · 项目知识库

**面向 OpenWrt 的中文组件更新平台**。在路由器 LuCI 中检查组件官方稳定版、下载预先构建并校验的软件包、执行本机原生软件包更新，以及在失败时恢复旧版本。

> 当前版本：**V0.5.0 RC1（预发布）**。IPK 与 APK 管理器均已发布。AX6S APK 路线通过真实固件镜像/ARM64 隔离环境测试，**尚未完成实体 AX6S 验收**；不要把云端通过误读为所有路由器可安全安装。

## 从哪里开始？

- [项目总体架构](System-Architecture.md)：理解 LuCI、rpcd、构建器、IPK 与 APK 双体系。
- [支持设备与兼容边界](Compatibility-and-Devices.md)：先确认你的设备是否真的属于已适配环境。
- [下载、验证与回滚](Security-and-Recovery.md)：更新前的校验、备份、代理风险。
- [日常操作与排障](Operations-and-Troubleshooting.md)：检查和验证、需要什么恢复准备。
- [版本发布与验收门禁](Release-and-Verification.md)：为什么 RC 不等于稳定版。
- [开发人员与 AI 协作](Developer-Guide.md)：如何遵守项目规范和维持文档更新。

## 最新产物

- [组件更新器 V0.5.0 RC1：同一 Release 下的 IPK / APK](https://github.com/wekingchen/luci-app-component-updater/releases/tag/luci-app-component-updater-v0.5.0-rc1)
- [AX6S NaiveProxy APKv3 候选：升级包和原固件恢复包](https://github.com/wekingchen/luci-app-component-updater/releases/tag/component-naiveproxy-v154.0.8037.49-5-upx521-r3-ax6s-apk1)

本知识库由主仓库 `wiki-src/` 维护。实际技术约束以 [项目开发规则](https://github.com/wekingchen/luci-app-component-updater/blob/main/AGENTS.md)、[项目治理](https://github.com/wekingchen/luci-app-component-updater/blob/main/docs/project-governance.md)及可运行的代码/测试为准，Wiki 页面不替代设备验收。
