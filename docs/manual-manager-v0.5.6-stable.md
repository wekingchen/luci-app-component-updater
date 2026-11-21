# V0.5.6 Stable · 限定设备的一次性人工发布

2026-11-21 的设备范围决定：**GL-MT3600BE（IPK/opkg）及指定固件 Redmi AX6S（APKv3）**。**N1 不需要实机测试**，其缺少真机记录不能阻止本次稳定版发布；仍允许兼容 IPK，但不得声称 N1 已被实机认证。

## 已知验收与证据等级

- AX6S：管理器 V0.5.6-r3 → 测试 r4 → r3，NaiveProxy APK 原厂 r1 → 构建 r3 → r1；已有版本、二进制 SHA256、UCI/配置、`/etc/apk/world` 和任务状态的真实输出。
- MT3600BE：用户明确确认 IPK 正常更新与回滚已实测；LuCI 手机端、反代官方查询、设置保存有记录。完整 IPK 更新前/后/回滚后的三阶段命令输出未在仓库归档，因此不伪造任何缺失的版本或哈希。
- CI：原生 opkg 21.02.5/24.10.5、APKv3、ARM64、安装/回滚、LuCI/rpcd、Python/JS/Shell 现有回归已通过。

## 尚未验证

N1 真机（无需测试）、PassWall 运行中流量/进程切换、实体设备中断下载及写入失败自动恢复、受控断电、其它 APK 固件。AX6S 当时未运行 PassWall，`runtime_processes=0` 正常。回滚后 `check_state=ready` 而实际 `ready=false` 的检查状态残留是已知非阻断问题。

## 仅一次人工发布

[打开 Release / V0.5.6 Stable (scoped one-time manual)](https://github.com/wekingchen/luci-app-component-updater/actions/workflows/manual-manager-v0.5.6-stable.yml)，主分支选择 Run workflow，填写 `PUBLISH_0.5.6_STABLE`。流程绑定已成功的 main CI Run `44898618719`、提交 `91008d098080552e8579872ec52f1bb9cb87b366` 和固定 Artifact digest；严格复用同批构建资产，不重新构建、不覆盖已有 tag/Release。

Release 必须包含 `luci-app-component-updater_0.5.6-3_all.ipk`、`luci-app-component-updater-0.5.6-r3.apk` 及 `SHA256SUMS.txt`。发布成功后在 [GitHub V0.5.6 Stable Release](https://github.com/wekingchen/luci-app-component-updater/releases/tag/luci-app-component-updater-v0.5.6) 核对资产。**不打开 `AX6S_APK_AUTO_PUBLISH`，后续版本不自动取得 Stable 资格。**只有 Release 确实创建成功才算正式发版。
