# 设备兼容性与边界

**支持 IPK 与 APK 两种软件包体系，不等于支持所有 OpenWrt 设备。** 设备必须同时满足包管理器、固件、架构、软件包归属、依赖及回滚条件。

| 环境 | 包管理器 | 当前结论 |
| --- | --- | --- |
| GL-MT3600BE（GL.iNet 定制 OpenWrt） | opkg / IPK | 原有 IPK 路线；已有用户反馈的基础真实安装与界面操作，发布前的全量验收需按清单核对 |
| Phicomm N1（LEDE/OpenWrt） | opkg / IPK | 原有 IPK 路线，隔离 rootfs 已覆盖原生 opkg，不能把隔离测试当作 N1 的完整实测 |
| Redmi AX6S（`AX6Sproject 2026.11.17-2044-AX6S-MTK`） | APK / APKv3 | V0.5.0 RC1 已通过固件原始数据与 ARM64 chroot 安装/回滚；**实体路由器仍待验收** |
| 其他 AX6S 固件或其他 APK 设备 | APK / APKv3 | **暂未适配；保持只读或禁止写入**，不可推断兼容 |
| 未经适配的组件或设备 | 任意 | 不提供强制安装绕过 |

## AX6S 的适配范围

验证依据是 [特定固件 Release](https://github.com/golldenstj/AX6Sproject/releases/tag/2026.11.17-2044-AX6S-MTK)，平台 `mediatek/mt7622`、架构 `aarch64_cortex-a53`。固件原始镜像与包数据库的哈希、原文件和测试结果载于 [AX6S 适配证明](https://github.com/wekingchen/luci-app-component-updater/blob/main/docs/ax6s-apk-compatibility.md)。

适配器依赖原始软件包的元数据与文件哈希，系统固件更新、用户自己覆盖 ELF 或配置布局变化都可能导致拒绝更新；这属于保护机制而非应跳过的错误。

## 扩展新机型的最低步骤

确认固件身份与真实原生包管理器；采集软件包归属与配置；建立原版备份/恢复方案；加入拒绝未知设备的单测；通过原生根文件系统和架构测试；最后取得该设备的实际安装、联网及回滚验收。

[发布级别与未完成项](Release-and-Verification.md) · [首页](Home.md)
