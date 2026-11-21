# 管理器 V0.5.6 RC3 的一次性人工发布

**状态**：仅在 GitHub Actions 中人工触发的 **RC/prerelease** 发布入口；不影响 `AX6S_APK_AUTO_PUBLISH` 自动稳定发布安全门禁。这个工作流只发布 V0.5.6-r3 APK 和 V0.5.6-3 IPK，不做设备安装。

## 何时可以使用

- GitHub 主分支的 `Component Updater / CI & native IPK/APK` Run [44897597757](https://github.com/wekingchen/luci-app-component-updater/actions/runs/44897597757) 已成功、双包 Artifact 没有过期。
- 该 Run 对应的源提交固定为 `8981a7f8e08b3f788080b36a716a27ec08052b46`，工作流只复用该次已成功的构建资产，不二次编译。
- AX6S 的 APK 管理器自升级/回滚、NaiveProxy 正常安装/回滚已有实体设备证据；IPK 为两代原生 opkg 隔离 rootfs 与 CI 证据，GL-MT3600BE、N1 尚无同等级完整升级/回滚实机证据。
- 整机稳定版 G4 未满足，因此此发布必须为 `--prerelease --latest=false`，不得标记 Stable。

## 操作

进入 [GitHub Actions / Release / V0.5.6 RC3 manager (one-time manual)](https://github.com/wekingchen/luci-app-component-updater/actions/workflows/manual-manager-rc3-release.yml)，在主分支选择 **Run workflow**，输入 `PUBLISH_0.5.6_RC3`。完成后核对 [Release 标签 luci-app-component-updater-v0.5.6-rc3](https://github.com/wekingchen/luci-app-component-updater/releases/tag/luci-app-component-updater-v0.5.6-rc3) 的 IPK、APK 和 `SHA256SUMS.txt` 三个资产。

工作流验证固定 CI Run 的源码 SHA、通过状态、Artifact 名称和摘要，验证包号与文件 SHA256；若标签或 Release 已存在就直接失败，**绝不覆盖已发布文件或重新指向标签**。该工作流没有 push、schedule 或 PR 发布触发器，只有本人主动手工运行才可能发布。

## 发布后的边界

这个 RC 是**正式公开的预发布**，不是稳定版认证。保留未验收：IPK 两台实机的完整升级回滚、PassWall 实时流量、异常/断电恢复与未知 APK 设备兼容性。自动发布门禁保持关闭。发布后不要将 RC3 的成功解释为所有环境 G4 验收完成。
