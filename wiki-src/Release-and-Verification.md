# 版本发布与验收门禁

## 为什么区分 RC 和正式稳定版？

云端 CI、原生 opkg/APK 隔离根文件系统和 ARM64 chroot 可以证明**真实软件环境的安装/回滚路径**，却不能证明实体设备 Flash/overlay、实际 PassWall 流量、浏览器 UI、网络波动与断电安全。因此不能直接把 CI 绿色说成“所有真机稳定”。

| 级别 | 最低证据 | 可发布状态 |
| --- | --- | --- |
| G0：源码与行为单测 | Python、JS、Shell、接口/安装与异常契约 | 开发候选 |
| G1：包及原生环境 | 官方来源、UPX、SHA256、架构、原生 opkg/APKv3、实际 rootfs 和 ARM64 验证 | RC 预发布 |
| G2：实机只读与 UI | 设备身份、空间、LuCI/rpcd、手机/桌面、反代检查 | 验收中 |
| G3：实机写入与回滚 | 备份、真实安装、依赖、服务、配置、失败/手动回滚 | 待确认稳定 |
| G4：审查与正式晋升 | 全部指定设备验收、回滚保障和记录可核查 | 稳定版资格 |

## 本次版本的事实状态

- **V0.5.0 RC1 管理器**：同版本 IPK 和 APK 在一个 GitHub Release；本次明确获得用户授权作为 *pre-release* 发布。
- **NaiveProxy**：IPK 组件按已验证的官方版本预编译，AX6S APK 组件使用相同的上游版本二进制单独构建并有原固件恢复包。
- **AX6S 目前达到 G1**：固件哈希固定、原版 APK 数据库、ARM64 环境下生产控制器与回滚流程通过；G2/G3 尚未完成。
- **自动发布门禁**：`AX6S_APK_AUTO_PUBLISH` 在真机验收之前不得开启；不要把一次性 V0.5.0 RC 授权延伸成所有后续版本的许可。

证据与待办：[AX6S 固件兼容与 CI](https://github.com/wekingchen/luci-app-component-updater/blob/main/docs/ax6s-apk-compatibility.md) · [实机验收清单](https://github.com/wekingchen/luci-app-component-updater/blob/main/docs/ax6s-hardware-acceptance-checklist.md) · [门禁原始细则](https://github.com/wekingchen/luci-app-component-updater/blob/main/docs/acceptance-gates.md)。

[首页](Home.md) · [开发约定](Developer-Guide.md)
