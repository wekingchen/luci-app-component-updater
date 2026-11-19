# GitHub 反代、供应链完整性与原生 IPK 更新

## 原生 IPK 模式（V0.2.1）

GitHub Actions 预压缩官方程序，生成 `naiveproxy_<version>_<arch>.ipk`，使用 OpenWrt 官方 gzip(tar) 外层 IPK，通过 `opkg install` 升级，因此 opkg 版本随实际安装软件包变化。V0.2.1 不需要 usign 私钥、公钥或 GitHub Secret。

每次检查读取 NaiveProxy 官方 Release 版本、组件构建 Release 的 GitHub API `digest`，验证下载的 Manifest SHA256，校验它声明的 IPK 哈希与 GitHub API 中的 IPK `digest` 一致。安装前再核对 IPK 实际 SHA256。

**这不是端到端数字签名：** GitHub 账户被侵入、代理篡改 GitHub API 响应与文件、或本机管理员权限被恶意利用时，哈希不能保证来源真实性。默认只允许手动确认安装，建议使用可信自有反代，不启用自动升级。

## GitHub 反代

LuCI → 系统 → 组件更新 → GitHub 下载设置。
- 关闭：完全直连 GitHub。
- 仅文件：API 直连；Manifest 与 IPK 可以经过 HTTPS 前缀反代（安全性优先）。
- API + 文件：所有请求经过自定义 HTTPS 前缀；适用于 API 也无法直连的环境，但需要信任反代服务。
- 支持代理失败时直连回退。不要关闭 HTTPS 证书验证。

## 回滚行为

更新前检查旧 naiveproxy 包只拥有 `/usr/bin/naive`，避免覆盖其他程序配置。生成一个使用当前 `opkg` 包版本、架构、依赖信息和当前二进制的本地恢复 IPK，并在持久化目录备份。更新前要求设备已安装 `libgcc1`，不允许在更新时临时从软件源补装依赖。升级使用 `opkg install`；失败时安装备份的 IPK（允许降级）并检查旧 SHA256 和软件包版本。

用户原先手动 UPX 覆盖的文件与 opkg 记录本来可能不同：恢复时会准确恢复更新前的*文件及 opkg 软件包版本记录*，两者仍可能不同。更新器不重启 PassWall，但原软件包升级的旧维护脚本可能有副作用；必须真机验证。

## 真机验收

分别在 GL-MT3600BE、N1 安装 CI 产生的开发 IPK 后执行只读检查：

```sh
sh /usr/libexec/component-updater/device-readonly-acceptance.sh
```

双设备只读门禁通过之后，在具备物理/局域网管理能力时，才执行包含真实安装及恢复的测试：

```sh
COMPONENT_ACCEPT_LIVE=I_UNDERSTAND sh /usr/libexec/component-updater/device-live-acceptance.sh --install-and-rollback
```

通过须证明 opkg 包版本、文件 SHA256、实际程序版本、回滚时的旧版记录均正确；且 PassWall 的符号链接不受影响。实际用户设备测试还没有执行，不得把 CI 绿灯当作 G2/G3 真机通过。
