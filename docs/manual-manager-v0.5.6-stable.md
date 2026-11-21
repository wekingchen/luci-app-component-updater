# V0.5.6 Stable · 限定设备的一次性人工发布

2026-11-21 的设备范围决定：**GL-MT3600BE（IPK/opkg）及指定固件 Redmi AX6S（APKv3）**。**N1 不需要实机测试**，其缺少真机记录不能阻止本次稳定版发布；仍允许兼容 IPK，但不得声称 N1 已被实机认证。

## 已知验收与证据等级

- AX6S：管理器 V0.5.6-r3 → 测试 r4 → r3，NaiveProxy APK 原厂 r1 → 构建 r3 → r1；已有版本、二进制 SHA256、UCI/配置、`/etc/apk/world` 和任务状态的真实输出。
- MT3600BE：用户明确确认 IPK 正常更新与回滚已实测；LuCI 手机端、反代官方查询、设置保存有记录。完整 IPK 更新前/后/回滚后的三阶段命令输出未在仓库归档，因此不伪造任何缺失的版本或哈希。
- CI：原生 opkg 21.02.5/24.10.5、APKv3、ARM64、安装/回滚、LuCI/rpcd、Python/JS/Shell 现有回归已通过。

## 尚未验证

N1 真机（无需测试）、PassWall 运行中流量/进程切换、实体设备中断下载及写入失败自动恢复、受控断电、其它 APK 固件。AX6S 当时未运行 PassWall，`runtime_processes=0` 正常。回滚后 `check_state=ready` 而实际 `ready=false` 的检查状态残留是已知非阻断问题。

## 已授权的一次性自动发布

本次不需要任何人工确认输入。新的 [V0.5.6 Stable 自动发布工作流](https://github.com/wekingchen/luci-app-component-updater/actions/workflows/auto-manager-v0.5.6-stable.yml) 只会在可信主分支 `Component Updater / CI & native IPK/APK` 成功完成后触发，校验来源并发布一次固定版本。之前手动发布失败源于代码错误：用户输入 `PUBLISH_0.5.6_STABLE`，脚本却检查 `PUBLISH_0.5.6_Stable`。

自动流程复用成功 CI Run `44898618719` 的固定提交 `91008d098080552e8579872ec52f1bb9cb87b366` 与 Artifact ID/摘要，**不重新打包**。仅发布 `luci-app-component-updater-v0.5.6`，包含 `luci-app-component-updater_0.5.6-3_all.ipk`、`luci-app-component-updater-0.5.6-r3.apk`、`SHA256SUMS.txt`。如已发布同名正式版且资产齐全则跳过；同名 Tag 不匹配则拒绝覆盖。

**这不等于所有未来版本自动 Stable**。本次只对已确认的 V0.5.6 授权，其他版本仍需定义相应验收及发布规则；`AX6S_APK_AUTO_PUBLISH` 保持关闭。

[核对 GitHub V0.5.6 Stable Release](https://github.com/wekingchen/luci-app-component-updater/releases/tag/luci-app-component-updater-v0.5.6)。未确认实际 Release 和附件存在前，不得宣称发版完成。
