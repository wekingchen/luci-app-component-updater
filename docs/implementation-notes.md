# V0.1 实施与验收记录

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

现有二进制由用户通过 UPX 5.2.1 `--lzma --best` 手动压缩并覆盖，代理功能已被用户实测可用。首版保留 opkg 双版本显示，不尝试直接改动软件包数据库。

## 首轮真机验收

1. 通过 Actions 下载 IPK；在 MT3600BE 安装后检查 `ubus -v list component-updater` 是否注册、LuCI 页面及 ACL 是否工作。确保 rpcd 不需要额外 `rpcd-mod-ucode`。
2. 执行 `component-updaterctl status`，确认真实版本 154.0.8037.49 和 opkg 记录 150.x 并存。
3. 执行 `component-updaterctl check`，确认官方 Tag、对应 `aarch64_cortex-a53` 预压缩构建存在或明确提示尚未同步。
4. 单独审查 Manifest 中的 SHA256 和来源；检查压缩后文件大小和 `naive --version`，先不替换生产文件。
5. 在预留可恢复访问路径时测试更新、PassWall 保持运行、旧进程继续运行、后续服务切换和回滚。
6. 重启与 OTA 后验证本工具记录、软链接、备份和安装状态的一致性；再扩大到 N1。

## 发布门槛

GitHub Actions 单测与基础 UPX 测试通过只能进入候选状态。没有独立签名、公钥绑定和双真机验收的版本，不应标为经过完整稳定性验证的生产稳定版。
