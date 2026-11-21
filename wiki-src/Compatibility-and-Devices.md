# 设备兼容性与边界

**支持 IPK 与 APK 两种软件包体系，不等于支持所有 OpenWrt 设备。** 设备必须同时满足包管理器、固件、架构、软件包归属、依赖及回滚条件。

| 环境 | 包管理器 | 当前结论 |
| --- | --- | --- |
| GL-MT3600BE（GL.iNet 定制 OpenWrt） | opkg / IPK | V0.5.6 Stable 的 IPK 目标设备；用户确认正常更新与回滚已实测，手机 LuCI/反代查询/设置保留有原始反馈，完整三阶段命令日志尚未归档 |
| Phicomm N1（LEDE/OpenWrt） | opkg / IPK | 保留 opkg 兼容性与 CI 测试；**N1 不需要真机测试、也不阻塞 Stable 发布**，不声称已在 N1 实机验收 |
| Redmi AX6S（`AX6Sproject 2026.11.17-2044-AX6S-MTK`） | APK / APKv3 | 已有原固件 rootfs/ARM64 回归及实体 AX6S **管理器自升级/回滚、NaiveProxy r1→r3→r1 正常安装与手动恢复**实测；运行时代理流量、异常及断电恢复未验收 |
| 其他 AX6S 固件或其他 APK 设备 | APK / APKv3 | **暂未适配；保持只读或禁止写入**，不可推断兼容 |
| 未经适配的组件或设备 | 任意 | 不提供强制安装绕过 |

## AX6S 的适配范围

验证依据是 [特定固件 Release](https://github.com/golldenstj/AX6Sproject/releases/tag/2026.11.17-2044-AX6S-MTK)，平台 `mediatek/mt7622`、架构 `aarch64_cortex-a53`。固件原始镜像与包数据库的哈希、原文件和测试结果载于 [AX6S 适配证明](https://github.com/wekingchen/luci-app-component-updater/blob/main/docs/ax6s-apk-compatibility.md)。

适配器依赖原始软件包的元数据与文件哈希，系统固件更新、用户自己覆盖 ELF 或配置布局变化都可能导致拒绝更新；这属于保护机制而非应跳过的错误。

## 扩展新机型的最低步骤

确认固件身份与真实原生包管理器；采集软件包归属与配置；建立原版备份/恢复方案；加入拒绝未知设备的单测；通过原生根文件系统和架构测试；最后取得该设备的实际安装、联网及回滚验收。

[发布级别与未完成项](Release-and-Verification.md) · [首页](Home.md)
