# V0.2.1 OpenWrt gzip(tar) 格式原生 IPK 更新验收门禁

G0：每次 PR/push 必须通过 Python 单元测试、构建器定义校验、LuCI JS 解析、POSIX/BusyBox Shell 检查、rpcd ACL / 菜单检查，以及离线 opkg 升级与回滚模拟。覆盖损坏 IPK、错误架构、错误哈希、未发布新版本、非单文件软件包、过期预案、并发更新、中断恢复状态和反代安全边界。

G1：GitHub Actions 必须从官方 NaiveProxy GitHub Releases 下载资产，验证官方 digest，使用 UPX 5.2.1 `--lzma --best`，完成 `upx -t`、解压后原文比较、ELF 验证。生成 `aarch64_cortex-a53` 与 `aarch64_generic` 原生 IPK；校验 Control `Package` / `Version` / `Architecture`、仅含目标程序的 Data 和对应 Manifest SHA256。还须在原生 ARM64 musl/libgcc 隔离容器中执行压缩后与未压缩的真实二进制，核对 `--version`。再在 SHA256 固定的官方 OpenWrt 21.02.5 / 24.10.5 rootfs 中使用两代原生 opkg 完成安装、升级、同版本重装与降级回滚。所有门禁通过后才可发布 prerelease；设备真实功能尚未验收前不得标记稳定版。

G2：GL-MT3600BE 和 N1 分别安装 CI 测试 IPK，执行 `device-readonly-acceptance.sh`，在 LuCI 桌面端与手机端检查菜单、RPC、ACL、反代设置和版本状态。

G3：必须拥有独立管理通道，在两台设备分别执行 `device-live-acceptance.sh --install-and-rollback`，核对旧、新、回滚后的文件 SHA256、opkg 数据库版本、PassWall 符号链接，测试下载失败与异常恢复。旧程序正在运行不等于新程序已生效，需分别记录。

G4：全部上述真实测试、连接恢复及前端回归通过后才允许正式稳定发布；不允许在 G2/G3 未完成时宣称真机可用或自动升级。

## 用户体验

默认分支按每 20 分钟一次的时间表预先扫描并构建，但 GitHub Actions 定时任务可能延迟。LuCI 只检查已经发布的云端原生 IPK，云端未就绪时显示 Pending，不会点击后现场等待压缩。

## 供应链安全

V0.2 不使用独立签名私钥。默认让 GitHub API 直连，匹配 API 的 asset `digest` 与 Manifest / IPK 实际 SHA256。选择“API + 文件全部代理”时须信任 HTTPS 代理本身，不能等同签名验证。
