# LuCI 组件更新器 · 中文知识库

**当前正式版本：V0.5.6 Stable（2026-11-21）**。本项目为 OpenWrt / ImmortalWrt 提供 LuCI 中的 NaiveProxy 官方版本检查、预构建包下载验证、原生 IPK/APKv3 安装及回滚；不是固件 OTA 工具。

[下载 V0.5.6 中文正式版（IPK / APK / 校验文件）](https://github.com/wekingchen/luci-app-component-updater/releases/tag/luci-app-component-updater-v0.5.6) · [中文发行说明](https://github.com/wekingchen/luci-app-component-updater/blob/main/docs/releases/v0.5.6-zh-CN.md)

## 设备支持和已验证内容

- **GL-MT3600BE / IPK（opkg）**：用户确认正常更新与手动回滚已在真机完成；移动端 LuCI、GitHub 反代查询和配置保留有记录，三阶段 Shell 原始日志尚未归档。
- **Redmi AX6S / 已适配的 APKv3 固件**：真机通过管理器 `0.5.6-r3 → 测试 r4 → r3` 和 NaiveProxy `154.0.8037.49.5-r1 → r3 → r1`；原程序 SHA256、配置和 APK world 得到回滚前后一致性验证。
- **Phicomm N1 / IPK**：保留 opkg 兼容路径，**不要求 N1 实机验收**，不称已经真机认证。

本版 Stable 仅针对指定设备的正常更新和手动回滚路径。尚未验证运行中的 PassWall 流量、异常写入与断电恢复，以及其他 APK 固件；AX6S 实测时没有运行 PassWall。回滚后旧 `check_state=ready` 可能残留，而 `ready=false` 是当前安装计划已失效的状态。自动发布门禁继续关闭，后续版本不自动晋升 Stable。

## 从哪里开始？

- [设备兼容性](Compatibility-and-Devices.md)：选择对应固件的软件包格式。
- [使用说明与常见问题](Operations-and-Troubleshooting.md)：安装、检查、下载设置、回滚和排障。
- [安全与恢复](Security-and-Recovery.md)：摘要、代理信任和恢复边界。
- [系统架构](System-Architecture.md)：LuCI、rpcd、组件构建器与原生包管理器。
- [版本发布和验收记录](Release-and-Verification.md)：正式版范围、真实测试和未验项。
- [开发协作规范](Developer-Guide.md)：版本、代码、测试与文档同步。

## 发布与历史记录

- [V0.5.6 Stable（当前 Latest）](https://github.com/wekingchen/luci-app-component-updater/releases/tag/luci-app-component-updater-v0.5.6)
- [NaiveProxy AX6S APK 更新/恢复组件产物](https://github.com/wekingchen/luci-app-component-updater/releases/tag/component-naiveproxy-v154.0.8037.49-5-upx521-r3-ax6s-apk1)
- [V0.5.0 RC1（历史预发布）](https://github.com/wekingchen/luci-app-component-updater/releases/tag/luci-app-component-updater-v0.5.0-rc1)

V0.5.2～V0.5.5 的手机主题、菜单、检查状态和 Overlay 空间预检问题属于**历史开发过程**，不能把当时的“待实机验证”误读成 V0.5.6 当前状态。历史记录见 [UI 验收档案](https://github.com/wekingchen/luci-app-component-updater/blob/main/docs/product-ui-acceptance.md) 和 [AX6S 验收档案](https://github.com/wekingchen/luci-app-component-updater/blob/main/docs/ax6s-hardware-acceptance-checklist.md)。

本 Wiki 由主仓库 `wiki-src/` 维护，并通过 CI/Actions 同步。需要判断最新发布状态时，以真实 GitHub Release 及其 IPK、APK、`SHA256SUMS.txt` 为准。
