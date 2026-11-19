# V0.2.1 适配环境与验收记录

## 已知真机信息（用户提供）

| 项目 | GL-MT3600BE |
|---|---|
| 固件 | OpenWrt 21.02-SNAPSHOT / iStoreOS-like 定制 |
| Target/Architecture | mediatek/mt7987 / aarch64_cortex-a53 |
| opkg 记录 | naiveproxy 150.0.7871.63.1-r1 |
| 二进制实际版本 | naive 154.0.8037.49 |
| ELF | AArch64 (e_machine 183), UPX! 特征 |
| 更新文件 | /usr/bin/naive |
| PassWall 路径 | /tmp/etc/passwall/bin/naive → /usr/bin/naive |
| 进程 | 2 个 NaiveProxy |
| 可用 /overlay /tmp | 181.7 MiB / 239.3 MiB（检测时） |

现有二进制由用户通过 UPX 5.2.1 `--lzma --best` 手动压缩并覆盖，代理功能已被用户实测可用。当前采用原生 IPK 的 opkg 安装，升级后会同步 opkg 包版本。回滚会恢复更新前记录和旧二进制；如果曾手动覆盖程序，回滚后两套版本信息仍可能不同。

## 首轮真机验收

1. 通过 Actions 下载 IPK；在 MT3600BE 安装后检查 `ubus -v list component-updater` 是否注册、LuCI 页面及 ACL 是否工作。确保 rpcd 不需要额外 `rpcd-mod-ucode`。
2. 执行 `component-updaterctl status`，确认真实版本 154.0.8037.49 和 opkg 记录 150.x 并存。
3. 执行 `component-updaterctl check`，确认官方 Tag、对应 `aarch64_cortex-a53` 预压缩构建存在或明确提示尚未同步。
4. 单独审查 Manifest 中的 SHA256 和来源；检查压缩后文件大小和 `naive --version`，先不替换生产文件。
5. 在预留独立恢复通路时测试原生 IPK 更新、opkg 版本同步、正在运行的 PassWall 进程、后续服务切换和恢复 IPK 回滚。
6. 重启与 OTA 后验证本工具记录、软链接、备份和安装状态的一致性；再扩大到 N1。

## 发布门槛

GitHub Actions 单测与基础 UPX 测试通过只能进入候选状态。V0.2.x 不采用独立数字签名，但必须进行 GitHub Release SHA256 验证；在双真机测试、实际代理连接与恢复验收通过前，不应标为生产稳定版。


## 2026-11-19 · 构建与包格式审计

- 两种 ARM64 官方 NaiveProxy 二进制分别在原生 ARM64 Alpine musl + libgcc 沙盒中执行成功（包括 UPX 压缩版）。
- 最初的 Debian ar 外层 IPK 被真实 OpenWrt 21.02 opkg 判定为 Malformed package；已经统一切换为 OpenWrt 官方 `gzip(tar)` 外层 IPK，涵盖 LuCI 包、NaiveProxy 包和恢复包。
- 真实 OpenWrt 21.02.5 opkg（2021-06-13 版本）及 OpenWrt 24.10.5 opkg 在隔离 rootfs 内，均通过旧版安装、升级、同版本强制重装与降级回滚；测试文件和版本哈希一致。
- 它们不等于 GL-MT3600BE 定制固件与 N1 LEDE 定制固件的真机验收。PR 保持 Draft，未装真机。
