# GitHub 反代、供应链完整性与原生 IPK 更新

> **当前状态（V0.5.6 Stable）**：本页的 V0.2.1～V0.5.2 命令与反代观察属于历史基线。MT3600BE IPK 的正常更新/回滚由用户确认完成，AX6S APK 正常更新/回滚另有完整真机证据；**N1 不要求真机测试**。具体发布范围、未验 PassWall 与故障恢复风险见 [中文发行说明](releases/v0.5.6-zh-CN.md) 与 [验收门禁](acceptance-gates.md)。

## MT3600BE 反代真实查询记录（2026-11-20）

用户在 V0.5.2 的手机 LuCI 下载设置中保存了反代选项，并报告将连接方式调整为 **「版本查询与文件下载均使用中转」** 后成功执行「检查官方更新」。这验证了当前真机环境下该配置的官方版本查询功能可用；尚无独立网络抓包证据，也**不能据此认定安装包文件中转下载、SHA256 及升级回滚已通过**。这份 2026-11-20 的反代查询记录不能单独证明文件中转下载及摘要校验；虽然用户后来确认 MT3600BE IPK 正常更新与回滚已完成，仓库仍缺该次三阶段完整终端日志及独立中转下载校验记录。

## 原生 IPK 模式（V0.2.1）

GitHub Actions 预压缩官方程序，生成 `naiveproxy_<version>_<arch>.ipk`，使用 OpenWrt 官方 gzip(tar) 外层 IPK，通过 `opkg install` 升级，因此 opkg 版本随实际安装软件包变化。V0.2.1 不需要 usign 私钥、公钥或 GitHub Secret。

每次检查读取 NaiveProxy 官方 Release 版本、组件构建 Release 的 GitHub API `digest`，验证下载的 Manifest SHA256，校验它声明的 IPK 哈希与 GitHub API 中的 IPK `digest` 一致。安装前再核对 IPK 实际 SHA256。

**这不是端到端数字签名：** GitHub 账户被侵入、代理篡改 GitHub API 响应与文件、或本机管理员权限被恶意利用时，哈希不能保证来源真实性。默认只允许手动确认安装，建议使用可信自有反代，不启用自动升级。

## GitHub 反代

LuCI → 系统 → 组件更新 → GitHub 下载设置。
- 关闭：完全直连 GitHub。
- 仅文件：API 直连；Manifest 与 IPK 可以经过 HTTPS 前缀反代（安全性优先）。
- API + 文件：所有请求经过自定义 HTTPS 前缀；适用于 API 也无法直连的环境，但需要信任反代服务。
- 预置节点选择：`gh-proxy.org`、`ghproxy.cc`、`ghproxy.com`、`ghfast.top`，以及自定义 HTTPS 前缀；默认关闭反代。
- 支持代理失败时直连回退。不要关闭 HTTPS 证书验证。节点预置不等于实时连通测试，实际可用性取决于路由器所在网络。

## 回滚行为

更新前检查旧 naiveproxy 包只拥有 `/usr/bin/naive`，避免覆盖其他程序配置。生成一个使用当前 `opkg` 包版本、架构、依赖信息和当前二进制的本地恢复 IPK，并在持久化目录备份。更新前要求设备已安装 `libgcc1`，不允许在更新时临时从软件源补装依赖。升级使用 `opkg install`；失败时安装备份的 IPK（允许降级）并检查旧 SHA256 和软件包版本。

用户原先手动 UPX 覆盖的文件与 opkg 记录本来可能不同：恢复时会准确恢复更新前的*文件及 opkg 软件包版本记录*，两者仍可能不同。更新器不重启 PassWall，但原软件包升级的旧维护脚本可能有副作用；必须真机验证。

## V0.5.6 正式版的实机验收边界

**MT3600BE** 是本版 IPK 正式验收设备。用户已经确认正常更新及手动回滚完成；原始三阶段 Shell 日志尚未在本仓归档，不能杜撰未知的 opkg 版本及文件哈希。需要复查时，在设备已有脚本的前提下可先执行只读诊断：

```sh
sh /usr/libexec/component-updater/device-readonly-acceptance.sh
```

具有独立恢复手段并明确希望重新做安装/恢复验证时，才考虑：

```sh
COMPONENT_ACCEPT_LIVE=I_UNDERSTAND sh /usr/libexec/component-updater/device-live-acceptance.sh --install-and-rollback
```

该命令执行真实写入，**不属于检查文档或升级管理器时的例行必做项**。N1 可沿用通用 IPK 路线和原生 opkg CI 兼容性测试，但**不要求 N1 专门实机测试，也不声称 N1 已真机认证**。实际代理流量及断电/异常恢复仍需另行专项验证。
