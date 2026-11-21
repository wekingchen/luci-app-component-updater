# 版本发布与验收门禁

**当前正式版本：V0.5.6 Stable**，于 2026-11-21 公开发布，包含管理器 IPK、APKv3 与 SHA256SUMS，GitHub Release 的标题和更新说明已改成简体中文。

[查看 V0.5.6 Stable 正式版](https://github.com/wekingchen/luci-app-component-updater/releases/tag/luci-app-component-updater-v0.5.6) · [中文发行说明](https://github.com/wekingchen/luci-app-component-updater/blob/main/docs/releases/v0.5.6-zh-CN.md)

## 发布证据等级

| 门禁 | 覆盖内容 | 含义 |
| --- | --- | --- |
| G0 | Python/JS/Shell、rpcd/ACL、打包及异常状态单测 | 仅为开发回归通过 |
| G1 | 来源/摘要、UPX、原生 opkg/APKv3、真实 rootfs/ARM64 验证 | 云端构建及安装格式可回归，不等于实机 |
| G2 | 指定设备身份、LuCI 页面、官方版本查询、下载设置与配置保留 | 对应设备的只读/前端验收 |
| G3 | 指定设备正常真实更新、原版备份、软件包版本和手动回滚 | 可对已实际测试的正常主路径作出结论 |
| G4（本版限定范围） | 目标设备与格式、G0～G3 已有证据、恢复通道、发行说明的风险披露 | 可以对本次限定范围发布 Stable，不代表故障注入及所有设备通过 |

完整门禁定义见 [仓库质量验收细则](https://github.com/wekingchen/luci-app-component-updater/blob/main/docs/acceptance-gates.md)。云端 CI 通过不能直接推断真实 Flash、PassWall 实时代理或断电安全。

## V0.5.6 Stable：已验收的设备和范围

- **GL-MT3600BE / IPK（opkg）**：用户已确认真机正常升级与回滚完成，手机 LuCI、GitHub 反代官方查询、配置保留另有历史反馈。完整三阶段原始 Shell 日志未归档，**不杜撰具体版本、文件 SHA256 或独立网络抓包证据**。
- **Redmi AX6S / 指定固件 APKv3**：真机通过管理器 `0.5.6-r3 → 仅测试 r4 → r3` 的网页升级与恢复；完成后/回滚后 `busy=false`，UCI 配置保留。NaiveProxy 组件完成 `154.0.8037.49.5-r1 → r3 → r1`，新版 ELF SHA256 为 `fb19517f2738b131e23c6e49a30d246bf69a2cef835b37c7b6ae82c2168715da`，回滚后恢复原厂 SHA256 `94a9d2ebce92b2fd877e1e7019dbfa09a7bb7a5d481ec593bd34b5d5abd2a861`，配置和 `/etc/apk/world` 在三次观测中哈希保持一致。
- **N1 / IPK（opkg）**：有原生 opkg CI 兼容证据，但**不要求 N1 真机测试**，不作为本次 Stable 的发布阻碍，也不宣称已经取得 N1 真机认证。

**未验收且不在本次 Stable 承诺范围内：** PassWall 正在运行时的流量与进程切换、真实设备上损坏/中断安装的自动恢复、意外断电及其他 APK 固件。AX6S 测试时没有运行 PassWall，`runtime_processes=0` 符合预期。组件操作后可能残留 `check_state=ready`，但实际 `ready=false`，这是待后续修复的非阻断状态一致性问题。

## 发布流程和安全界限

本次 V0.5.6 Stable 由[固定版本的一次性自动发布工作流](https://github.com/wekingchen/luci-app-component-updater/actions/workflows/auto-manager-v0.5.6-stable.yml) 在可信 main CI 完成后自动创建，复用固定成功 CI 的 IPK/APK 产物与摘要校验。首次发行说明曾误用英文，已通过校验现有三个附件 SHA256 后**只修改 Release 标题与正文**，并验证为中文；附件、标签、已发布版本均未替换。

已发布 V0.5.6 不意味着未来所有版本可自动晋升 Stable。仓库变量 `AX6S_APK_AUTO_PUBLISH` 保持关闭，尚未验收的故障/流量/断电仍是未来版本的专项门禁。RC3 手动确认码工作流已经退役，**不需要用户再次输入发布确认码**。

## 历史版本与证据

- [V0.5.0 RC1（早期预发布）](https://github.com/wekingchen/luci-app-component-updater/releases/tag/luci-app-component-updater-v0.5.0-rc1)：当时 AX6S 未完成真机升级/回滚，**不是当前 Latest**。
- V0.5.1～V0.5.5：GL.iNet 与 AX6S 的移动端 UI、菜单、页头、检查状态、Overlay 空间预算等修复候选，当时的未验结论不应套用到 V0.5.6。
- [V0.5.6 AX6S 真实验收原始摘要](https://github.com/wekingchen/luci-app-component-updater/blob/main/docs/ax6s-hardware-acceptance-checklist.md) 与 [历史 UI 修复档案](https://github.com/wekingchen/luci-app-component-updater/blob/main/docs/product-ui-acceptance.md) 保存具体过程和未完成项。

[首页](Home.md) · [设备兼容性](Compatibility-and-Devices.md) · [使用说明](Operations-and-Troubleshooting.md)
