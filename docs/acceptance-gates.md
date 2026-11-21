# LuCI Component Updater · V0.5.6 指定设备验收门禁

G0：每次 PR/push 必须通过 Python 单元测试、构建器定义校验、LuCI JS 解析、POSIX/BusyBox Shell 检查、rpcd ACL / 菜单检查，以及离线 opkg 升级与回滚模拟。覆盖损坏 IPK、错误架构、错误哈希、未发布新版本、非单文件软件包、过期预案、并发更新、中断恢复状态和反代安全边界。

G1：GitHub Actions 必须从官方 NaiveProxy GitHub Releases 下载资产，验证官方 digest，使用 UPX 5.2.1 `--lzma --best`，完成 `upx -t`、解压后原文比较、ELF 验证。生成 `aarch64_cortex-a53` 与 `aarch64_generic` 原生 IPK；校验 Control `Package` / `Version` / `Architecture`、仅含目标程序的 Data 和对应 Manifest SHA256。还须在原生 ARM64 musl/libgcc 隔离容器中执行压缩后与未压缩的真实二进制，核对 `--version`。再在 SHA256 固定的官方 OpenWrt 21.02.5 / 24.10.5 rootfs 中使用两代原生 opkg 完成安装、升级、同版本重装与降级回滚。所有门禁通过后才可发布 prerelease；设备真实功能尚未验收前不得标记稳定版。

G2：V0.5.6 Stable 的目标设备是 GL-MT3600BE（opkg/IPK）和指定固件 Redmi AX6S（APKv3）；核对各自设备身份、LuCI 手机/桌面、RPC/ACL、更新/恢复、反代设置和版本状态。**N1 不在 V0.5.6 Stable 的强制真机验收范围内**，现有 opkg CI 可以作为兼容性证据，但不等于 N1 实测。

G3：目标设备须具备独立恢复通道；MT3600BE IPK 正常更新与回滚由用户明确确认完成，已保存手机 LuCI、反代版本查询与设置保留证据，但三阶段 Shell 原始记录尚未在仓库归档（不得推造版本或哈希）；AX6S 管理器 r3→测试 r4→r3 和 NaiveProxy APK r1→r3→r1 已有实际版本、二进制 SHA256、配置和 world 输出。**N1 实机不要求测试，也不阻塞本版发布。**

G4：V0.5.6 可作为**限定目标设备的 Stable**发布：两种包格式来自相同成功 CI，正常更新及手动回滚分别有用户确认或原始输出、恢复路径明确；Release 必须如实披露证据等级。N1 不在强制验收内；**不宣称**已测试 PassWall 运行中无中断、实体设备损坏/断网自动恢复或断电恢复。上述未验场景继续作为专项风险，不能借本次一次性 Stable 解除 `AX6S_APK_AUTO_PUBLISH` 后续自动发布门禁。

## 用户体验

默认分支按每 20 分钟一次的时间表预先扫描并构建，但 GitHub Actions 定时任务可能延迟。LuCI 只检查已经发布的云端原生 IPK，云端未就绪时显示 Pending，不会点击后现场等待压缩。

## 供应链安全

V0.2 不使用独立签名私钥。默认让 GitHub API 直连，匹配 API 的 asset `digest` 与 Manifest / IPK 实际 SHA256。选择“API + 文件全部代理”时须信任 HTTPS 代理本身，不能等同签名验证。
