# LuCI 组件更新器

**当前正式版：V0.5.6 Stable（2026-11-21）**。在 OpenWrt / ImmortalWrt 的 LuCI 中检查 NaiveProxy 官方更新、下载已构建并校验的原生安装包、保留本地配置并支持手动回滚。本项目**不是固件 OTA 升级器**，也不会在路由器上构建/压缩 NaiveProxy。

[下载 V0.5.6 中文正式版（IPK / APK / SHA256SUMS）](https://github.com/wekingchen/luci-app-component-updater/releases/tag/luci-app-component-updater-v0.5.6) · [中文发行说明](docs/releases/v0.5.6-zh-CN.md) · [使用与排障](wiki-src/Operations-and-Troubleshooting.md)

## 安装与兼容范围

| 固件及设备 | 管理器安装包 | 已有证据与范围 |
| --- | --- | --- |
| GL-MT3600BE · opkg 固件 | `luci-app-component-updater_0.5.6-3_all.ipk` | 用户确认已完成 IPK 正常更新/回滚；手机 LuCI、反代查询与设置保留有记录；完整三阶段原始 Shell 日志未归档 |
| Redmi AX6S · 已验证的指定 APKv3 固件 | `luci-app-component-updater-0.5.6-r3.apk` | 管理器网页自升级/回滚、NaiveProxy APK 正常更新/回滚均已真机通过，包数据库与 SHA256 可核对 |
| Phicomm N1 · opkg | 通用 IPK 路线 | **N1 不需要实机测试**，也不将 N1 描述为已获真机认证；以 opkg CI/隔离 rootfs 兼容性回归为证据 |
| 其它 APK 设备及不同固件 | 不提供通用写入承诺 | 未独立适配时应由设备身份、架构及包归属检查拒绝安装，不能跨格式强制安装 |

AX6S 验证的固件基线为 [AX6Sproject 2026.11.17-2044-AX6S-MTK](https://github.com/golldenstj/AX6Sproject/releases/tag/2026.11.17-2044-AX6S-MTK)；详见 [固件兼容证明](docs/ax6s-apk-compatibility.md)。两种管理器安装包**不能混装或互相改扩展名**。请从正式 Release 下载对应文件与 `SHA256SUMS.txt`，在更新前保留独立的管理通道和恢复手段。

## 当前功能

- **中文 LuCI**：入口「系统 → 组件更新」，状态、版本查询、更新和回滚操作；移动端及桌面主题适配。
- **GitHub 下载**：直连、仅文件反代、API + 文件反代三种模式，内置可选节点及自定义 HTTPS 前缀。
- **可信文件校验**：核对 GitHub Release API 资产摘要、Manifest/下载 SHA256、架构、包管理器及本机文件归属；**目前不提供独立数字签名**。
- **更新与恢复**：使用设备自己的 opkg / APKv3 离线安装；保留配置与恢复基线；NaiveProxy 历史备份最多两级、管理器自升级最多保留一份上一版恢复包；不主动重启 PassWall。
- **目前支持的更新组件**：NaiveProxy。管理器自升级与组件更新是两条独立流程，不能把二者的回滚状态混为一谈。

## V0.5.6 Stable 的验收与边界

2026-11-21，AX6S 真实完成管理器 `0.5.6-r3 → 仅测试的 r4 → r3`，任务状态 `completed / rolled_back`、`busy=false`、UCI 设置保留。NaiveProxy 真实完成 `154.0.8037.49.5-r1 → r3 → r1`，回滚后程序的 SHA256 与原厂一致，`/etc/config/naiveproxy` 和 `/etc/apk/world` 更新前后相同。MT3600BE 的 IPK 更新与回滚由用户确认完成，但未归档完整三阶段终端日志，不能杜撰具体版本和文件哈希。

**仍未验收：** 实际运行中的 PassWall 流量与进程切换、实体设备损坏包/写入中断自动恢复、受控断电恢复及其它 APK 固件。AX6S 实测时没有运行 PassWall，`runtime_processes=0` 符合预期。组件更新/回滚后偶见 `check_state=ready` 与 `ready=false` 的过期检查记录，属于待修的非阻断性状态残留。

本次 **Stable 只对上述限定设备的正常安装与手动回滚主路径作出发布判断**。N1 非强制实机验收目标；后续版本不自动继承 Stable 资格，通用自动发布变量 `AX6S_APK_AUTO_PUBLISH` 仍关闭。参见 [验收门禁](docs/acceptance-gates.md)、[AX6S 真实验收记录](docs/ax6s-hardware-acceptance-checklist.md) 及 [发布规则](docs/manual-manager-v0.5.6-stable.md)。

## 文档与维护

[中文知识库](wiki-src/Home.md) · [在线 GitHub Wiki](https://github.com/wekingchen/luci-app-component-updater/wiki) · [设备兼容范围](wiki-src/Compatibility-and-Devices.md) · [安全与回滚](wiki-src/Security-and-Recovery.md) · [备份与空间](docs/backup-retention.md) · [反代及供应链完整性](docs/signing-proxy-device-acceptance.md)

早期 V0.2.x～V0.5.5 UI、包格式、空间预检与菜单修复的*当时状态*保存在 [历史实施记录](docs/implementation-notes.md)、[UI 实机反馈记录](docs/product-ui-acceptance.md) 和 Git 提交历史中，**不代表当前 V0.5.6 仍待发布**。

修改代码前请阅读 [AGENTS.md](AGENTS.md) 和 [项目治理规则](docs/project-governance.md)。`wiki-src/` 是 Wiki 唯一版本化源；主分支更新由 Actions 自动同步，发布说明优先采用简体中文。

## 本地回归

```sh
python3 tools/check_docs.py
python3 -m unittest discover -s tests -v
node tests/luci_ui_smoke.js
python3 tools/package_ipk.py --out dist
```

主 CI 还执行两代原生 opkg、真实 APKv3、ARM64 和 LuCI 浏览器回归；CI 通过不等于未经测试的设备/异常场景已获得认证。
