# AX6S APKv3 原生更新与回滚 · 固件适配及真机分项验收

## 验证的固件来源

来自 [AX6Sproject 2026.11.17-2044-AX6S-MTK](https://github.com/golldenstj/AX6Sproject/releases/tag/2026.11.17-2044-AX6S-MTK) 的原版 `sysupgrade.itb`，SHA256：
`a963222763cf7c2c1b9bc521730a9d1b06b2e261caca156e6c7ebdebe1afc181`。

从已经验证 SHA256 的固件中提取真正的 SquashFS、APK 数据库及 NaiveProxy 原始文件（架构 `aarch64_cortex-a53`，平台 `mediatek/mt7622`）。原版本 `154.0.8037.49.5-r1`，依赖 `libc`。原始核心文件：

| 文件 | 固件中的 SHA256 |
| --- | --- |
| `/usr/bin/naive` | `94a9d2ebce92b2fd877e1e7019dbfa09a7bb7a5d481ec593bd34b5d5abd2a861` |
| `/etc/init.d/naiveproxy` | `4d9dec9eb81586c5ea932260500329b68fc60f8c38af0712516b7a0f0ae59849` |
| `/etc/config/naiveproxy` | `201d0b3afd1e131f7695a4e4f541ec0ff6447dc8bf824eb8f96827d530b03682` |

注意：**实际固件内的 naive ELF 摘要与该 Release 正文里列出的预编译 ELF 摘要不同**。本仓库以经过固件镜像验证的真实文件作为恢复基线，不将 Release 正文的单独哈希当作固件原始程序哈希。

## 两种原生软件包管理器，共用 UI

- 旧版 OpenWrt/opkg：原有 GitHub 发现、IPK、旧版备份、安装及失败回滚逻辑保持不变。
- AX6S/ImmortalWrt APK：新加入 `ax6s-apkctl.sh`，检查相同的官方版本和 Manifest，但下载和安装原生 APKv3，不会误调用 opkg，既有下载反代及 LuCI UI 共用。
- 其它未知 APK 环境不会误启用更新，强制检查固件板型、版本、APK 数据库及 NaiveProxy 文件所有权。

## 原生 APK 完整安全闭环

1. GitHub Actions 直接复用已经验证官方来源和 UPX 5.2.1 解压回环的 r3 IPK 二进制，利用 pin 版本的完整 `apk-tools 3.0.7` 在云端生成两个真正的 APKv3 包：新版安装包、从原固件文件重建的 r1 恢复包，均带对应 SHA256。设备不自行压缩或制包。
2. 检查固件身份、现有 `naiveproxy` APK 数据库版本、已拥有的文件、`naive` 哈希及 init 脚本哈希；出现无法解释的手动改动则阻止安装。
3. 校验官方发布 tag 与更新器仓库 Release API 摘要、Manifest、原始与目标 APK SHA256；已有真实包、签名密钥或不兼容架构之间不做静默降级。
4. 先永久保存恢复包、当前真实可执行文件、用户配置、APK 版本与收据，并在磁盘上记录事务标识；如果旧版完整 APK 下载/校验不成功则不安装。
5. 安装前执行 APK `--simulate`，随后以 `--no-network --no-scripts --no-commit-hooks` 安装**唯一已经经过摘要校验的本地 APK**，不会因为 stale feed 额外安装其它包，也不会主动重启 PassWall。
6. 安装后核对 APK 数据库、二进制、服务脚本及用户配置的 SHA256；失败立即恢复旧版，保留未完成事务供人工处理。成功后保存新 APK 供下一轮升级前备份，支持手动回滚。
7. 使用 `--allow-untrusted` 只针对已经由 GH Release API + Manifest 多级摘要校验的单个本地 APK。**没有独立数字签名**，启用 GitHub API 反代意味着额外信任反代节点，风险需要明确告知。

## 已完成的 CI 验证

- 真实 hash-pinned AX6S 固件 rootfs 的 APK 数据库 r1→r3→r1 升级、降级及 bin/init SHA256 核验通过。
- Ubuntu ARM64 runner 上使用固件真实 `/bin/sh`、`apk-tools 3.0.5`、`jshn`、`jsonfilter` 运行生产 `component-updaterctl` 和 `ax6s-apkctl.sh`（**只替换网络下载为经过摘要校验的本地 fixture**）：新版检查、故意篡改拒装、真实 APK 安装、用户更改配置不丢失、手动恢复及清除事务标记已验证。
- 原有 opkg 21.02.5 / 24.10.5 软件包管理、LuCI、rpcd 回归测试保持独立，不能为了支持 APK 放宽 IPK 约束。

## AX6S 实际安装后菜单缺失回归（2026-11-20）

真实 AX6S 上，用户成功以本地 `--no-network --allow-untrusted` 安装管理器 `0.5.3-r1`（并确认 APK 已安装），但是 LuCI 菜单未出现。云端测试检查包数据库和 JSON 文件，不代表真实 HTTP 进程已重新读取菜单与 ACL。本次暴露出旧版 APK 的 post-install 仅 `rpcd reload`，与 IPK 的 `rpcd restart` 不一致。V0.5.4 在包内使用同一控制面刷新脚本：清理 LuCI 临时索引和模块缓存，重启 rpcd 和 uhttpd，**不重启 NaiveProxy/PassWall**。此变更尚须真机复验，也不能排除 ACL/菜单路径等其他原因。

## 2026-11-21 AX6S 真机：NaiveProxy r1 → r3 → r1 完整正常更新与手动回滚

用户在 Redmi AX6S 实体路由器的 LuCI 页面上完成检查更新、下载并更新和「恢复上一个版本」，以 SSH 原始输出核对了**同一上游版本的两个 APK 构建修订**（不是 NaiveProxy 上游版本升级）：

| 校验项 | 更新前（原厂） | 更新后（优化构建） | 网页回滚后 |
| --- | --- | --- | --- |
| `apk list --installed --manifest naiveproxy` | `154.0.8037.49.5-r1` | `154.0.8037.49.5-r3` | `154.0.8037.49.5-r1` |
| `/usr/bin/naive` SHA256 | `94a9d2ebce92b2fd877e1e7019dbfa09a7bb7a5d481ec593bd34b5d5abd2a861` | `fb19517f2738b131e23c6e49a30d246bf69a2cef835b37c7b6ae82c2168715da` | `94a9d2ebce92b2fd877e1e7019dbfa09a7bb7a5d481ec593bd34b5d5abd2a861` |
| `/etc/config/naiveproxy` SHA256 | `201d0b3afd1e131f7695a4e4f541ec0ff6447dc8bf824eb8f96827d530b03682` | 相同 | 相同 |
| `/etc/apk/world` SHA256 | `5f8b004990fc8d141196c98b55917df51c41ceecea7bdcc7163cf5960eb9ac2a` | 相同 | 相同 |
| `job_state` | — | `completed` | `rolled_back` |
| `rollback_available` | 初始网页禁用 | `true` | `false`（上一版本已恢复） |

- 更新后程序输出 `naive 154.0.8037.49`，组件管理器报告 `package_version=154.0.8037.49.5-r3`、`job_message=Native APK installed; PassWall not restarted`；回滚后报告 `package_version=154.0.8037.49.5-r1`、`job_message=Original APK version and configuration restored`。
- 设备识别：`device_board=xiaomi,redmi-router-ax6s`、`firmware_target=mediatek/mt7622`、`architecture=aarch64_cortex-a53`、`compatibility=ax6s-apk-native`。用户处理空间限制后，页面实际进入「新版本已准备就绪」，并能执行安装。
- 已证实：本机真实 APK 软件包更新、可执行文件替换、原配置及 APK world 完整保留、正常手动回滚和原文件恢复。已安装版本与 SHA256 的前后对比由用户实机 Shell 输出支持。
- **未验证**：用户明确表示当前没有运行 PassWall，`runtime_processes=0` 属于预期；因此本次**不构成代理流量、进程热切换或连接不中断验收**。也未实际诱发下载中断、损坏包、安装中故障、overlay 写入失败及断电恢复。
- **已知小问题（不阻断回滚，留待后续版本修复）**：更新/回滚后 `check_state=ready`、`check_message=Verified native APK is ready for manual installation` 是检查阶段残留，实际 `ready=false`；页面的版本、按钮及回滚状态已正确刷新。后续将终态检查状态与已清除的更新计划统一，补单测；本次仅更新验收文档，不改运行逻辑或另发 r4。

## 尚需实体 AX6S 验收

**已通过的分项**：实体 AX6S 上的管理器网页自升级/回滚，以及 NaiveProxy 正常 APK 检查、下载安装、原配置与 world 保持、手动 r3→r1 回滚。设备的实际 Flash/overlay 写入在正常安装/恢复场景已经发生，不能再笼统写成「真机写入和回滚从未测试」。

**尚未验证**：真实代理进程运行中热切换、PassWall/NaiveProxy 流量与服务恢复、下载中断、损坏包导致的自动恢复、Flash/Overlay 写入失败、意外断电、所有桌面 LuCI 导航场景和其它 APK 固件身份。由于本次设备未运行 PassWall，这些运行时项目不能据此视为通过。**整机完整验收和稳定版资格尚未达到**；RC / prerelease 与自动发布门禁继续保持。
