# AX6S APKv3：实机分项验收记录与正式版发布门禁

> 决策日期：2026-11-20。用户已决定**先记录真实设备未测项，同时允许 V0.5.0 合并并发布 RC 预发布版**。RC 预发布并不代表 AX6S 实际路由器已经验收；不得写成稳定版。

## 已通过的云端验收

- [更新器 V0.5.0 IPK/APKv3、单元及 LuCI/rpcd 回归](https://github.com/wekingchen/luci-app-component-updater/actions/runs/44558226988)。
- [原始 AX6S 固件镜像、原生 APKv3 完整 ARM64 升级/降级、篡改包拒装和恢复包恢复测试](https://github.com/wekingchen/luci-app-component-updater/actions/runs/44558226790)。
- 真实固件 rootfs 下 native ubusd/rpcd 接口、管理器 V0.4→V0.5 更新以及 UCI 设置保留。
- 真实 APK 数据库 r1→r3→r1；保留配置与 `/etc/apk/world`；模拟中断事务、恢复包故意损坏、拒装与修复后回滚。

**模拟环境不包括真实 AX6S 的 Flash、overlay、PassWall 实时流量以及意外断电。**

## 2026-11-20 AX6S 真机新增证据：首次 APK 安装成功，LuCI 菜单缺失

- 用户通过 `apk --no-network --allow-untrusted --simulate add /tmp/upload.apk` 预演安装，得到 `luci-app-component-updater 0.5.3-r1`，并看到 `OK: 286.8 MiB in 305 packages`。
- 用户实际执行 `apk --no-network --allow-untrusted add /tmp/upload.apk` 成功，post-install 被执行，随后 `apk --no-network list --installed --manifest luci-app-component-updater` 返回 `luci-app-component-updater 0.5.3-r1`。
- **故障**：刷新 LuCI 页面仍没有出现「组件更新」菜单；未知菜单文件存在性、rpcd ACL 重新加载结果和直接访问路由结果，均需要进一步收集，不能归因为单一原因。
- **修复候选**：V0.5.4 将 APK 与 IPK 使用同一套 post-install 缓存清理和控制面重启脚本，补此前未覆盖的真实脚本效果单测；仍需真机实测验证，不宣称完成 AX6S G2 及 G3。
- **安全**：跳过签名只能对已经独立核对可信 SHA256 的特定本地包使用 `--allow-untrusted`，不可全局关闭签名校验；安装本地包可使用 `--no-network`。

## 2026-11-21 AX6S 真机新增证据：管理器网页升级与回滚闭环

用户在实体 AX6S/ImmortalWrt 上完成 **V0.5.6-r3 → 测试版 r4 → r3** 的网页管理器自升级与手动回滚。r4 是从 r3 临时将包修订号改为 `4` 的自动化测试包，不是新的正式产品版本。保留以下可复核的终态证据：

- 升级后：`apk list --installed --manifest luci-app-component-updater` 输出 `luci-app-component-updater 0.5.6-r4`；`manager-self-update.sh status` 返回 `installed_version=0.5.6-r4`、`job_state=completed`、`busy=false`、`recovery_available=true`、`recovery_required=false`，消息为 `Manager upgrade completed; one rollback archive retained`。
- 用户通过网页执行「恢复上一版本」，页面显示 `当前版本：0.5.6-r3`；SSH APK 数据库也确认 `luci-app-component-updater 0.5.6-r3`。
- 回滚后 `manager-self-update.sh status` 返回 `installed_version=0.5.6-r3`、`job_state=rolled_back`、`job_message=Previous manager restored and checked`、`busy=false`、`recovery_required=false`、`recovery_available=false`；末项为已消耗上一版恢复包后的正常结果，并非回滚失败。`staged_candidate=0.5.6-r4` 是旧候选记录，不代表当前运行 r4。
- `uci show component-updater` 仍存在完整主配置（稳定通道、`auto_install=0`、保留两级组件备份、官方上游与仓库、反代关闭及预置节点）。
- 这一证据支持**管理器网页自升级/回滚子流程在 AX6S 实机通过**，特别是 r2 曾出现的升级后 `busy` 不释放问题，在此次 r3→r4 未复现。NaiveProxy 的正常升级/手动回滚已于同日另行实测（见下节），但掉电恢复、PassWall 实时流量、安装失败自动回滚仍未验证，不能将整个 AX6S G3/G4 标记通过。
- 对应分支 PR [#19](https://github.com/wekingchen/luci-app-component-updater/pull/19)，同一提交的[管理器/双包 CI](https://github.com/wekingchen/luci-app-component-updater/actions/runs/44807615639)与[原生 AX6S ARM64 回归](https://github.com/wekingchen/luci-app-component-updater/actions/runs/44807615837)均成功。自动发布条件仍必须保留关闭。

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

## 实机验收清单（进行中）

- [ ] 确认实际 AX6S 固件身份、架构、板型、APK 包管理器、NaiveProxy 版本、文件归属，并保存当前完整恢复基线。
- [ ] 预检 overlay/Flash 空间与安装风险，安装同 Release 下经过 SHA256SUMS 验证的 V0.5.0 管理器 APK。
- [ ] 验证 LuCI 界面（桌面和手机）、rpcd 全部操作、直连及 GitHub 反代策略、已保存配置升级不丢失。
- [x] AX6S 真机 LuCI 官方检查、下载并安装 NaiveProxy 原生 APK，核验 APK 数据库及新版 ELF SHA256，任务为 `completed`。
- [ ] 单独采集升级后 `/etc/init.d/naiveproxy` SHA256（生产安装器自检包含该校验，但用户终端未单独提供哈希输出）。
- [ ] 验证 PassWall 现有连接不中断、正常代理流量及设备稳定性；确认未未经授权重启服务。
- [x] 对比 `/etc/config/naiveproxy` 和 `/etc/apk/world` 更新前、更新后及回滚后的完整 SHA256，三次均相同。
- [x] AX6S 真机 LuCI 手动 r3→r1 回滚；APK 版本、原厂 ELF SHA256、配置及 APK world 均恢复/保留，任务为 `rolled_back`。
- [ ] 独立核对回滚后的 init 脚本哈希和详细持久化收据，并在实际启用代理时验证流量/运行时版本切换。
- [ ] 在具备恢复手段的前提下验证下载中断、事务未完成、闪存写入失败，以及安全受控的断电恢复。
- [ ] 根据真机验收记录修复任何问题，并完整重跑 IPK/APK 双格式回归。

## 发布决策

- **V0.5.0 RC1**：允许合并并发布为 *GitHub pre-release*；同一版本分别产出 IPK 和 APK 管理器，均附 SHA256SUMS。Release 明确标明“AX6S 真机尚未验收”，不标记 latest/stable。
- **V0.5.6 限定范围 Stable（2026-11-21 发布决策）**：目标设备是 MT3600BE（IPK）和指定固件 AX6S（APK）；N1 不要求实机测试、不阻塞本次稳定发布。以已确认的正常升级与手动回滚主路径、同批 CI 双包及发行说明明确的剩余风险作为一次性发布依据。MT3600BE IPK 完整三阶段原始终端日志未归档，只记录用户确认，不杜撰具体哈希。
- **后续无人值守自动发布 / 更广泛稳定性认证**：上述尚未完成的在线流量、故障注入与断电等实机项目仍属门禁，不能因本次限定范围 Stable 自动跳过。
- **持续自动发布**：`AX6S_APK_AUTO_PUBLISH` 在上述真实设备验收前保持关闭。V0.5.0 RC1 仅授权一次性发布，不应导致未来提交自动绕过验收门禁。

*仓库 Issues 功能当前关闭，因此此文件作为持久的项目验收记录。*

- **2026-11-20 新 UI 缺口**：V0.5.4 的 AX6S iPhone Safari 截图已确认能进入菜单并看到组件/设备信息，但标题竖排、页头悬浮遮挡。V0.5.5 针对宿主 `header` 规则隔离页头，尚待手机和桌面 LuCI 真机检查。安装成功与页面可见不能替代完整 G2/G3 验收。

- **2026-11-20 当时的功能缺口（已由 2026-11-21 正常检查与更新实机操作补足）**：AX6S 已有互联网连接，但 LuCI NaiveProxy 官方版本检查实际返回失败，具体 `check_message` 未采集；同一时段 UI 错误地显示更新任务进行中而后端无任务。V0.5.5 已补前端状态区分与安全中文诊断，拆分 APK manifest 下载与摘要错误；其后已取得 2026-11-21 真机检查/更新/手动回滚的状态与包数据库输出；原故障仍作为历史问题保留。
