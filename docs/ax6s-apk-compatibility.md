# Redmi AX6S / ImmortalWrt APK 原生包兼容性（V0.4.0 RC1）

## 支持范围与确切来源

本轮以固件 Release [2026.11.17-2044-AX6S-MTK](https://github.com/golldenstj/AX6Sproject/releases/tag/2026.11.17-2044-AX6S-MTK) 为准，源代码快照为 AX6Sproject 标签提交 `0d9b1d0dc4820ecc11f734db8da8da59d805bd5c`，而非猜测目标设备型号。

| 对照项 | Release 的构建配置 |
| --- | --- |
| 源固件 | `immortalwrt/immortalwrt` 的 `master` |
| 目标 | `mediatek/mt7622`，`xiaomi_redmi-router-ax6s` |
| 架构 | `aarch64_cortex-a53` |
| 包管理器 | `CONFIG_USE_APK=y`，`apk-openssl` |
| 组件支持 | `luci-base`、`rpcd`、`jsonfilter`、`libubox`、`naiveproxy` 均在完整版本中选中 |
| APK 签名 | `CONFIG_SIGN_EACH_PACKAGE=y`，其构建密钥不等于本仓库的私钥 |
| 初始 NaiveProxy | Release 声明 `v154.0.8037.49-5`，二进制 SHA256 为 `89049dae919a088ced487bff2760ca3e624fb818200da43e29d6acaa91ed6ba2` |

固件使用精简 `apk-tools 3`，**未包含 `mkpkg` 命令**，无法像 opkg 版本那样由设备自动打包原版恢复 IPK。AX6S 的自定义 `naiveproxy` 包由 `diy-mtk-part2.sh` 在构建阶段生成，包含 `/usr/bin/naive`、`/etc/config/naiveproxy` 和 `/etc/init.d/naiveproxy` 三个文件，与原更新器“只占有一个可执行文件”前提不相符。

## V0.4.0 RC1 的实际能力

- 新增独立 **原生 APKv3 格式 LuCI 管理包**，由独立的完整 host `apk-tools 3.0.7` 生成，不用 tar.gz 冒充 APK。
- 通过 `/lib/apk/db`、实际 `apk` 命令、`mediatek/mt7622`、架构和板级名称识别 AX6S；即使设备上还有 opkg 也优先识别原生 APK。
- 识别后首页展示中文兼容性提示、固件架构和软件包管理器。对于 APK 环境，**检查更新、下载并更新、恢复旧版全部保持禁用**，rpcd 后端也拒绝执行 IPK 安装、原有 IPK 计划和 IPK 恢复。
- 配置文件列入 APK 保留清单；预检脚本只读取包数据库、系统环境与 SHA256。
- GL-MT3600BE 和 N1 的 opkg 安装、回滚及原有 IPK 发布模式保持不变。

**本版本并不宣称 AX6S 已经能够安装新版 NaiveProxy。** 安装动作必须在以下条件均满足后才能解锁：得到可验证的 AX6S 旧版 APK 恢复包（包含已安装的服务文件、配置文件和原软件包元数据）、官方新版完整 APK、跨版本前后哈希与 APK 数据库版本校验、实机安装与回滚、PassWall 服务不被主动重启的验证。

## AX6S 只读检查（无需升级 NaiveProxy）

从 V0.4.0 RC1 Release 下载 `luci-app-component-updater-0.4.0-r1.apk`，先核对 Release 提供的 SHA256。此 APK 在本仓库生成，不使用 AX6S 固件签名密钥；首次安装时需要明确采用第三方包安装模式：

```sh
# 上传 APK 到 /tmp 后执行；不要把 IPK 安装到 APK 固件
apk add --allow-untrusted /tmp/luci-app-component-updater-0.4.0-r1.apk

# 安装后只读取系统状态，不执行更新
sh /usr/libexec/component-updater/device-ax6s-apk-preflight.sh
```

`--allow-untrusted` 仅对已核验的本地包使用。它会跳过 APK 包自身的签名信任检查，不代表可以跳过 Release 文件摘要核验。当前 Release 的管理器 APK 首次上机前尚无真机确认。

## 两机旧版保护

管理器在 APK 目标上只显示只读提示，后端 `require_opkg` 防护必须经过独立测试。旧版 opkg 目标继续使用固有的只读脚本及原生 IPK，不能以新的 APK 包替代。

## 后续完整能力门禁

1. 先读取 AX6S 真机 `apk info -L naiveproxy`、`apk info -W /usr/bin/naive`、`apk info -v naiveproxy` 和服务脚本 SHA256，确认与 Release 一致且无其他文件归属。
2. 建立 APKv3 NaiveProxy 候选及精确旧版恢复包，保留原配置与服务脚本所有权；必须使用 host `apk mkpkg` 构建，不依赖设备端 `mkpkg`。
3. 在独立 APK rootfs 中验证 install/reinstall/rollback 和版本登记；对无旧包、脚本差异、缺少回滚包、架构不匹配时必须拒绝安装。
4. AX6S 实机测试版本升级和回滚，核对三个文件、APK 数据库和 PassWall 运行状态，再解锁按钮并发布稳定版。

**区分：目前完成的是 APK 管理包与只读设备适配；NaiveProxy 的 APK 更新闭环仍未完成。**
