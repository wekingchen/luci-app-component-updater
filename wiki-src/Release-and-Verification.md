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

## V0.5.6 RC3 的公开发布路径

同一来源提交的 IPK/APK 双包已由主分支 CI 验证。为了不打开长期自动发布门禁，提供 [RC3 一次性人工发布工作流](https://github.com/wekingchen/luci-app-component-updater/actions/workflows/manual-manager-rc3-release.yml)，按要求输入确认字串才能执行；详细说明见 [人工发布指引](https://github.com/wekingchen/luci-app-component-updater/blob/main/docs/manual-manager-rc3-release.md)。**只有 GitHub Release 页面实际存在且三个资产核对完成，才算正式公开发布。**本次目标是预发布 RC，不代表已有 IPK 全部真机验收或 G4 通过。

## 本次版本的事实状态

- **V0.5.4 AX6S LuCI 安装后菜单修复候选（未发布）**：用户真机安装 V0.5.3-r1 成功，但菜单未出现。V0.5.4 统一 APK 与 IPK post-install 控制面刷新，新增 mock-service 回归；仍需设备复测，不能将“包已安装”记为 LuCI UI 已验收通过。

- **V0.5.3 状态文案修复候选（未发布）**：仅调整最新版本状态的提示、可选重新检查按钮视觉层级和无恢复包说明。V0.5.2 MT3600BE Safari 的首页与下载设置可读性以及设置保存已由用户截图和反馈验证；用户还报告在「API 与文件均使用中转」模式下成功查询官方更新。**未取得文件实际中转下载、SHA256 安装包校验及真机升级回滚证据**，也不因此开放 AX6S 正式自动发布。

- **V0.5.2 GL.iNet 手机 UI 打磨候选**：尚未公开发布。V0.5.1 在 MT3600BE 手机 Safari 真实截图中已经解决白底浅字，仍有冗余二级菜单、蓝色主题装饰条、反代节点被隐藏等不足。V0.5.2 增加主题隔离、设置入口及动态表单可发现性回归；**不得从 Chromium 模拟验收推断真机最终通过**。

- **V0.5.0 RC1 管理器**：同版本 IPK 和 APK 在一个 GitHub Release；本次明确获得用户授权作为 *pre-release* 发布。
- **NaiveProxy**：IPK 组件按已验证的官方版本预编译，AX6S APK 组件使用相同的上游版本二进制单独构建并有原固件恢复包。
- **AX6S 当前分项验收**：固件哈希固定、原版 APK 数据库、ARM64 环境下生产控制器与回滚流程通过；**管理器自升级和上一版回滚**已取得实体设备证据（2026-11-21，见下方），**NaiveProxy 正常 APK 更新与手动回滚**也已取得同日 AX6S 实机证据；但 **PassWall 运行时流量、失败自动恢复、受控断电与完整 G3/G4** 未验收。
- **自动发布门禁**：`AX6S_APK_AUTO_PUBLISH` 在真机验收之前不得开启；不要把一次性 V0.5.0 RC 授权延伸成所有后续版本的许可。

### V0.5.6-r3 管理器升级/回滚真机证据（2026-11-21）

AX6S 实体路由器网页操作完成 `0.5.6-r3 → 0.5.6-r4 → 0.5.6-r3`，其中 r4 仅为测试修订号，无独立产品功能变化。升级后 APK 与管理器版本均为 r4、`job_state=completed`、`busy=false`、`recovery_available=true`；网页恢复上一版后 APK 与管理器均为 r3、`job_state=rolled_back`、`busy=false`、`recovery_required=false`。UCI 配置保持，回滚后 `recovery_available=false` 说明该轮恢复包已经使用。此前 r2 的终态空锁问题在本次 r3→r4 没有复现。未单独验证掉电恢复与组件安装失败自动恢复。

因此可将 **管理器自身网页升级/回滚子流程**列为真机通过，但不能仅凭这一项宣称整个组件更新器 G3/G4 通过。NaiveProxy 的正常 APK 分项另见下文；管理器 r3 仍只能作为 RC 候选，自动发布门禁保持关闭。

### NaiveProxy 正常 APK 升级与回滚真机证据（2026-11-21）

实体 AX6S 通过 LuCI 完成 `naiveproxy 154.0.8037.49.5-r1 → r3 → r1`；新包 APK 数据库为 r3，更新后 ELF SHA256 为 `fb19517f2738b131e23c6e49a30d246bf69a2cef835b37c7b6ae82c2168715da`，`job_state=completed`，`rollback_available=true`；网页手动恢复后 APK 数据库和原厂 ELF SHA256 `94a9d2ebce92b2fd877e1e7019dbfa09a7bb7a5d481ec593bd34b5d5abd2a861` 与最初一致，`job_state=rolled_back`，`rollback_available=false`。`/etc/config/naiveproxy` 与 `/etc/apk/world` 的完整 SHA256 在三次观测中完全不变。

**边界**：设备当时未运行 PassWall，`runtime_processes=0` 不是安装故障，也不能证明代理流量或运行中更新安全；下载中断、安装失败自动恢复与断电仍未实测。检查缓存残留 `check_state=ready`、`ready=false` 为后续非阻断性修复项。此为正常更新与手动回滚的真机分项通过，**非 G4 稳定版通过**。

证据与待办：[AX6S 固件兼容与 CI](https://github.com/wekingchen/luci-app-component-updater/blob/main/docs/ax6s-apk-compatibility.md) · [实机验收清单](https://github.com/wekingchen/luci-app-component-updater/blob/main/docs/ax6s-hardware-acceptance-checklist.md) · [门禁原始细则](https://github.com/wekingchen/luci-app-component-updater/blob/main/docs/acceptance-gates.md)。

[首页](Home.md) · [开发约定](Developer-Guide.md)
